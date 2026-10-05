"""Perfilado de PaySim en memoria acotada; no transforma Bronze."""

import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path


FIELDS = (
    "step", "type", "amount", "nameOrig", "oldbalanceOrg", "newbalanceOrig",
    "nameDest", "oldbalanceDest", "newbalanceDest", "isFraud", "isFlaggedFraud",
)
NUMERIC_FIELDS = (
    "amount", "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest",
)
TRANSACTION_TYPES = {"PAYMENT", "TRANSFER", "CASH_OUT", "DEBIT", "CASH_IN"}


def nonnegative_number(value: str, field: str) -> float:
    """Rechaza nulos, valores no finitos y cantidades negativas."""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field}: se esperaba un número") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{field}: se esperaba un número finito no negativo")
    return number


def validate_record(row: dict) -> tuple[dict, list[str]]:
    """Devuelve valores tipados e incidencias; no corrige registros."""
    values = {}
    issues = []
    if None in row:
        issues.append("extra_columns")
    for field in FIELDS:
        value = row.get(field)
        if value is None or not str(value).strip():
            issues.append(f"missing:{field}")
            continue
        if field in NUMERIC_FIELDS:
            try:
                values[field] = nonnegative_number(value, field)
            except ValueError:
                issues.append(f"invalid:{field}")
        elif field in ("step", "isFraud", "isFlaggedFraud"):
            try:
                number = int(value)
                if number < 0 or (field != "step" and number not in (0, 1)):
                    raise ValueError
                values[field] = number
            except (TypeError, ValueError):
                issues.append(f"invalid:{field}")
        elif field == "type" and value not in TRANSACTION_TYPES:
            issues.append("invalid:type")
        else:
            values[field] = value
    return values, issues


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def summarize_steps(steps: list[dict]) -> dict:
    """Detecta periodos de una sola clase para revisar la división temporal."""
    normal_steps = [item["step"] for item in steps if item["rows"] > item["fraud"]]
    fraud_steps = [item["step"] for item in steps if item["fraud"] > 0]
    fraud_only = [item for item in steps if item["rows"] == item["fraud"]]
    return {
        "distinct_steps": len(steps),
        "last_step_with_nonfraud": max(normal_steps) if normal_steps else None,
        "last_step_with_fraud": max(fraud_steps) if fraud_steps else None,
        "fraud_only_steps": len(fraud_only),
        "rows_in_fraud_only_steps": sum(item["rows"] for item in fraud_only),
    }


def profile_paysim(path: Path, limit: int | None = None) -> dict:
    """Perfila todos los registros o una muestra inicial explícita."""
    path = Path(path)
    if limit is not None and limit < 1:
        raise ValueError("El límite debe ser un entero positivo")
    missing = Counter({field: 0 for field in FIELDS})
    issues = Counter()
    labels = Counter({"0": 0, "1": 0})
    types = Counter()
    fraud_types = Counter()
    steps = Counter()
    fraud_steps = Counter()
    flag_pairs = Counter()
    stats = {field: {"count": 0, "min": None, "max": None, "sum": 0.0}
             for field in NUMERIC_FIELDS}
    rows = invalid = 0
    truncated = False
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, strict=True)
        header = reader.fieldnames or []
        if header and header[0].startswith("version https://git-lfs.github.com"):
            raise ValueError("El archivo es una referencia Git LFS, no el CSV completo")
        if len(header) != len(FIELDS) or set(header) != set(FIELDS):
            raise ValueError(f"Cabecera PaySim inesperada: {header}")
        for row in reader:
            if limit is not None and rows >= limit:
                truncated = True
                break
            rows += 1
            for field in FIELDS:
                if row.get(field) is None or not row[field].strip():
                    missing[field] += 1
            values, row_issues = validate_record(row)
            if row_issues:
                invalid += 1
                issues.update(row_issues)
                continue
            label, tx_type, step = values["isFraud"], values["type"], values["step"]
            labels[str(label)] += 1
            types[tx_type] += 1
            fraud_types[tx_type] += label
            steps[step] += 1
            fraud_steps[step] += label
            flag_pairs[f"fraud={label},flagged={values['isFlaggedFraud']}"] += 1
            for field, summary in stats.items():
                number = values[field]
                summary["count"] += 1
                summary["sum"] += number
                summary["min"] = number if summary["min"] is None else min(summary["min"], number)
                summary["max"] = number if summary["max"] is None else max(summary["max"], number)
    if rows == 0:
        raise ValueError("El CSV no contiene registros")
    for summary in stats.values():
        summary["mean"] = summary.pop("sum") / summary["count"] if summary["count"] else None
    valid = rows - invalid
    step_rows = [{"step": step, "rows": steps[step], "fraud": fraud_steps[step]}
                 for step in sorted(steps)]
    return {
        "schema_version": 1,
        "source": {"file": path.name, "bytes": path.stat().st_size, "sha256": _sha256(path)},
        "scope": "first_rows_sample" if truncated else "complete_file",
        "row_limit": limit,
        "rows": rows,
        "valid_rows": valid,
        "invalid_rows": invalid,
        "missing_by_column": dict(missing),
        "issues": dict(sorted(issues.items())),
        "label_counts": dict(labels),
        "fraud_rate_valid_rows": labels["1"] / valid if valid else None,
        "numeric_summary_valid_rows": stats,
        "by_type": {kind: {"rows": count, "fraud": fraud_types[kind],
                             "fraud_rate": fraud_types[kind] / count}
                    for kind, count in sorted(types.items())},
        "by_step": step_rows,
        "temporal_summary": summarize_steps(step_rows),
        "fraud_vs_flagged": dict(sorted(flag_pairs.items())),
        "not_measured": ["exact_duplicate_rows", "unique_accounts", "numeric_quantiles"],
    }


