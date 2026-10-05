"""Genera un perfil reproducible del CSV transaccional PaySim.

El script procesa el archivo por bloques para no cargar todas sus columnas
simultáneamente en memoria. Solo lee Bronze y escribe reportes; nunca modifica
el CSV original.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    REPOSITORY_ROOT
    / "data"
    / "bronze"
    / "transactions"
    / "PS_20174392719_1491204439457_log.csv"
)
DEFAULT_JSON_OUTPUT = (
    REPOSITORY_ROOT / "artifacts" / "reports" / "transactions_profile.json"
)
DEFAULT_MARKDOWN_OUTPUT = (
    REPOSITORY_ROOT / "docs" / "pronosticos" / "calidad-paysim.md"
)

EXPECTED_COLUMNS = (
    "step",
    "type",
    "amount",
    "nameOrig",
    "oldbalanceOrg",
    "newbalanceOrig",
    "nameDest",
    "oldbalanceDest",
    "newbalanceDest",
    "isFraud",
    "isFlaggedFraud",
)

NUMERIC_COLUMNS = (
    "step",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "isFraud",
    "isFlaggedFraud",
)

EXPECTED_TRANSACTION_TYPES = {
    "CASH_IN",
    "CASH_OUT",
    "DEBIT",
    "PAYMENT",
    "TRANSFER",
}

PERCENTILES = (0.25, 0.50, 0.75, 0.95, 0.99, 0.999)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Perfila el CSV transaccional PaySim sin modificar Bronze."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"CSV de entrada. Valor predeterminado: {DEFAULT_INPUT}",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=DEFAULT_JSON_OUTPUT,
        help=f"Reporte JSON. Valor predeterminado: {DEFAULT_JSON_OUTPUT}",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=DEFAULT_MARKDOWN_OUTPUT,
        help=f"Resumen Markdown. Valor predeterminado: {DEFAULT_MARKDOWN_OUTPUT}",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=500_000,
        help="Filas leídas en cada bloque. Valor predeterminado: 500000.",
    )
    return parser.parse_args()


def file_sha256(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def blank_mask(series: pd.Series) -> pd.Series:
    return series.isna() | series.fillna("").str.strip().eq("")


def finite_numeric(series: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    missing = blank_mask(series)
    numeric = pd.to_numeric(series.mask(missing), errors="coerce")
    invalid = ~missing & numeric.isna()
    non_finite = numeric.notna() & ~np.isfinite(numeric)
    numeric = numeric.mask(non_finite)
    return numeric, invalid, non_finite


def update_numeric_range(
    ranges: dict[str, dict[str, float | None]], column: str, values: pd.Series
) -> None:
    valid = values.dropna()
    if valid.empty:
        return

    current_min = float(valid.min())
    current_max = float(valid.max())
    stored = ranges[column]
    stored["min"] = (
        current_min if stored["min"] is None else min(stored["min"], current_min)
    )
    stored["max"] = (
        current_max if stored["max"] is None else max(stored["max"], current_max)
    )


def profile_csv(path: Path, chunksize: int) -> dict[str, Any]:
    if chunksize <= 0:
        raise ValueError("chunksize debe ser un entero positivo")
    if not path.is_file():
        raise FileNotFoundError(f"No se encontró el CSV: {path}")

    header = pd.read_csv(path, nrows=0).columns.tolist()
    missing_columns = sorted(set(EXPECTED_COLUMNS) - set(header))
    extra_columns = sorted(set(header) - set(EXPECTED_COLUMNS))
    if missing_columns:
        raise ValueError(
            "El CSV no contiene todas las columnas requeridas: "
            + ", ".join(missing_columns)
        )

    row_count = 0
    null_counts: Counter[str] = Counter()
    invalid_numeric_counts: Counter[str] = Counter()
    non_finite_counts: Counter[str] = Counter()
    numeric_ranges = {
        column: {"min": None, "max": None} for column in NUMERIC_COLUMNS
    }
    transaction_type_counts: Counter[str] = Counter()
    unexpected_type_counts: Counter[str] = Counter()
    fraud_value_counts: Counter[str] = Counter()
    flagged_value_counts: Counter[str] = Counter()
    origin_prefix_counts: Counter[str] = Counter()
    destination_prefix_counts: Counter[str] = Counter()
    invalid_integer_steps = 0
    non_positive_steps = 0
    negative_amounts = 0
    zero_amounts = 0
    amount_values: list[np.ndarray] = []
    row_hashes: list[np.ndarray] = []
    step_stats: dict[int, dict[str, float | int]] = defaultdict(
        lambda: {
            "transaction_count": 0,
            "valid_amount_count": 0,
            "total_amount": 0.0,
            "fraud_count": 0,
        }
    )

    reader = pd.read_csv(
        path,
        dtype="string",
        chunksize=chunksize,
        keep_default_na=True,
        low_memory=False,
    )

    for chunk in reader:
        row_count += len(chunk)
        selected = chunk.loc[:, list(EXPECTED_COLUMNS)]

        row_hashes.append(
            pd.util.hash_pandas_object(
                selected, index=False, categorize=False
            ).to_numpy(dtype=np.uint64)
        )

        numeric_values: dict[str, pd.Series] = {}
        for column in EXPECTED_COLUMNS:
            null_counts[column] += int(blank_mask(selected[column]).sum())

        for column in NUMERIC_COLUMNS:
            numeric, invalid, non_finite = finite_numeric(selected[column])
            numeric_values[column] = numeric
            invalid_numeric_counts[column] += int(invalid.sum())
            non_finite_counts[column] += int(non_finite.sum())
            update_numeric_range(numeric_ranges, column, numeric)

        normalized_types = selected["type"].fillna("<missing>").str.strip()
        type_counts = normalized_types.value_counts(dropna=False)
        transaction_type_counts.update(
            {str(key): int(value) for key, value in type_counts.items()}
        )
        unexpected = normalized_types[~normalized_types.isin(EXPECTED_TRANSACTION_TYPES)]
        unexpected_type_counts.update(
            {str(key): int(value) for key, value in unexpected.value_counts().items()}
        )

        for values, counter in (
            (numeric_values["isFraud"], fraud_value_counts),
            (numeric_values["isFlaggedFraud"], flagged_value_counts),
        ):
            counter.update(
                {
                    str(int(key)) if float(key).is_integer() else str(float(key)): int(value)
                    for key, value in values.value_counts(dropna=True).items()
                }
            )

        origin_prefix_counts.update(
            {
                str(key): int(value)
                for key, value in selected["nameOrig"]
                .fillna("<missing>")
                .str.strip()
                .str[:1]
                .replace("", "<missing>")
                .value_counts()
                .items()
            }
        )
        destination_prefix_counts.update(
            {
                str(key): int(value)
                for key, value in selected["nameDest"]
                .fillna("<missing>")
                .str.strip()
                .str[:1]
                .replace("", "<missing>")
                .value_counts()
                .items()
            }
        )

        step = numeric_values["step"]
        valid_step_number = step.notna()
        integer_step = valid_step_number & step.mod(1).eq(0)
        invalid_integer_steps += int((valid_step_number & ~integer_step).sum())
        non_positive_steps += int((integer_step & step.le(0)).sum())
        valid_step = integer_step & step.gt(0)

        amount = numeric_values["amount"]
        negative_amounts += int(amount.lt(0).sum())
        zero_amounts += int(amount.eq(0).sum())
        valid_amount_array = amount.dropna().to_numpy(dtype=np.float64)
        if valid_amount_array.size:
            amount_values.append(valid_amount_array)

        fraud = numeric_values["isFraud"]
        valid_binary_fraud = fraud.where(fraud.isin((0, 1)))

        temporal = pd.DataFrame(
            {
                "step": step.where(valid_step),
                "amount": amount,
                "isFraud": valid_binary_fraud,
            }
        ).dropna(subset=["step"])
        temporal["step"] = temporal["step"].astype("int64")

        grouped = temporal.groupby("step", sort=False).agg(
            transaction_count=("step", "size"),
            valid_amount_count=("amount", "count"),
            total_amount=("amount", "sum"),
            fraud_count=("isFraud", "sum"),
        )
        for step_value, values in grouped.iterrows():
            stored = step_stats[int(step_value)]
            stored["transaction_count"] += int(values["transaction_count"])
            stored["valid_amount_count"] += int(values["valid_amount_count"])
            stored["total_amount"] += float(values["total_amount"])
            stored["fraud_count"] += int(values["fraud_count"])

    all_hashes = np.concatenate(row_hashes) if row_hashes else np.array([], dtype=np.uint64)
    _, hash_frequencies = np.unique(all_hashes, return_counts=True)
    duplicate_rows_by_hash = int(np.maximum(hash_frequencies - 1, 0).sum())

    all_amounts = (
        np.concatenate(amount_values) if amount_values else np.array([], dtype=np.float64)
    )
    amount_summary: dict[str, float | int | None] = {
        "valid_count": int(all_amounts.size),
        "min": None,
        "max": None,
        "mean": None,
        "median": None,
        "std": None,
        "sum": None,
        "percentiles": {},
    }
    if all_amounts.size:
        quantiles = np.quantile(all_amounts, PERCENTILES)
        amount_summary.update(
            {
                "min": float(all_amounts.min()),
                "max": float(all_amounts.max()),
                "mean": float(all_amounts.mean()),
                "median": float(np.median(all_amounts)),
                "std": float(all_amounts.std(ddof=1)),
                "sum": float(all_amounts.sum()),
                "percentiles": {
                    f"p{percentile * 100:g}": float(value)
                    for percentile, value in zip(PERCENTILES, quantiles, strict=True)
                },
            }
        )

    sorted_steps = sorted(step_stats)
    missing_steps: list[int] = []
    if sorted_steps:
        missing_steps = sorted(
            set(range(sorted_steps[0], sorted_steps[-1] + 1)) - set(sorted_steps)
        )

    per_step: list[dict[str, float | int]] = []
    for step_value in sorted_steps:
        values = step_stats[step_value]
        transaction_count = int(values["transaction_count"])
        valid_amount_count = int(values["valid_amount_count"])
        fraud_count = int(values["fraud_count"])
        per_step.append(
            {
                "step": step_value,
                "transaction_count": transaction_count,
                "valid_amount_count": valid_amount_count,
                "total_amount": float(values["total_amount"]),
                "average_amount": (
                    float(values["total_amount"]) / valid_amount_count
                    if valid_amount_count
                    else None
                ),
                "fraud_count": fraud_count,
                "fraud_rate": fraud_count / transaction_count if transaction_count else None,
            }
        )

    final_fraud_only_start: int | None = None
    for values in reversed(per_step):
        if values["transaction_count"] == values["fraud_count"]:
            final_fraud_only_start = int(values["step"])
        else:
            break

    invalid_binary_fraud = sum(
        value for key, value in fraud_value_counts.items() if key not in {"0", "1"}
    )
    invalid_binary_flagged = sum(
        value for key, value in flagged_value_counts.items() if key not in {"0", "1"}
    )

    quality_checks = {
        "expected_header": header == list(EXPECTED_COLUMNS),
        "no_missing_columns": not missing_columns,
        "no_extra_columns": not extra_columns,
        "no_null_or_blank_values": sum(null_counts.values()) == 0,
        "numeric_columns_parse": sum(invalid_numeric_counts.values()) == 0,
        "numeric_columns_are_finite": sum(non_finite_counts.values()) == 0,
        "known_transaction_types": sum(unexpected_type_counts.values()) == 0,
        "steps_are_positive_integers": invalid_integer_steps == 0
        and non_positive_steps == 0,
        "continuous_step_range": not missing_steps,
        "amounts_are_non_negative": negative_amounts == 0,
        "fraud_flags_are_binary": invalid_binary_fraud == 0
        and invalid_binary_flagged == 0,
    }

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": file_sha256(path),
        },
        "schema": {
            "columns": header,
            "expected_columns": list(EXPECTED_COLUMNS),
            "missing_columns": missing_columns,
            "extra_columns": extra_columns,
            "order_matches": header == list(EXPECTED_COLUMNS),
        },
        "row_count": row_count,
        "null_or_blank_counts": dict(null_counts),
        "invalid_numeric_counts": dict(invalid_numeric_counts),
        "non_finite_numeric_counts": dict(non_finite_counts),
        "numeric_ranges": numeric_ranges,
        "duplicate_rows_by_hash": duplicate_rows_by_hash,
        "duplicate_detection_method": (
            "Comparación de hashes pandas de 64 bits sobre las 11 columnas."
        ),
        "transaction_type_counts": dict(transaction_type_counts),
        "unexpected_type_counts": dict(unexpected_type_counts),
        "fraud_value_counts": dict(fraud_value_counts),
        "flagged_fraud_value_counts": dict(flagged_value_counts),
        "origin_prefix_counts": dict(origin_prefix_counts),
        "destination_prefix_counts": dict(destination_prefix_counts),
        "step_quality": {
            "invalid_non_integer": invalid_integer_steps,
            "non_positive": non_positive_steps,
            "min": sorted_steps[0] if sorted_steps else None,
            "max": sorted_steps[-1] if sorted_steps else None,
            "distinct_count": len(sorted_steps),
            "missing_steps": missing_steps,
            "final_fraud_only_start": final_fraud_only_start,
        },
        "amount_quality": {
            "negative_count": negative_amounts,
            "zero_count": zero_amounts,
            **amount_summary,
        },
        "per_step": per_step,
        "quality_checks": quality_checks,
    }


def format_number(value: float | int | None, decimals: int = 2) -> str:
    if value is None:
        return "n.a."
    if isinstance(value, int):
        return f"{value:,}"
    if not math.isfinite(value):
        return "n.a."
    return f"{value:,.{decimals}f}"


def render_markdown(profile: dict[str, Any]) -> str:
    checks = profile["quality_checks"]
    amount = profile["amount_quality"]
    step_quality = profile["step_quality"]
    per_step = profile["per_step"]

    lines = [
        "# Perfil de calidad — PaySim",
        "",
        "## Fuente",
        "",
        f"- Archivo: `{Path(profile['source']['path']).name}`",
        f"- Tamaño: {profile['source']['size_bytes']:,} bytes",
        f"- SHA-256: `{profile['source']['sha256']}`",
        f"- Filas: {profile['row_count']:,}",
        f"- Columnas: {len(profile['schema']['columns'])}",
        "",
        "## Controles principales",
        "",
        "| Control | Resultado |",
        "| --- | --- |",
    ]
    for name, passed in checks.items():
        lines.append(f"| `{name}` | {'OK' if passed else 'REVISAR'} |")

    lines.extend(
        [
            "",
            "## Valores nulos o vacíos",
            "",
            "| Columna | Cantidad |",
            "| --- | ---: |",
        ]
    )
    for column in EXPECTED_COLUMNS:
        lines.append(
            f"| `{column}` | {profile['null_or_blank_counts'].get(column, 0):,} |"
        )

    lines.extend(
        [
            "",
            "## Tipos de transacción",
            "",
            "| Tipo | Cantidad | Porcentaje |",
            "| --- | ---: | ---: |",
        ]
    )
    for transaction_type, count in sorted(
        profile["transaction_type_counts"].items(), key=lambda item: -item[1]
    ):
        percentage = count / profile["row_count"] if profile["row_count"] else 0
        lines.append(
            f"| `{transaction_type}` | {count:,} | {percentage:.3%} |"
        )

    percentiles = amount["percentiles"]
    lines.extend(
        [
            "",
            "## Distribución de `amount`",
            "",
            "| Métrica | Valor |",
            "| --- | ---: |",
            f"| Mínimo | {format_number(amount['min'])} |",
            f"| Promedio | {format_number(amount['mean'])} |",
            f"| Mediana | {format_number(amount['median'])} |",
            f"| Percentil 95 | {format_number(percentiles.get('p95'))} |",
            f"| Percentil 99 | {format_number(percentiles.get('p99'))} |",
            f"| Percentil 99.9 | {format_number(percentiles.get('p99.9'))} |",
            f"| Máximo | {format_number(amount['max'])} |",
            f"| Montos negativos | {amount['negative_count']:,} |",
            f"| Montos iguales a cero | {amount['zero_count']:,} |",
            "",
            "## Etiquetas",
            "",
            "| Campo | Valor 0 | Valor 1 |",
            "| --- | ---: | ---: |",
            (
                "| `isFraud` | "
                f"{profile['fraud_value_counts'].get('0', 0):,} | "
                f"{profile['fraud_value_counts'].get('1', 0):,} |"
            ),
            (
                "| `isFlaggedFraud` | "
                f"{profile['flagged_fraud_value_counts'].get('0', 0):,} | "
                f"{profile['flagged_fraud_value_counts'].get('1', 0):,} |"
            ),
            "",
            "## Cobertura temporal",
            "",
            "| Métrica | Valor |",
            "| --- | ---: |",
            f"| Step mínimo | {format_number(step_quality['min'], 0)} |",
            f"| Step máximo | {format_number(step_quality['max'], 0)} |",
            f"| Steps distintos | {step_quality['distinct_count']:,} |",
            f"| Steps ausentes | {len(step_quality['missing_steps']):,} |",
            (
                "| Inicio del tramo final compuesto solo por fraude | "
                f"{format_number(step_quality['final_fraud_only_start'], 0)} |"
            ),
            "",
            "### Últimos 10 steps",
            "",
            "| Step | Transacciones | Monto total | Fraudes | Tasa de fraude |",
            "| ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for values in per_step[-10:]:
        fraud_rate = values["fraud_rate"]
        lines.append(
            f"| {values['step']} | {values['transaction_count']:,} | "
            f"{format_number(values['total_amount'])} | {values['fraud_count']:,} | "
            f"{fraud_rate:.3%} |"
        )

    lines.extend(
        [
            "",
            "## Duplicados",
            "",
            (
                "Se detectaron "
                f"**{profile['duplicate_rows_by_hash']:,}** filas duplicadas mediante "
                "hash de las 11 columnas. El método permite comparar registros entre "
                "bloques sin cargar el CSV completo como texto en memoria."
            ),
            "",
            "## Puntos para revisión",
            "",
            "- Confirmar con los responsables de Silver cualquier regla de eliminación o corrección antes de modificar datos derivados.",
            "- Investigar el cambio de comportamiento del tramo final antes de definir entrenamiento y prueba.",
            "- Mantener los valores extremos de monto hasta determinar si son errores o resultados válidos de la simulación.",
            "",
            "El perfilado es de solo lectura y no modifica el archivo Bronze.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(
    profile: dict[str, Any], json_output: Path, markdown_output: Path
) -> None:
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    markdown_output.write_text(render_markdown(profile), encoding="utf-8")


def main() -> None:
    args = parse_args()
    profile = profile_csv(args.input.resolve(), args.chunksize)
    write_outputs(
        profile,
        args.json_output.resolve(),
        args.markdown_output.resolve(),
    )
    print(f"Filas perfiladas: {profile['row_count']:,}")
    print(f"Reporte JSON: {args.json_output.resolve()}")
    print(f"Resumen Markdown: {args.markdown_output.resolve()}")


if __name__ == "__main__":
    main()
