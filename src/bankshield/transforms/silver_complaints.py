"""Bronze → Silver de reclamos CFPB: tipos, rechazos trazables, duplicados y texto limpio."""

import json
from pathlib import Path

import pandas as pd

from bankshield.features.text_cleaning import RESIDUAL_REDACTION, clean_narrative, count_redactions
from bankshield.ingestion.complaints_profile import FIELDS, compute_sha256

SILVER_COLUMNS = (
    "row_id", "complaint_id", "date_received", "date_sent_to_company", "days_to_send",
    "sent_before_received", "product", "sub_product", "issue", "sub_issue", "company",
    "company_public_response", "company_response_to_consumer", "state", "zipcode",
    "zipcode_format_valid", "submitted_via", "timely_response", "consumer_disputed",
    "is_older_american", "is_servicemember", "consumer_consent_provided", "has_narrative",
    "narrative", "narrative_clean", "redaction_count", "clean_word_count", "narrative_is_repeated",
)

OPTIONAL_TEXT = ("sub_product", "sub_issue", "company_public_response", "state",
                 "consumer_consent_provided")
YES_NO = {"Yes": True, "No": False}


def read_complaints_csv(path):
    """Lee el CSV completo como texto, sin convertir vacíos en nulos."""
    frame = pd.read_csv(Path(path), dtype=str, keep_default_na=False, encoding="utf-8",
                        encoding_errors="replace")
    missing = set(FIELDS) - set(frame.columns)
    if missing:
        raise ValueError(f"Cabecera incompleta; faltan campos: {sorted(missing)}")
    return frame


def parse_dates(values):
    """MM/DD/YYYY, con YYYY-MM-DD como alternativa; lo no interpretable queda como NaT."""
    stripped = values.str.strip()
    parsed = pd.to_datetime(stripped, format="%m/%d/%Y", errors="coerce")
    return parsed.fillna(pd.to_datetime(stripped, format="%Y-%m-%d", errors="coerce"))


def reject_reasons(frame):
    """Serie con los motivos de rechazo separados por coma; vacía si la fila es válida."""
    ids = frame["complaint_id"].str.strip()
    received_text = frame["date_received"].str.strip()
    received = parse_dates(frame["date_received"])
    checks = {
        "missing:complaint_id": ids == "",
        "invalid:complaint_id": (ids != "") & ~ids.str.fullmatch(r"\d+"),
        "missing:date_received": received_text == "",
        "invalid:date_received": (received_text != "") & received.isna(),
        "missing:product": frame["product"].str.strip() == "",
    }
    reasons = pd.Series("", index=frame.index)
    for name, mask in checks.items():
        reasons = reasons.mask(mask, reasons + "," + name)
    return reasons.str.lstrip(",")


def _blank_to_na(series):
    stripped = series.str.strip()
    return stripped.where(stripped != "", None)


def transform_complaints(bronze):
    """Devuelve (silver, rechazadas, conteos). Nunca modifica el DataFrame recibido."""
    frame = bronze.copy()
    frame.insert(0, "bronze_row", range(len(frame)))
    reasons = reject_reasons(frame)
    rejected = frame[reasons != ""].assign(reject_reason=reasons[reasons != ""])
    valid = frame[reasons == ""]
    duplicated = valid["complaint_id"].str.strip().astype("int64").duplicated(keep="first")
    removed = valid[duplicated]
    unique = valid[~duplicated].reset_index(drop=True)

    out = pd.DataFrame({"row_id": unique["bronze_row"].astype("int64")})
    out["complaint_id"] = unique["complaint_id"].str.strip().astype("int64")
    out["date_received"] = parse_dates(unique["date_received"])
    out["date_sent_to_company"] = parse_dates(unique["date_sent_to_company"])
    delta = (out["date_sent_to_company"] - out["date_received"]).dt.days
    out["days_to_send"] = delta.astype("Int64")
    out["sent_before_received"] = (delta < 0).fillna(False).astype(bool)
    for column in ("product", "issue", "company", "company_response_to_consumer", "submitted_via"):
        out[column] = unique[column].str.strip()
    for column in OPTIONAL_TEXT:
        out[column] = _blank_to_na(unique[column])
    zipcode = _blank_to_na(unique["zipcode"])
    out["zipcode"] = zipcode
    out["zipcode_format_valid"] = zipcode.str.fullmatch(r"\d{5}|\d{3}[Xx]{2}").fillna(False).astype(bool)
    out["timely_response"] = unique["timely_response"].str.strip().map(YES_NO).astype("boolean")
    out["consumer_disputed"] = unique["consumer_disputed?"].str.strip().map(YES_NO).astype("boolean")
    tags = unique["tags"].fillna("")
    out["is_older_american"] = tags.str.contains("Older American", regex=False)
    out["is_servicemember"] = tags.str.contains("Servicemember", regex=False)

    narrative = _blank_to_na(unique["consumer_complaint_narrative"])
    out["has_narrative"] = narrative.notna()
    out["narrative"] = narrative
    # Los vacíos pueden llegar como None o NaN según la versión de pandas: se prueba con isna.
    out["narrative_clean"] = narrative.map(lambda t: None if pd.isna(t) else clean_narrative(t))
    out["redaction_count"] = narrative.map(lambda t: 0 if pd.isna(t) else count_redactions(t)).astype("int64")
    out["clean_word_count"] = out["narrative_clean"].map(
        lambda t: 0 if pd.isna(t) else len(t.split())).astype("int64")
    out["narrative_is_repeated"] = (out["has_narrative"] & narrative.duplicated(keep=False)).astype(bool)

    silver = out[list(SILVER_COLUMNS)]

    def narratives(df):
        return int((df["consumer_complaint_narrative"].str.strip() != "").sum())

    reason_counts = rejected["reject_reason"].str.split(",").explode().value_counts()
    counts = {
        "bronze_rows": len(bronze),
        "rejected_rows": len(rejected),
        "duplicate_ids_removed": int(duplicated.sum()),
        "silver_rows": len(silver),
        "reject_reasons": {k: int(v) for k, v in reason_counts.items()},
        "bronze_narratives": narratives(frame),
        "rejected_narratives": narratives(rejected),
        "duplicate_narratives": narratives(removed),
        "silver_narratives": int(silver["has_narrative"].sum()),
        "sent_before_received": int(silver["sent_before_received"].sum()),
        "sent_date_unparseable": int(silver["date_sent_to_company"].isna().sum()),
        "zipcode_format_invalid": int((silver["zipcode"].notna() & ~silver["zipcode_format_valid"]).sum()),
        "repeated_narratives": int(silver["narrative_is_repeated"].sum()),
        "redactions_total": int(silver["redaction_count"].sum()),
    }
    return silver, rejected, counts