def write_reports(profile: dict, json_path: Path, markdown_path: Path | None = None) -> None:
    """Guarda evidencia agregada, sin publicar identificadores de cuentas."""
    json_path = Path(json_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                         encoding="utf-8")
    if markdown_path is None:
        return
    rate = profile["fraud_rate_valid_rows"]
    lines = [
        "# Perfil de PaySim — módulo de fraude", "",
        "Informe generado por `scripts/profile_fraud.py`. Los originales no se modifican.", "",
        f"- Archivo: `{profile['source']['file']}`.",
        f"- SHA-256: `{profile['source']['sha256']}`.",
        f"- Alcance: `{profile['scope']}`; registros leídos: {profile['rows']:,}.",
        f"- Registros válidos: {profile['valid_rows']:,}; inválidos: {profile['invalid_rows']:,}.",
        f"- Fraudes: {profile['label_counts']['1']:,}; operaciones etiquetadas como no fraudulentas: {profile['label_counts']['0']:,}.",
        f"- Prevalencia de fraude en registros válidos: {rate:.6%}." if rate is not None else "- Sin registros válidos para calcular prevalencia.",
        "", "## Fraude por tipo", "",
        "| Tipo | Registros válidos | Fraudes | Prevalencia |", "| --- | ---: | ---: | ---: |",
    ]
    for kind, group in profile["by_type"].items():
        lines.append(f"| {kind} | {group['rows']:,} | {group['fraud']:,} | {group['fraud_rate']:.6%} |")
    lines += ["", "## Calidad", "", "| Columna | Valores ausentes |", "| --- | ---: |"]
    lines += [f"| `{field}` | {count:,} |" for field, count in profile["missing_by_column"].items()]
    lines += ["", "Incidencias detectadas: `" + json.dumps(profile["issues"], ensure_ascii=False) + "`.",
              "", "## Rangos numéricos de registros válidos", "",
              "| Campo | Mínimo | Máximo | Media |", "| --- | ---: | ---: | ---: |"]
    for field, summary in profile["numeric_summary_valid_rows"].items():
        lines.append(f"| `{field}` | {summary['min']} | {summary['max']} | {summary['mean']} |")
    steps = profile["by_step"]
    if steps:
        lines += ["", "## Cobertura de simulación", "",
                  f"Se observan {len(steps)} pasos distintos, desde {steps[0]['step']} hasta {steps[-1]['step']}. "
                  "El JSON contiene los recuentos y fraudes de cada paso. `step` no representa una fecha calendario."]
        temporal = profile["temporal_summary"]
        lines += ["",
                  f"Hay {temporal['fraud_only_steps']} pasos que contienen únicamente fraude "
                  f"({temporal['rows_in_fraud_only_steps']:,} registros). El último paso con operaciones "
                  f"no fraudulentas es {temporal['last_step_with_nonfraud']}. "
                  "Antes de fijar los cortes temporales hay que revisar clases y prevalencia por partición. "
                  "No se eliminarán periodos en función de sus etiquetas para mejorar métricas."]
    lines += ["", "## Límites del perfil", "",
              "Los recuentos por tipo, etiqueta, paso y rangos excluyen registros inválidos. "
              "La ausencia de incidencias no demuestra que no haya duplicados: este perfil no mide "
              "duplicados exactos, cuentas únicas ni cuantiles. La procedencia y licencia siguen pendientes de confirmación.",
              "", "## Uso para modelado", "",
              "Consultar el [contrato de variables](contrato-variables.md). Usar `step` para separar periodos "
              "y comprobar fraude en cada partición antes de entrenar. La etiqueta queda fuera de las variables; "
              "los saldos posteriores y `isFlaggedFraud` también se excluyen del primer modelo."]
    markdown_path = Path(markdown_path)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
