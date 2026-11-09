"""Lectura validada del contrato D1 y procedencia de experimentos offline."""

import hashlib
import json
import platform
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import sklearn

from bankshield.transforms.analytical_transactions import (
    ANALYTICS_COLUMNS, ANALYTICS_SCHEMA, PARTITION_NAMES, apply_bins,
    assign_partitions, canonical_sha256, git_state, write_json_atomic,
)
from bankshield.transforms.silver_transactions import file_sha256
from bankshield.ingestion.paysim_profile import TRANSACTION_TYPES

ROOT = Path(__file__).resolve().parents[2]


def resolve(value, root=ROOT):
    path = Path(value)
    return path if path.is_absolute() else Path(root) / path


def strict_json(path):
    def invalid(value):
        raise ValueError(f"JSON no finito: {value}")
    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=invalid)


def digest(payload):
    return canonical_sha256(payload).lower()


def versions():
    return {"python": platform.python_version(), "numpy": np.__version__,
            "pandas": pd.__version__, "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__}


def provenance(paths):
    return {"git": git_state(ROOT), "versions": versions(), "code_sha256": {
        str(Path(path).resolve().relative_to(ROOT)).replace("\\", "/"): file_sha256(path).lower()
        for path in paths}}


class AnalyticalDataset:
    """Comprueba metadatos, huellas, valores, particiones y bins sin reajustar."""

    def __init__(self, path, dataset_report, discretization_report, chunksize=250_000):
        self.path = Path(path)
        self.report = strict_json(dataset_report)
        self.bins = strict_json(discretization_report)
        self.chunksize = chunksize
        if isinstance(chunksize, bool) or not isinstance(chunksize, int) or chunksize < 1:
            raise ValueError("chunksize debe ser un entero positivo")
        if self.report.get("schema_version") != 1 or self.bins.get("schema_version") != 1:
            raise ValueError("Versión D1 incompatible")
        checks = self.report.get("quality_checks", {})
        if not checks or not all(value is True for value in checks.values()):
            raise ValueError("D1 no tiene controles aprobados")
        self.dataset_sha256 = file_sha256(self.path).lower()
        self.source_sha256 = self.report["source"]["sha256"].lower()
        self.discretization_sha256 = self.report["discretization"]["sha256"].lower()
        if self.dataset_sha256 != self.report["output"]["sha256"].lower():
            raise ValueError("La huella del archivo D1 no coincide")
        for key, value in (("dataset_sha256", self.dataset_sha256),
                           ("source_sha256", self.source_sha256),
                           ("discretization_sha256", self.discretization_sha256)):
            if str(self.bins.get(key, "")).lower() != value:
                raise ValueError(f"Metadatos D1 incompatibles: {key}")
        canonical = {key: self.bins[key] for key in (
            "schema_version", "fit_partition", "fit_step_range", "interval_closure", "quantiles")}
        canonical["columns"] = {col: {key: spec[key] for key in (
            "interior_edges", "labels", "output_column")} for col, spec in self.bins["columns"].items()}
        if digest(canonical) != self.discretization_sha256:
            raise ValueError("Esquema de discretización alterado")
        if self.bins["fit_partition"] != "train" or self.bins["fit_step_range"] != {"min": 1, "max": 323}:
            raise ValueError("Bins deben estar ajustados solo en train 1-323")
        self.partitions = self.report["config"]["partitions"]
        if self.partitions != {"train": [1, 323], "validation": [324, 378],
                               "test": [379, 718], "stress": [719, 743]}:
            raise ValueError("Particiones D1 incompatibles con el protocolo")
        parquet = pq.ParquetFile(self.path)
        if not parquet.schema_arrow.equals(ANALYTICS_SCHEMA, check_metadata=False):
            raise ValueError("Esquema de columnas D1 incompatible")
        if parquet.metadata.num_rows != self.report["counts"]["rows_out"]:
            raise ValueError("Recuento D1 incompatible")
        self._stat = (self.path.stat().st_mtime_ns, self.path.stat().st_size)

    def batches(self, partition=None):
        if partition is not None and partition not in PARTITION_NAMES:
            raise ValueError("Partición desconocida")
        counts = dict.fromkeys(PARTITION_NAMES, 0)
        offset = 0
        for batch in pq.ParquetFile(self.path).iter_batches(batch_size=self.chunksize, columns=list(ANALYTICS_COLUMNS)):
            frame = batch.to_pandas()
            n = len(frame)
            if frame.isna().any().any():
                raise ValueError("D1 contiene nulos")
            if not np.array_equal(frame.row_id.to_numpy(), np.arange(offset + 1, offset + n + 1)):
                raise ValueError("row_id D1 no es ordinal, único y continuo")
            offset += n
            numeric = frame[["amount", "oldbalanceOrg"]].to_numpy()
            if not np.isfinite(numeric).all() or (numeric < 0).any():
                raise ValueError("Montos/saldos D1 inválidos")
            if not frame.type.isin(TRANSACTION_TYPES).all() or not frame.isFraud.isin([0, 1]).all():
                raise ValueError("Tipos/etiquetas D1 inválidos")
            if not frame.step.between(1, 743).all():
                raise ValueError("Steps D1 fuera de rango")
            if not np.array_equal(assign_partitions(frame.step.to_numpy(), 323, 378, 718), frame.partition):
                raise ValueError("Partición D1 incorrecta")
            for column, spec in self.bins["columns"].items():
                if not np.array_equal(apply_bins(frame[column].to_numpy(), spec["interior_edges"], spec["labels"]), frame[spec["output_column"]]):
                    raise ValueError("Bins D1 distintos del esquema ajustado")
            for name, nrows in frame.partition.value_counts().items():
                counts[name] += int(nrows)
            selected = frame if partition is None else frame.loc[frame.partition.eq(partition)]
            if len(selected):
                yield selected
        if any(counts[name] != self.report["partitions"][name]["rows"] for name in counts):
            raise ValueError("Recuentos por partición D1 incompatibles")
        if self._stat != (self.path.stat().st_mtime_ns, self.path.stat().st_size):
            raise ValueError("D1 cambió durante el experimento")

    def identity(self):
        return {"source_sha256": self.source_sha256, "dataset_sha256": self.dataset_sha256,
                "discretization_sha256": self.discretization_sha256, "partitions": self.partitions,
                "rows": {name: values["rows"] for name, values in self.report["partitions"].items()}}


def atomic_model(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        joblib.dump(payload, temporary, compress=3)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def validate_model_versions(saved):
    current = versions()
    for name in ("python", "scikit_learn", "numpy", "pandas", "joblib"):
        if saved.get(name, "").split(".")[:2] != current[name].split(".")[:2]:
            raise ValueError(f"Versión incompatible de {name}; regenerar el artefacto")