def quality_checks(silver, counts):
    clean = silver["narrative_clean"].dropna()
    return {
        "expected_header": True,
        "row_accounting": counts["bronze_rows"] == counts["silver_rows"] + counts["rejected_rows"]
                          + counts["duplicate_ids_removed"],
        "complaint_ids_unique": bool(silver["complaint_id"].is_unique),
        "row_ids_unique": bool(silver["row_id"].is_unique),
        "dates_received_valid": bool(silver["date_received"].notna().all()),
        "narrative_accounting": counts["bronze_narratives"] == counts["silver_narratives"]
                                + counts["rejected_narratives"] + counts["duplicate_narratives"],
        "clean_text_only_with_narrative": bool(
            silver["narrative_clean"].notna().equals(silver["has_narrative"])),
        "no_residual_redaction": not bool(clean.str.contains(RESIDUAL_REDACTION).any()),
    }


def build_silver_complaints(input_path, output_path, quality_path, markdown_path=None):
    input_path, output_path = Path(input_path), Path(output_path)
    bronze = read_complaints_csv(input_path)
    silver, rejected, counts = transform_complaints(bronze)
    checks = quality_checks(silver, counts)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    silver.to_parquet(output_path, index=False)
    report = {
        "schema_version": 1, "scope": "complete_file",
        "source": {"file": input_path.name, "sha256": compute_sha256(input_path)},
        "output": {"file": output_path.name, "sha256": compute_sha256(output_path)},
        "counts": counts, "quality_checks": checks,
        "date_range": {"min": silver["date_received"].min().date().isoformat() if len(silver) else None,
                       "max": silver["date_received"].max().date().isoformat() if len(silver) else None},
        "rejected_examples": json.loads(rejected.head(10).to_json(orient="records")),
    }
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
    lines = ["# Calidad Silver de reclamos — Angel", "",
             f"Fuente Bronze SHA-256: `{r['source']['sha256']}`. Parquet SHA-256: `{r['output']['sha256']}`.", "",
             "| Concepto | Filas |", "| --- | ---: |",
             f"| Bronze | {c['bronze_rows']:,} |",
             f"| Rechazadas por validez | {c['rejected_rows']:,} |",
             f"| Duplicados de `complaint_id` eliminados | {c['duplicate_ids_removed']:,} |",
             f"| **Silver** | **{c['silver_rows']:,}** |", ""]
    if c["reject_reasons"]:
        lines += ["Motivos de rechazo: " + ", ".join(f"`{k}`: {v}" for k, v in c["reject_reasons"].items()) + ".", ""]
    else:
        lines += ["No hubo filas rechazadas.", ""]
    lines += [f"Rango de `date_received`: {r['date_range']['min']} a {r['date_range']['max']}.", "",
              "## Narrativas y marcas de calidad", "", "| Concepto | Valor |", "| --- | ---: |",
              f"| Narrativas en Bronze | {c['bronze_narratives']:,} |",
              f"| Narrativas en Silver | {c['silver_narratives']:,} |",
              f"| Narrativas repetidas exactamente (`narrative_is_repeated`) | {c['repeated_narratives']:,} |",
              f"| Elementos censurados reemplazados por marcador | {c['redactions_total']:,} |",
              f"| Envío anterior a recepción (`sent_before_received`, se conservan) | {c['sent_before_received']:,} |",
              f"| `date_sent_to_company` no interpretable | {c['sent_date_unparseable']:,} |",
              f"| `zipcode` con formato distinto de 5 dígitos o `123XX` | {c['zipcode_format_invalid']:,} |", "",
              "## Controles", "", "| Control | Resultado |", "| --- | --- |"]
    lines += [f"| `{k}` | {'aprobado' if v else 'FALLÓ'} |" for k, v in r["quality_checks"].items()]
    lines.append("")
    return "\n".join(lines)
