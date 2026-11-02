"""Ejecución offline de un DAG con recibos verificables y manifiesto de fallos."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
from importlib.metadata import distributions
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import uuid


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def json_read(path):
    def invalid(value):
        raise ValueError(f"JSON no finito: {value}")
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=invalid)


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


@dataclass(frozen=True)
class Stage:
    name: str
    script: str
    arguments: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    configs: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    json_versions: dict[str, int] = field(default_factory=dict)
    optional: bool = False
    unavailable_reason: str | None = None


def dependency_order(stages, selected):
    registry = {stage.name: stage for stage in stages}
    if len(registry) != len(stages):
        raise ValueError("Hay nombres de etapa duplicados")
    ordered, visiting, visited = [], set(), set()

    def visit(name):
        if name not in registry:
            raise ValueError(f"Etapa desconocida: {name}")
        if name in visiting:
            raise ValueError(f"Dependencia circular: {name}")
        if name in visited:
            return
        visiting.add(name)
        for dependency in registry[name].dependencies:
            visit(dependency)
        visiting.remove(name)
        visited.add(name)
        ordered.append(registry[name])
    for name in selected:
        visit(name)
    return ordered


class Preparation:
    SCHEMA_VERSION = 1

    def __init__(self, root, report_dir="artifacts/reports/demo", *, environment=None, context=None):
        self.root = Path(root).resolve()
        self.report_dir = self.path(report_dir)
        self.manifest_path = self.report_dir / "preparation-manifest.json"
        self.environment = environment if environment is not None else {
            "python": platform.python_version(), "platform": platform.platform(),
            "packages": dict(sorted((d.metadata["Name"].lower(), d.version) for d in distributions())),
        }
        self._hashes = {}
        self.context = context or {}

    def path(self, relative):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError(f"La ruta sale del proyecto: {relative}")
        return path

    def fingerprint(self, relative):
        path = self.path(relative)
        stat = path.stat()
        if not path.is_file() or stat.st_size == 0:
            raise ValueError(f"Archivo ausente o vacío: {relative}")
        key = (str(path), stat.st_size, stat.st_mtime_ns)
        if key not in self._hashes:
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            self._hashes[key] = digest.hexdigest()
        return {"sha256": self._hashes[key], "size_bytes": stat.st_size}

    def fingerprints(self, files):
        return {relative: self.fingerprint(relative) for relative in files}

    def signature(self, stage):
        configuration = {name: json_read(self.path(name)) for name in stage.configs}
        sources = (stage.script, *stage.sources)
        return {
            "stage_version": 1,
            "recipe_sha256": canonical_sha(asdict(stage)),
            "config_sha256": canonical_sha(configuration),
            "sources": self.fingerprints(sources),
            "inputs": self.fingerprints(stage.inputs),
            "environment_sha256": canonical_sha(self.environment),
        }

    def validate_outputs(self, stage):
        outputs = self.fingerprints(stage.outputs)
        for filename in stage.outputs:
            if filename.endswith(".json"):
                report = json_read(self.path(filename))
                if not isinstance(report, dict):
                    raise ValueError(f"Reporte sin objeto JSON: {filename}")
                if filename in stage.json_versions and report.get("schema_version") != stage.json_versions[filename]:
                    raise ValueError(f"schema_version incompatible: {filename}")
                quality = report.get("quality_checks")
                if quality is not None and (not quality or not all(value is True for value in quality.values())):
                    raise ValueError(f"Controles no aprobados: {filename}")
                # Los reportes modernos ya publican huellas; se contrastan con
                # las entradas/salidas declaradas, además del recibo del DAG.
                for key, candidates in (("source", stage.inputs), ("training_input", stage.inputs), ("output", stage.outputs)):
                    identity = report.get(key)
                    if isinstance(identity, dict) and identity.get("sha256"):
                        digest = identity["sha256"].lower()
                        if not any(self.fingerprint(path)["sha256"] == digest for path in candidates):
                            raise ValueError(f"Identidad {key} incompatible: {filename}")
                model_id = report.get("model_id")
                models = [p for p in (*stage.inputs, *stage.outputs) if p.endswith(".joblib")]
                if model_id is not None and models and model_id not in [self.fingerprint(p)["sha256"] for p in models]:
                    raise ValueError(f"model_id incompatible: {filename}")
            elif filename.endswith(".parquet"):
                import pyarrow.parquet as pq
                parquet = pq.ParquetFile(self.path(filename))
                if parquet.metadata.num_rows == 0 or parquet.metadata.num_columns == 0:
                    raise ValueError(f"Parquet vacío: {filename}")
        return outputs

    def reusable(self, stage, signature):
        receipt = self.report_dir / "receipts" / (stage.name + ".json")
        try:
            saved = json_read(receipt)
            valid = (saved.get("schema_version") == self.SCHEMA_VERSION
                     and saved.get("signature") == signature
                     and saved.get("outputs") == self.validate_outputs(stage))
            return valid, "recibo y contratos verificados" if valid else "cambió configuración, código, entorno, entrada o salida"
        except (OSError, ValueError, KeyError):
            return False, "sin recibo verificable o artefacto incompatible; se reconstruye"

    def run_command(self, stage, log_path):
        environment = {**os.environ, **{name: "2" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}}
        try:
            import psutil
        except ImportError:
            psutil = None
        peak = None
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen([sys.executable, str(self.path(stage.script)), *stage.arguments],
                                       cwd=self.root, env=environment, stdout=log, stderr=subprocess.STDOUT)
            try:
                while True:
                    if psutil is not None:
                        try:
                            parent = psutil.Process(process.pid)
                            memory = sum(p.memory_info().rss for p in [parent, *parent.children(recursive=True)] if p.is_running())
                            peak = max(peak or 0, memory)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    if process.poll() is not None:
                        break
                    time.sleep(0.2)
            except BaseException:
                if psutil is not None:
                    try:
                        for child in psutil.Process(process.pid).children(recursive=True):
                            child.terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                process.terminate()
                process.wait()
                raise
        return process.returncode, peak

    def run(self, stages, selected, *, force=False):
        self.report_dir.mkdir(parents=True, exist_ok=True)
        manifest = {"schema_version": self.SCHEMA_VERSION, "run_id": uuid.uuid4().hex,
                    "started_at_utc": utc_now(), "environment": self.environment, "force": force,
                    "context": self.context,
                    "disk_free_bytes_at_start": shutil.disk_usage(self.root).free,
                    "status": "running", "selected": list(selected), "stages": [],
                    "memory_measurement": "RSS aproximado sumado de proceso e hijos, muestreado cada 0.2 s; null si no se midió"}
        run_logs = self.report_dir / "runs" / manifest["run_id"]
        run_logs.mkdir(parents=True, exist_ok=True)
        active = None
        try:
            ordered = dependency_order(stages, selected)
            for stage in ordered:
                for output in stage.outputs:
                    target = self.path(output)
                    if target.is_relative_to(self.root / "data/bronze") or target.is_relative_to(self.root / "docs"):
                        raise ValueError(f"Salida protegida (Bronze/documentación): {output}")
            manifest["planned_stages"] = [stage.name for stage in ordered]
            # Fallar antes de entrenar si se pide una entrega todavía ausente.
            unavailable = next((s for s in ordered if s.unavailable_reason and not s.optional), None)
            if unavailable:
                started = time.perf_counter()
                active = {"stage": unavailable.name, "dependencies": list(unavailable.dependencies),
                          "started_at_utc": utc_now(), "status": "failed",
                          "log": str((run_logs / (unavailable.name + ".log")).relative_to(self.root))}
                manifest["stages"].append(active)
                raise RuntimeError(unavailable.unavailable_reason)
            for stage in ordered:
                started = time.perf_counter()
                active = {"stage": stage.name, "dependencies": list(stage.dependencies),
                          "started_at_utc": utc_now(), "status": "failed",
                          "log": str((run_logs / (stage.name + ".log")).relative_to(self.root))}
                manifest["stages"].append(active)
                blocked = [s["stage"] for s in manifest["stages"][:-1]
                           if s["stage"] in stage.dependencies and s["status"] not in ("built", "reused")]
                if blocked and not stage.optional:
                    raise RuntimeError(f"Dependencias incompletas de {stage.name}: {', '.join(blocked)}")
                if blocked:
                    stage = Stage(**{**asdict(stage), "unavailable_reason": "Dependencias opcionales incompletas: " + ", ".join(blocked)})
                if stage.unavailable_reason:
                    if not stage.optional:
                        raise RuntimeError(stage.unavailable_reason)
                    active.update(status="skipped_optional", reason=stage.unavailable_reason)
                else:
                    signature = self.signature(stage)
                    active.update(signature)
                    reuse, reason = self.reusable(stage, signature)
                    active["reason"] = "--force solicitado" if force else reason
                    if reuse and not force:
                        active.update(status="reused", outputs=self.validate_outputs(stage), peak_rss_bytes=None)
                        self.path(active["log"]).write_text("Reutilizado: recibo, huellas y contratos verificados.\n", encoding="utf-8")
                    else:
                        if not stage.outputs:
                            raise ValueError(f"Etapa sin contrato de salidas: {stage.name}")
                        print(f"Preparando {stage.name}; log: {active['log']}", flush=True)
                        before = {p: self.path(p).stat().st_mtime_ns for p in stage.outputs if self.path(p).is_file()}
                        returncode, peak = self.run_command(stage, self.path(active["log"]))
                        active.update(returncode=returncode, peak_rss_bytes=peak)
                        if returncode:
                            raise RuntimeError(f"Falló {stage.name} (código {returncode}); revisar {active['log']}")
                        outputs = self.validate_outputs(stage)
                        if any(self.path(p).stat().st_mtime_ns == stamp for p, stamp in before.items()):
                            raise ValueError(f"{stage.name} no volvió a publicar todas sus salidas; no se aceptan restos antiguos")
                        # Una entrada modificada durante el proceso invalida la ejecución.
                        if self.signature(stage) != signature:
                            raise ValueError(f"Cambiaron entradas/configuración/código mientras corría {stage.name}")
                        active.update(status="built", outputs=outputs)
                        atomic_json(self.report_dir / "receipts" / (stage.name + ".json"),
                                    {"schema_version": self.SCHEMA_VERSION, "signature": signature,
                                     "outputs": outputs, "built_at_utc": utc_now()})
                active.update(finished_at_utc=utc_now(), duration_seconds=round(time.perf_counter() - started, 3))
                if active["status"] == "skipped_optional":
                    self.path(active["log"]).write_text(active["reason"] + "\n", encoding="utf-8")
                atomic_json(self.manifest_path, manifest)
                print(f"{stage.name}: {active['status']}", flush=True)
            manifest["status"] = "passed"
            return manifest
        except (Exception, KeyboardInterrupt) as exc:
            manifest.update(status="failed", error=str(exc) or "Ejecución interrumpida")
            if active is not None:
                active.update(status="failed", error=manifest["error"], finished_at_utc=utc_now(),
                              duration_seconds=round(time.perf_counter() - started, 3))
                log = self.path(active["log"])
                with log.open("a", encoding="utf-8") as stream:
                    stream.write("\n" + manifest["error"] + "\n")
            raise
        finally:
            manifest["finished_at_utc"] = utc_now()
            manifest["disk_free_bytes_at_finish"] = shutil.disk_usage(self.root).free
            manifest["duration_seconds"] = round((datetime.fromisoformat(manifest["finished_at_utc"])
                                                 - datetime.fromisoformat(manifest["started_at_utc"])).total_seconds(), 3)
            manifest["output_bytes"] = sum(item["size_bytes"] for stage in manifest["stages"] for item in stage.get("outputs", {}).values())
            atomic_json(self.manifest_path, manifest)
