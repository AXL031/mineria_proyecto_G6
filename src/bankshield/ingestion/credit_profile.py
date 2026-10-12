"""Perfil del CSV crediticio: calidad, etiqueta y variables sospechosas de fuga."""

import hashlib
import json
from pathlib import Path

import pandas as pd

from bankshield.features.credit import (CATEGORIES, MAX_PLAUSIBLE_AGE, MIN_WORKING_AGE,
                                        RAW_COLUMNS, invalid_reasons)


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_credit_csv(path):
    frame = pd.read_csv(path)
    if tuple(frame.columns) != RAW_COLUMNS:
        raise ValueError("La cabecera del CSV crediticio no coincide con el contrato")
    return frame


def profile_credit(path):
    path = Path(path)
    frame = read_credit_csv(path)
    rows = len(frame)
    status = frame["loan_status"]
    reasons = invalid_reasons(frame)
    numeric = frame.select_dtypes("number").drop(columns="loan_status")
    ratio = frame["loan_amnt"] / frame["person_income"]
    by_grade = frame.groupby("loan_grade").agg(
        rows=("loan_status", "size"), default_rate=("loan_status", "mean"),
        rate_min=("loan_int_rate", "min"), rate_max=("loan_int_rate", "max"),
        rate_missing=("loan_int_rate", lambda s: int(s.isna().sum())))
    grade_rate_corr = float(frame[["loan_int_rate", "loan_status"]].corr().iloc[0, 1])
    return {
        "schema_version": 1,
        "source": {"file": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)},
        "rows": rows,
        "columns": list(frame.columns),
        "label": {"column": "loan_status",
                  "counts": {str(k): int(v) for k, v in status.value_counts().sort_index().items()},
                  "positive_rate": float(status.mean()),
                  "meaning_status": "unconfirmed_documentation_assumes_1_is_default"},
        "missing": {name: int(v) for name, v in frame.isna().sum().items() if v},
        "missing_rate": {name: float(v / rows) for name, v in frame.isna().sum().items() if v},
        "exact_duplicate_rows": int(frame.duplicated().sum()),
        "numeric_summary": {
            name: {stat: float(numeric[name].agg(stat)) for stat in ("min", "median", "max")}
            for name in numeric.columns},
        "categories": {name: {str(k): int(v) for k, v in frame[name].value_counts().items()}
                       for name in CATEGORIES},
        "implausible": {
            "age_over_limit": int((frame["person_age"] > MAX_PLAUSIBLE_AGE).sum()),
            "emp_length_over_age_minus_14": int((frame["person_emp_length"]
                                                 > frame["person_age"] - MIN_WORKING_AGE).sum()),
            "rejected_by_validity_rules": int((reasons != "").sum()),
            "reasons": {k: int(v) for k, v in reasons[reasons != ""].value_counts().items()},
        },
        "percent_income_check": {
            "rows_differing_more_than_0_01": int(((ratio - frame["loan_percent_income"]).abs() > 0.01).sum()),
            "max_abs_difference": float((ratio - frame["loan_percent_income"]).abs().max()),
        },
        "default_rate_by_grade": {
            grade: {"rows": int(r["rows"]), "default_rate": float(r["default_rate"]),
                    "rate_min": None if pd.isna(r["rate_min"]) else float(r["rate_min"]),
                    "rate_max": None if pd.isna(r["rate_max"]) else float(r["rate_max"]),
                    "rate_missing": int(r["rate_missing"])}
            for grade, r in by_grade.iterrows()},
        "default_rate_by_rate_missing": {
            str(bool(k)): float(v) for k, v in
            frame.groupby(frame["loan_int_rate"].isna())["loan_status"].mean().items()},
        "leakage_signals": {"loan_int_rate_vs_label_correlation": grade_rate_corr},
        "temporal_information": "none: no date or customer key, so no temporal split is possible",
    }


