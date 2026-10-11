"""Construcción del mart transaccional en Gold.

Parte del Parquet Silver y produce una tabla analítica con **una fila por
transacción**: identidad de la operación, los predictores del contrato de
fraude y dos residuos de balance descriptivos. No agrega por ``step`` (eso es
el Gold temporal de pronósticos) ni modifica Bronze o Silver.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from bankshield.features.fraud import MODEL_FEATURES, build_fraud_feature_frame
from bankshield.ingestion.paysim_profile import FIELDS
from bankshield.transforms.silver_transactions import file_sha256

REQUIRED_COLUMNS = tuple(FIELDS)
PREDICTOR_COLUMNS = tuple(MODEL_FEATURES)
DESCRIPTIVE_COLUMNS = ("origin_balance_delta", "destination_balance_delta")
GOLD_COLUMNS = (
    "step",
    "nameOrig",
    "nameDest",
    "type",
    "amount",
    "oldbalanceOrg",
    "amount_to_origin_balance",
    "exceeds_origin_balance",
    "origin_balance_delta",
    "destination_balance_delta",
    "isFraud",
    "isFlaggedFraud",
)

GOLD_SCHEMA = pa.schema(
    [
        ("step", pa.int64()),
        ("nameOrig", pa.string()),
        ("nameDest", pa.string()),
        ("type", pa.string()),
        ("amount", pa.float64()),
        ("oldbalanceOrg", pa.float64()),
        ("amount_to_origin_balance", pa.float64()),
        ("exceeds_origin_balance", pa.int8()),
        ("origin_balance_delta", pa.float64()),
        ("destination_balance_delta", pa.float64()),
        ("isFraud", pa.int8()),
        ("isFlaggedFraud", pa.int8()),
    ]
)


def transform_transactions(records: pd.DataFrame) -> pd.DataFrame:
    """Convierte un bloque Silver en su fila Gold de mart transaccional.

    Reutiliza ``build_fraud_feature_frame`` para los predictores, de modo que la
    lista de variables queda gobernada por el contrato de fraude y no se
    duplica. Los residuos de balance son descriptivos: usan los saldos
    posteriores y no deben emplearse como predictores antes de la operación.
    """
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(records.columns))
    if missing_columns:
        raise ValueError(f"Faltan columnas requeridas: {missing_columns}")
    if records.empty:
        raise ValueError("El dataset Silver está vacío")
    if records.loc[:, list(REQUIRED_COLUMNS)].isna().any().any():
        raise ValueError("Se encontraron valores ausentes en Silver")

    step = pd.to_numeric(records["step"], errors="raise")
    if not np.isfinite(step).all() or (step % 1 != 0).any() or (step < 0).any():
        raise ValueError("step debe contener enteros no negativos")
    for label in ("isFraud", "isFlaggedFraud"):
        values = pd.to_numeric(records[label], errors="raise")
        if not values.isin([0, 1]).all():
            raise ValueError(f"{label} debe contener únicamente 0 o 1")

    predictors = build_fraud_feature_frame(records)

    amount = pd.to_numeric(records["amount"], errors="raise").astype("float64")
    old_origin = pd.to_numeric(records["oldbalanceOrg"], errors="raise").astype("float64")
    new_origin = pd.to_numeric(records["newbalanceOrig"], errors="raise").astype("float64")
    old_destination = pd.to_numeric(records["oldbalanceDest"], errors="raise").astype("float64")
    new_destination = pd.to_numeric(records["newbalanceDest"], errors="raise").astype("float64")
    for name, values in (
        ("newbalanceOrig", new_origin),
        ("oldbalanceDest", old_destination),
        ("newbalanceDest", new_destination),
    ):
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError(f"{name}: valores ausentes, negativos o no finitos")

    gold = pd.DataFrame(index=records.index)
    gold["step"] = step.astype("int64")
    gold["nameOrig"] = records["nameOrig"].astype(str)
    gold["nameDest"] = records["nameDest"].astype(str)
    gold["type"] = predictors["type"].astype(str)
    gold["amount"] = predictors["amount"].astype("float64")
    gold["oldbalanceOrg"] = predictors["oldbalanceOrg"].astype("float64")
    gold["amount_to_origin_balance"] = predictors["amount_to_origin_balance"].astype("float64")
    gold["exceeds_origin_balance"] = predictors["exceeds_origin_balance"].astype("int8")
    gold["origin_balance_delta"] = (new_origin - (old_origin - amount)).astype("float64")
    gold["destination_balance_delta"] = (new_destination - (old_destination + amount)).astype("float64")
    gold["isFraud"] = pd.to_numeric(records["isFraud"], errors="raise").astype("int8")
    gold["isFlaggedFraud"] = pd.to_numeric(records["isFlaggedFraud"], errors="raise").astype("int8")
    return gold.loc[:, list(GOLD_COLUMNS)]


def _display_path(path: Path, base_dir: Path | None) -> str:
    if base_dir is None:
        return str(path)
    try:
        return str(Path(path).resolve().relative_to(Path(base_dir).resolve()))
    except ValueError:
        return str(path)


def _render_markdown(report: dict) -> str:
    counts = report["counts"]
    totals = report["totals"]
    checks = report["quality_checks"]
    lines = [
        "# Calidad del mart transaccional Gold",
        "",
        "Reporte generado por `scripts/build_gold_transactions.py`.",
        "",
        "## Entrada y salida",
        "",
        f"- Silver: `{report['source']['path']}`.",
        f"- Gold: `{report['output']['path']}`.",
        "- Grano: una fila por transacción.",
        "",
        "## Recuentos",
        "",
        "| Métrica | Valor |",
        "| --- | ---: |",
        f"| Transacciones de entrada | {counts['input_rows']:,} |",
        f"| Filas del mart Gold | {counts['output_rows']:,} |",
        "",
        "## Totales",
        "",
        "| Métrica | Valor |",
        "| --- | ---: |",
        f"| Monto total | {totals['amount']:,.2f} |",
        f"| Transacciones fraudulentas | {totals['fraud']:,} |",
        f"| Transacciones marcadas (`isFlaggedFraud`) | {totals['flagged']:,} |",
        f"| Residuos de balance origen distintos de cero | {totals['origin_residuals_nonzero']:,} |",
        f"| Residuos de balance destino distintos de cero | {totals['destination_residuals_nonzero']:,} |",
        "",
        "## Controles",
        "",
        "| Control | Resultado |",
        "| --- | --- |",
    ]
    for name, passed in checks.items():
        lines.append(f"| `{name}` | {'OK' if passed else 'REVISAR'} |")
    lines += [
        "",
        "## Predictores",
        "",
        "- Lista gobernada por el contrato de fraude: "
        + ", ".join(f"`{name}`" for name in report["predictor_columns"])
        + ".",
        "- `origin_balance_delta` y `destination_balance_delta` son descriptivos: "
        "usan saldos posteriores a la operación y quedan fuera de los predictores.",
        "",
        "## Limitaciones",
        "",
        "- `step` es una hora simulada, no una fecha calendario.",
        "- Los datos son sintéticos y los montos no tienen una moneda identificada.",
        "- Este mart no agrega actividad por `step`; el Gold temporal de "
        "pronósticos es una tabla distinta por módulo.",
        "- El mart conserva `isFraud` e `isFlaggedFraud` para evaluación; quedan "
        "fuera de cualquier conjunto de predictores.",
        "",
    ]
    return "\n".join(lines)


def build_gold_transactions(
    input_path: Path,
    output_path: Path,
    quality_json: Path | None = None,
    quality_markdown: Path | None = None,
    chunksize: int = 500_000,
    base_dir: Path | None = None,
) -> dict:
    """Lee Silver, escribe el mart transaccional Gold y devuelve su reporte."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    if not input_path.exists():
        raise ValueError(f"No existe el Parquet Silver: {input_path}")
    if chunksize < 1:
        raise ValueError("chunksize debe ser un entero positivo")

    parquet = pq.ParquetFile(input_path)
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(parquet.schema.names))
    if missing_columns:
        raise ValueError(
            f"El Parquet Silver no tiene las columnas requeridas: {missing_columns}"
        )
    source_sha = file_sha256(input_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")

    input_rows = 0
    output_rows = 0
    input_amount = 0.0
    output_amount = 0.0
    input_fraud = 0
    output_fraud = 0
    input_flagged = 0
    output_flagged = 0
    origin_residuals_nonzero = 0
    destination_residuals_nonzero = 0
    observed_steps: set[int] = set()

    writer = pq.ParquetWriter(tmp_path, GOLD_SCHEMA, compression="snappy")
    try:
        for batch in parquet.iter_batches(batch_size=chunksize):
            frame = batch.to_pandas()
            input_rows += len(frame)
            input_amount += float(pd.to_numeric(frame["amount"]).sum())
            input_fraud += int(pd.to_numeric(frame["isFraud"]).sum())
            input_flagged += int(pd.to_numeric(frame["isFlaggedFraud"]).sum())

            gold = transform_transactions(frame)
            output_rows += len(gold)
            output_amount += float(gold["amount"].sum())
            output_fraud += int(gold["isFraud"].sum())
            output_flagged += int(gold["isFlaggedFraud"].sum())
            origin_residuals_nonzero += int((gold["origin_balance_delta"] != 0).sum())
            destination_residuals_nonzero += int(
                (gold["destination_balance_delta"] != 0).sum()
            )
            observed_steps.update(int(step) for step in gold["step"].unique())

            writer.write_table(
                pa.Table.from_pandas(gold, schema=GOLD_SCHEMA, preserve_index=False)
            )
    except BaseException:
        writer.close()
        tmp_path.unlink(missing_ok=True)
        raise
    else:
        writer.close()

    if output_rows == 0:
        tmp_path.unlink(missing_ok=True)
        raise ValueError("El mart Gold quedaría sin registros")
    tmp_path.replace(output_path)

    checks = {
        "one_row_per_transaction": input_rows == output_rows,
        "predictors_present": set(PREDICTOR_COLUMNS).issubset(GOLD_COLUMNS),
        "amount_total_preserved": bool(
            np.isclose(input_amount, output_amount, rtol=1e-12, atol=0.01)
        ),
        "fraud_count_preserved": input_fraud == output_fraud,
        "flagged_count_preserved": input_flagged == output_flagged,
        "no_null_values": True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Fallaron controles de Gold: " + ", ".join(failed))

    report = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "path": _display_path(input_path, base_dir),
            "format": "parquet",
            "sha256": source_sha,
            "rows": input_rows,
            "columns_used": list(REQUIRED_COLUMNS),
        },
        "output": {
            "path": _display_path(output_path, base_dir),
            "sha256": file_sha256(output_path),
            "format": "parquet",
            "compression": "snappy",
            "rows": output_rows,
            "columns": list(GOLD_COLUMNS),
        },
        "counts": {
            "input_rows": input_rows,
            "output_rows": output_rows,
        },
        "totals": {
            "amount": output_amount,
            "fraud": output_fraud,
            "flagged": output_flagged,
            "origin_residuals_nonzero": origin_residuals_nonzero,
            "destination_residuals_nonzero": destination_residuals_nonzero,
        },
        "predictor_columns": list(PREDICTOR_COLUMNS),
        "descriptive_columns": list(DESCRIPTIVE_COLUMNS),
        "step_coverage": {
            "min": int(min(observed_steps)),
            "max": int(max(observed_steps)),
            "distinct": len(observed_steps),
        },
        "quality_checks": checks,
    }

    if quality_json is not None:
        quality_json = Path(quality_json)
        quality_json.parent.mkdir(parents=True, exist_ok=True)
        quality_json.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    if quality_markdown is not None:
        quality_markdown = Path(quality_markdown)
        quality_markdown.parent.mkdir(parents=True, exist_ok=True)
        quality_markdown.write_text(_render_markdown(report), encoding="utf-8")
    return report
