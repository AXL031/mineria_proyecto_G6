"""Bronze → Silver de crédito: validez, razón recalculada, duplicados y huellas."""

import json
from pathlib import Path

import pandas as pd

from bankshield.features.credit import invalid_reasons
from bankshield.ingestion.credit_profile import read_credit_csv, sha256_file

SILVER_COLUMNS = ("row_id", "person_age", "person_income", "person_home_ownership",
                  "person_emp_length", "loan_intent", "loan_grade", "loan_amnt",
                  "loan_int_rate", "loan_status", "loan_percent_income",
                  "cb_person_default_on_file", "cb_person_cred_hist_length",
                  "emp_length_missing", "int_rate_missing")


def transform_credit(bronze):
    """Devuelve (silver, rechazadas, conteos). Nunca modifica el DataFrame recibido."""
    frame = bronze.copy()
    frame.insert(0, "bronze_row", range(len(frame)))
    reasons = invalid_reasons(frame)
    rejected = frame[reasons != ""].assign(reject_reason=reasons[reasons != ""])
    valid = frame[reasons == ""]
    raw_columns = [c for c in bronze.columns]
    duplicated = valid.duplicated(subset=raw_columns, keep="first")
    unique = valid[~duplicated].copy()
    # Razón recalculada: el original está redondeado y difiere en algunas filas.
    unique["loan_percent_income"] = unique["loan_amnt"] / unique["person_income"]
    unique["emp_length_missing"] = unique["person_emp_length"].isna()
    unique["int_rate_missing"] = unique["loan_int_rate"].isna()
    unique = unique.reset_index(drop=True)
    unique.insert(0, "row_id", unique["bronze_row"].astype("int64"))
    silver = unique[list(SILVER_COLUMNS)].astype({"row_id": "int64", "loan_status": "int64"})
    counts = {"bronze_rows": len(bronze), "rejected_rows": len(rejected),
              "exact_duplicates_removed": int(duplicated.sum()), "silver_rows": len(silver),
              "reject_reasons": {k: int(v) for k, v in rejected["reject_reason"].value_counts().items()}}
    return silver, rejected, counts


def build_silver_credit(input_path, output_path, quality_path, markdown_path=None):
    input_path, output_path = Path(input_path), Path(output_path)
    bronze = read_credit_csv(input_path)
    silver, rejected, counts = transform_credit(bronze)
    checks = {
        "expected_header": True,
        "row_accounting": counts["bronze_rows"] == counts["silver_rows"] + counts["rejected_rows"]
                          + counts["exact_duplicates_removed"],
        "no_exact_duplicates_in_silver": not silver.drop(columns=["row_id"]).duplicated().any(),
        "labels_binary": bool(silver["loan_status"].isin([0, 1]).all()),
        "row_ids_unique": bool(silver["row_id"].is_unique),
        "ratio_matches_amount_over_income": bool(
            ((silver["loan_amnt"] / silver["person_income"] - silver["loan_percent_income"]).abs() < 1e-12).all()),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    silver.to_parquet(output_path, index=False)
    report = {"schema_version": 1, "scope": "complete_file",
              "source": {"file": input_path.name, "sha256": sha256_file(input_path)},
              "output": {"file": output_path.name, "sha256": sha256_file(output_path)},
              "counts": counts, "quality_checks": checks,
              "positive_rate": float(silver["loan_status"].mean()),
              "rejected_examples": json.loads(rejected.head(10).to_json(orient="records"))}
    Path(quality_path).parent.mkdir(parents=True, exist_ok=True)
    Path(quality_path).write_text(json.dumps(report, indent=2, allow_nan=False, default=str) + "\n",
                                  encoding="utf-8")
    if markdown_path:
        Path(markdown_path).parent.mkdir(parents=True, exist_ok=True)
        Path(markdown_path).write_text(quality_markdown(report), encoding="utf-8")
    if not all(checks.values()):
        raise ValueError(f"Fallaron controles de calidad: {[k for k, v in checks.items() if not v]}")
    return report


def quality_markdown(r):
    c = r["counts"]
    lines = ["# Calidad Silver de crédito — Sevan", "",
             f"Fuente Bronze SHA-256: `{r['source']['sha256']}`. Parquet SHA-256: `{r['output']['sha256']}`.", "",
             "| Concepto | Filas |", "| --- | ---: |",
             f"| Bronze | {c['bronze_rows']:,} |",
             f"| Rechazadas por validez | {c['rejected_rows']:,} |",
             f"| Duplicados exactos eliminados | {c['exact_duplicates_removed']:,} |",
             f"| **Silver** | **{c['silver_rows']:,}** |", ""]
    if c["reject_reasons"]:
        lines += ["Motivos de rechazo: " + ", ".join(f"`{k}`: {v}" for k, v in c["reject_reasons"].items()) + ".", ""]
    lines += ["Los rechazos son valores imposibles (p. ej. edad de 123–144 años o antigüedad laboral mayor "
              "que la edad); no se imputan. Los nulos de `person_emp_length` y `loan_int_rate` se conservan con "
              "indicador `*_missing`. `loan_percent_income` se recalcula como `loan_amnt / person_income`.", "",
              "## Controles", "", "| Control | Resultado |", "| --- | --- |"]
    lines += [f"| `{k}` | {'aprobado' if v else 'FALLÓ'} |" for k, v in r["quality_checks"].items()]
    lines += ["", f"Tasa de clase positiva en Silver: {r['positive_rate']:.2%}.", ""]
    return "\n".join(lines)