def write_reports(profile, json_path, markdown_path=None):
    json_path = Path(json_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(profile, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    if markdown_path:
        Path(markdown_path).parent.mkdir(parents=True, exist_ok=True)
        Path(markdown_path).write_text(profile_markdown(profile), encoding="utf-8")


def profile_markdown(p):
    label, imp, pc = p["label"], p["implausible"], p["percent_income_check"]
    lines = [
        "# Perfil del dataset crediticio — Sevan", "",
        f"Fuente: `{p['source']['file']}` ({p['source']['bytes']:,} bytes), SHA-256 `{p['source']['sha256']}`. "
        "Generado por `scripts/profile_credit.py`; no modifica Bronze.", "",
        "## Resumen", "",
        f"- Filas: **{p['rows']:,}**; columnas: {len(p['columns'])}.",
        f"- Duplicados exactos: **{p['exact_duplicate_rows']:,}**.",
        f"- `loan_status`: 0 = {label['counts'].get('0', 0):,}; 1 = {label['counts'].get('1', 0):,} "
        f"({label['positive_rate']:.2%} positivos).",
        "- No hay fecha ni clave de cliente: la separación temporal o por cliente no es posible.", "",
        "## Semántica de `loan_status`", "",
        "El archivo no incluye diccionario. Se **asume** que 1 significa impago/default y 0 préstamo "
        "al corriente, coherente con la tasa por grado (A≈10 % … G≈98 %) y con la tasa positiva de 21.8 %. "
        "Una copia del dataset en OpenML (api.openml.org/d/43454) documenta 0 = sin impago y 1 = impago "
        "y reporta los mismos 895 nulos en `person_emp_length`. Es una fuente secundaria: no confirma "
        "procedencia ni licencia. Hasta verificarlo con la fuente original, el módulo habla de "
        "«clase positiva = impago asumido».", "",
        "## Valores faltantes", "", "| Columna | Faltantes | % |", "| --- | ---: | ---: |"]
    for name, count in p["missing"].items():
        lines.append(f"| `{name}` | {count:,} | {p['missing_rate'][name]:.2%} |")
    rate_missing = p["default_rate_by_rate_missing"]
    lines += ["", f"Tasa de clase positiva con `loan_int_rate` ausente: {rate_missing.get('True', float('nan')):.2%} "
              f"frente a {rate_missing.get('False', float('nan')):.2%} con valor. "
              "La ausencia es informativa, así que se conserva un indicador en vez de descartar filas.", "",
              "## Valores implausibles", "",
              f"- Edad mayor de 100 años: {imp['age_over_limit']}.",
              f"- Antigüedad laboral mayor que edad − 14: {imp['emp_length_over_age_minus_14']}.",
              f"- Filas rechazadas por las reglas de validez de Silver: **{imp['rejected_by_validity_rules']}** "
              f"({', '.join(f'{k}: {v}' for k, v in imp['reasons'].items()) or 'ninguna'}).",
              f"- `loan_percent_income` difiere más de 0.01 de `loan_amnt / person_income` en "
              f"{pc['rows_differing_more_than_0_01']:,} filas (máx. {pc['max_abs_difference']:.3f}); "
              "Silver recalcula la razón.", "",
              "## Grado y tasa: ¿variables disponibles al decidir?", "",
              "`loan_grade` y `loan_int_rate` las fija el prestamista **después** de evaluar el riesgo del "
              "solicitante. La tasa se solapa por grado y refleja el riesgo ya estimado, de modo que usarlas "
              "para «decidir» sería circular. El modelo principal las excluye y una variante comparativa las incluye.", "",
              "| Grado | Filas | Tasa positiva | Tasa mín. | Tasa máx. | Tasa ausente |",
              "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for grade, g in p["default_rate_by_grade"].items():
        lo = "—" if g["rate_min"] is None else f"{g['rate_min']:.2f}"
        hi = "—" if g["rate_max"] is None else f"{g['rate_max']:.2f}"
        lines.append(f"| {grade} | {g['rows']:,} | {g['default_rate']:.2%} | {lo} | {hi} | {g['rate_missing']:,} |")
    lines += ["", "## Estrategia de partición", "",
              "Sin fecha ni cliente, se usa una partición **aleatoria estratificada** 70/15/15 con semilla "
              "fija, después de eliminar duplicados exactos para que una misma fila no caiga en dos particiones. "
              "Limitación: no mide generalización temporal ni a clientes nuevos, y no se puede descartar que "
              "una misma persona aparezca varias veces con valores distintos. La métrica de prueba se reporta "
              "una sola vez, con modelo, calibración y umbral ya congelados.", ""]
    return "\n".join(lines)
