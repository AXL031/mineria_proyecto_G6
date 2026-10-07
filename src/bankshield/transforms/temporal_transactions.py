"""Construcción de la tabla Gold temporal para pronósticos.

La transformación parte del Parquet Silver, agrupa las transacciones por
``step`` y conserva una fila por hora simulada. No entrena modelos ni modifica
Bronze o Silver.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = ("step", "amount", "isFraud")
GOLD_COLUMNS = (
    "step",
    "transaction_count",
    "total_amount",
    "average_amount",
    "fraud_count",
    "fraud_rate",
)


def aggregate_temporal_transactions(transactions: pd.DataFrame) -> pd.DataFrame:
    """Agrupa transacciones Silver y devuelve una fila por ``step``.

    Si entre el menor y el mayor ``step`` faltara una hora, la incorpora con
    actividad cero. Así la serie mantiene una frecuencia regular.
    """
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(transactions.columns))
    if missing_columns:
        raise ValueError(f"Faltan columnas requeridas: {missing_columns}")
    if transactions.empty:
        raise ValueError("El dataset Silver está vacío")

    source = transactions.loc[:, list(REQUIRED_COLUMNS)].copy()
    step = pd.to_numeric(source["step"], errors="coerce")
    amount = pd.to_numeric(source["amount"], errors="coerce")
    fraud = pd.to_numeric(source["isFraud"], errors="coerce")

    if step.isna().any() or not np.isfinite(step).all():
        raise ValueError("Silver contiene valores de step inválidos")
    if (step % 1 != 0).any() or (step < 0).any():
        raise ValueError("step debe contener enteros no negativos")
    if amount.isna().any() or not np.isfinite(amount).all():
        raise ValueError("Silver contiene valores de amount inválidos")
    if (amount < 0).any():
        raise ValueError("amount no puede contener valores negativos")
    if fraud.isna().any() or not fraud.isin([0, 1]).all():
        raise ValueError("isFraud debe contener únicamente 0 o 1")

    source["step"] = step.astype("int64")
    source["amount"] = amount.astype("float64")
    source["isFraud"] = fraud.astype("int64")

    grouped = (
        source.groupby("step", sort=True, observed=True)
        .agg(
            transaction_count=("step", "size"),
            total_amount=("amount", "sum"),
            average_amount=("amount", "mean"),
            fraud_count=("isFraud", "sum"),
        )
    )

    complete_steps = pd.RangeIndex(
        int(grouped.index.min()), int(grouped.index.max()) + 1, name="step"
    )
    gold = grouped.reindex(complete_steps)
    for column in ("transaction_count", "total_amount", "fraud_count"):
        gold[column] = gold[column].fillna(0)
    gold["average_amount"] = gold["average_amount"].fillna(0.0)
    gold["fraud_rate"] = np.where(
        gold["transaction_count"] > 0,
        gold["fraud_count"] / gold["transaction_count"],
        0.0,
    )

    gold = gold.reset_index()
    gold["step"] = gold["step"].astype("int64")
    gold["transaction_count"] = gold["transaction_count"].astype("int64")
    gold["total_amount"] = gold["total_amount"].astype("float64")
    gold["average_amount"] = gold["average_amount"].astype("float64")
    gold["fraud_count"] = gold["fraud_count"].astype("int64")
    gold["fraud_rate"] = gold["fraud_rate"].astype("float64")
    return gold.loc[:, list(GOLD_COLUMNS)]


def _display_path(path: Path, base_dir: Path | None) -> str:
    if base_dir is None:
        return str(path)
    try:
        return str(path.resolve().relative_to(base_dir.resolve()))
    except ValueError:
        return str(path)


def _final_fraud_only_start(gold: pd.DataFrame) -> int | None:
    start: int | None = None
    for row in reversed(list(gold.itertuples(index=False))):
        if row.transaction_count > 0 and row.transaction_count == row.fraud_count:
            start = int(row.step)
        else:
            break
    return start


def _write_markdown(report: dict, path: Path) -> None:
    counts = report["counts"]
    steps = report["step_coverage"]
    checks = report["quality_checks"]
    lines = [
        "# Calidad de la tabla Gold temporal",
        "",
        "Reporte generado por `scripts/build_forecast_gold.py`.",
        "",
        "## Entrada y salida",
        "",
        f"- Silver: `{report['source']['path']}`.",
        f"- Gold: `{report['output']['path']}`.",
        "- Grano: una fila por `step` (hora simulada).",
        "",
        "## Recuentos",
        "",
        "| Métrica | Valor |",
        "| --- | ---: |",
        f"| Transacciones de entrada | {counts['input_transactions']:,} |",
        f"| Filas temporales Gold | {counts['gold_rows']:,} |",
        f"| Steps incorporados con actividad cero | {counts['filled_steps']:,} |",
        f"| Transacciones representadas en Gold | {counts['output_transactions']:,} |",
        "",
        "## Cobertura temporal",
        "",
        "| Métrica | Valor |",
        "| --- | ---: |",
        f"| Step mínimo | {steps['min']} |",
        f"| Step máximo | {steps['max']} |",
        f"| Steps observados en Silver | {steps['observed']} |",
        f"| Steps en Gold | {steps['gold']} |",
        f"| Inicio del tramo final solo fraude | {steps['final_fraud_only_start']} |",
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
        "## Totales",
        "",
        f"- Monto total: {report['totals']['amount']:,.2f}.",
        f"- Transacciones fraudulentas: {report['totals']['fraud']:,}.",
        "",
        "## Limitaciones",
        "",
        "- `step` es una hora simulada, no una fecha calendario.",
        "- Los datos son sintéticos y los montos no tienen una moneda identificada.",
        "- `fraud_count` y `fraud_rate` son variables descriptivas; no se usarán "
        "como información futura para predecir volumen.",
        "- El tramo final solo fraude debe analizarse por separado antes del "
        "backtesting.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_temporal_gold(
    input_path: Path,
    output_path: Path,
    quality_json: Path | None = None,
    quality_markdown: Path | None = None,
    base_dir: Path | None = None,
) -> dict:
    """Lee Silver, escribe Gold temporal y devuelve su reporte de calidad."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    if not input_path.exists():
        raise ValueError(f"No existe el Parquet Silver: {input_path}")

    transactions = pd.read_parquet(input_path, columns=list(REQUIRED_COLUMNS))
    observed_steps = set(pd.to_numeric(transactions["step"]).astype("int64"))
    gold = aggregate_temporal_transactions(transactions)

    input_rows = int(len(transactions))
    output_transactions = int(gold["transaction_count"].sum())
    input_amount = float(pd.to_numeric(transactions["amount"]).sum())
    output_amount = float(gold["total_amount"].sum())
    input_fraud = int(pd.to_numeric(transactions["isFraud"]).sum())
    output_fraud = int(gold["fraud_count"].sum())
    filled_steps = [
        int(step) for step in gold["step"] if int(step) not in observed_steps
    ]

    checks = {
        "one_row_per_step": not gold["step"].duplicated().any(),
        "regular_step_sequence": gold["step"].tolist()
        == list(range(int(gold["step"].min()), int(gold["step"].max()) + 1)),
        "transaction_count_preserved": input_rows == output_transactions,
        "amount_total_preserved": bool(
            np.isclose(input_amount, output_amount, rtol=1e-12, atol=0.01)
        ),
        "fraud_count_preserved": input_fraud == output_fraud,
        "no_null_values": not gold.isna().any().any(),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Fallaron controles de Gold: " + ", ".join(failed))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        gold.to_parquet(temporary, index=False, compression="snappy")
        temporary.replace(output_path)
    finally:
        if temporary.exists():
            temporary.unlink()

    report = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "path": _display_path(input_path, base_dir),
            "format": "parquet",
            "rows": input_rows,
            "columns_used": list(REQUIRED_COLUMNS),
        },
        "output": {
            "path": _display_path(output_path, base_dir),
            "format": "parquet",
            "compression": "snappy",
            "rows": int(len(gold)),
            "columns": list(GOLD_COLUMNS),
        },
        "counts": {
            "input_transactions": input_rows,
            "gold_rows": int(len(gold)),
            "filled_steps": len(filled_steps),
            "filled_step_values": filled_steps,
            "output_transactions": output_transactions,
        },
        "step_coverage": {
            "min": int(gold["step"].min()),
            "max": int(gold["step"].max()),
            "observed": len(observed_steps),
            "gold": int(len(gold)),
            "final_fraud_only_start": _final_fraud_only_start(gold),
        },
        "totals": {
            "amount": output_amount,
            "fraud": output_fraud,
        },
        "quality_checks": checks,
    }

    if quality_json is not None:
        quality_json = Path(quality_json)
        quality_json.parent.mkdir(parents=True, exist_ok=True)
        quality_json.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    if quality_markdown is not None:
        _write_markdown(report, Path(quality_markdown))
    return report
