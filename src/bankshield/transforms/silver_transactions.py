"""Transformación Silver del CSV transaccional PaySim.

Lee Bronze en bloques, aplica controles de calidad, tipa las columnas y
escribe un Parquet en Silver sin modificar el original. El reporte de
calidad registra recuentos antes y después, rechazos por causa, duplicados
exactos, cuentas únicas y cuantiles de monto.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from bankshield.ingestion.paysim_profile import FIELDS, TRANSACTION_TYPES

FLOAT_FIELDS = (
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
)
BINARY_FIELDS = ("isFraud", "isFlaggedFraud")
QUANTILES = (0.25, 0.50, 0.75, 0.95, 0.99, 0.999)

SILVER_SCHEMA = pa.schema(
    [
        ("step", pa.int64()),
        ("type", pa.string()),
        ("amount", pa.float64()),
        ("nameOrig", pa.string()),
        ("oldbalanceOrg", pa.float64()),
        ("newbalanceOrig", pa.float64()),
        ("nameDest", pa.string()),
        ("oldbalanceDest", pa.float64()),
        ("newbalanceDest", pa.float64()),
        ("isFraud", pa.int8()),
        ("isFlaggedFraud", pa.int8()),
    ]
)


def file_sha256(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def read_header(path: Path) -> list[str]:
    """Valida la cabecera; rechaza referencias Git LFS y esquemas inesperados."""
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        header = next(csv.reader(handle), [])
    if header and header[0].startswith("version https://git-lfs.github.com"):
        raise ValueError("Se requiere el CSV completo, no una referencia Git LFS")
    if len(header) != len(FIELDS) or set(header) != set(FIELDS):
        raise ValueError(f"Cabecera PaySim inesperada: {header}")
    return header


def clean_chunk(chunk: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Devuelve las filas válidas tipadas y las incidencias del bloque."""
    issues: Counter[str] = Counter()
    source = chunk.loc[:, list(FIELDS)]
    rejected = pd.Series(False, index=source.index)

    blank: dict[str, pd.Series] = {}
    for field in FIELDS:
        mask = source[field].isna() | source[field].fillna("").str.strip().eq("")
        blank[field] = mask
        if mask.any():
            issues[f"missing:{field}"] = int(mask.sum())
        rejected |= mask

    typed = pd.DataFrame(index=source.index)

    step = pd.to_numeric(source["step"], errors="coerce")
    bad_step = ~blank["step"] & (step.isna() | (step % 1 != 0) | (step < 0))
    if bad_step.any():
        issues["invalid:step"] = int(bad_step.sum())
        rejected |= bad_step
    typed["step"] = step

    for field in FLOAT_FIELDS:
        values = pd.to_numeric(source[field], errors="coerce")
        bad = ~blank[field] & ~np.isfinite(values)
        negative = ~blank[field] & np.isfinite(values) & (values < 0)
        if bad.any():
            issues[f"invalid:{field}"] = int(bad.sum())
            rejected |= bad
        if negative.any():
            issues[f"negative:{field}"] = int(negative.sum())
            rejected |= negative
        typed[field] = values

    for field in BINARY_FIELDS:
        values = pd.to_numeric(source[field], errors="coerce")
        bad = ~blank[field] & ~values.isin([0, 1])
        if bad.any():
            issues[f"invalid:{field}"] = int(bad.sum())
            rejected |= bad
        typed[field] = values

    bad_type = ~blank["type"] & ~source["type"].isin(TRANSACTION_TYPES)
    if bad_type.any():
        issues["invalid:type"] = int(bad_type.sum())
        rejected |= bad_type
    typed["type"] = source["type"]

    for field in ("nameOrig", "nameDest"):
        typed[field] = source[field]

    clean = typed.loc[~rejected, list(FIELDS)].copy()
    if not clean.empty:
        clean["step"] = clean["step"].astype("int64")
        for field in BINARY_FIELDS:
            clean[field] = clean[field].astype("int8")
    return clean, dict(issues)


def build_silver(
    input_path: Path,
    output_path: Path,
    quality_json: Path | None = None,
    quality_markdown: Path | None = None,
    chunksize: int = 500_000,
    limit: int | None = None,
    expected_sha256: str | None = None,
    base_dir: Path | None = None,
) -> dict:
    """Construye Silver a partir de Bronze y devuelve el reporte de calidad.

    ``base_dir`` permite registrar rutas relativas al repositorio en el
    reporte, para que el documento sea reproducible en otras máquinas.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    def display(path: Path) -> str:
        if base_dir is None:
            return str(path)
        try:
            return str(Path(path).resolve().relative_to(Path(base_dir).resolve()))
        except ValueError:
            return str(path)

    if chunksize < 1:
        raise ValueError("chunksize debe ser un entero positivo")
    if limit is not None and limit < 1:
        raise ValueError("limit debe ser un entero positivo")

    read_header(input_path)
    source_sha = file_sha256(input_path)
    if expected_sha256 and source_sha != str(expected_sha256).strip().upper():
        raise ValueError(
            f"La huella SHA-256 del CSV no coincide con la esperada: {source_sha}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")

    rejected_by_issue: Counter[str] = Counter()
    by_type: dict[str, dict[str, float]] = {}
    by_step: dict[int, dict[str, int]] = {}
    amount_blocks: list[np.ndarray] = []
    hash_blocks: list[np.ndarray] = []
    origin_blocks: list[np.ndarray] = []
    destination_blocks: list[np.ndarray] = []
    bronze_rows = 0
    silver_rows = 0
    truncated = False

    reader = pd.read_csv(
        input_path, dtype="string", chunksize=chunksize, encoding="utf-8-sig"
    )
    writer = pq.ParquetWriter(tmp_path, SILVER_SCHEMA, compression="snappy")
    try:
        for chunk in reader:
            if limit is not None and bronze_rows >= limit:
                truncated = True
                break
            if limit is not None and bronze_rows + len(chunk) > limit:
                chunk = chunk.iloc[: limit - bronze_rows]
                truncated = True
            bronze_rows += len(chunk)

            clean, issues = clean_chunk(chunk)
            rejected_by_issue.update(issues)
            if clean.empty:
                continue
            silver_rows += len(clean)

            grouped = clean.groupby("type").agg(
                rows=("step", "size"), amount=("amount", "sum"), fraud=("isFraud", "sum")
            )
            for name, row in grouped.iterrows():
                bucket = by_type.setdefault(
                    str(name), {"rows": 0, "amount": 0.0, "fraud": 0}
                )
                bucket["rows"] += int(row["rows"])
                bucket["amount"] += float(row["amount"])
                bucket["fraud"] += int(row["fraud"])

            steps = clean.groupby("step").agg(
                rows=("step", "size"), fraud=("isFraud", "sum")
            )
            for step_value, row in steps.iterrows():
                bucket = by_step.setdefault(int(step_value), {"rows": 0, "fraud": 0})
                bucket["rows"] += int(row["rows"])
                bucket["fraud"] += int(row["fraud"])

            amount_blocks.append(clean["amount"].to_numpy(dtype="float64"))
            hash_blocks.append(
                pd.util.hash_pandas_object(clean[list(FIELDS)], index=False).to_numpy(
                    dtype=np.uint64
                )
            )
            origin_blocks.append(
                pd.util.hash_pandas_object(clean["nameOrig"], index=False).to_numpy(
                    dtype=np.uint64
                )
            )
            destination_blocks.append(
                pd.util.hash_pandas_object(clean["nameDest"], index=False).to_numpy(
                    dtype=np.uint64
                )
            )

            writer.write_table(
                pa.Table.from_pandas(clean, schema=SILVER_SCHEMA, preserve_index=False)
            )
            print(f"Silver: {bronze_rows:,} filas de Bronze", flush=True)
    except BaseException:
        writer.close()
        tmp_path.unlink(missing_ok=True)
        raise
    else:
        writer.close()

    if silver_rows == 0:
        tmp_path.unlink(missing_ok=True)
        raise ValueError("Silver quedaría sin registros válidos; revisar la calidad")
    tmp_path.replace(output_path)

    amounts = np.concatenate(amount_blocks)
    row_hashes = np.concatenate(hash_blocks)
    origin_hashes = np.concatenate(origin_blocks)
    destination_hashes = np.concatenate(destination_blocks)
    _, frequencies = np.unique(row_hashes, return_counts=True)
    duplicate_rows = int(np.maximum(frequencies - 1, 0).sum())
    all_account_hashes = np.concatenate([origin_hashes, destination_hashes])

    sorted_steps = sorted(by_step)
    missing_steps = sorted(
        set(range(sorted_steps[0], sorted_steps[-1] + 1)) - set(sorted_steps)
    )
    rejected_rows = bronze_rows - silver_rows

    quality_checks = {
        "expected_header": True,
        "source_sha256_matches": (
            source_sha == str(expected_sha256).strip().upper()
            if expected_sha256
            else None
        ),
        "no_rejected_rows": rejected_rows == 0,
        "no_exact_duplicate_rows": duplicate_rows == 0,
        "steps_are_contiguous": not missing_steps,
    }

    report = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "path": display(input_path),
            "size_bytes": input_path.stat().st_size,
            "sha256": source_sha,
            "expected_sha256": str(expected_sha256).strip().upper()
            if expected_sha256
            else None,
        },
        "output": {
            "path": display(output_path),
            "sha256": file_sha256(output_path),
            "format": "parquet",
            "compression": "snappy",
            "rows": silver_rows,
            "columns": list(FIELDS),
        },
        "scope": "first_rows_sample" if truncated else "complete_file",
        "row_limit": limit,
        "counts": {
            "bronze_rows": bronze_rows,
            "silver_rows": silver_rows,
            "rejected_rows": rejected_rows,
            "rejected_by_issue": dict(sorted(rejected_by_issue.items())),
        },
        "duplicates": {
            "exact_duplicate_rows": duplicate_rows,
            "policy": "kept",
            "method": "Hash pandas de 64 bits sobre las 11 columnas de Silver.",
        },
        "accounts": {
            "unique_origins": int(np.unique(origin_hashes).size),
            "unique_destinations": int(np.unique(destination_hashes).size),
            "unique_accounts": int(np.unique(all_account_hashes).size),
        },
        "amount_summary": {
            "min": float(amounts.min()),
            "max": float(amounts.max()),
            "mean": float(amounts.mean()),
            "quantiles": {
                f"p{quantile * 100:g}": float(value)
                for quantile, value in zip(QUANTILES, np.quantile(amounts, QUANTILES))
            },
        },
        "by_type": {
            name: {
                "rows": values["rows"],
                "amount": values["amount"],
                "fraud": values["fraud"],
            }
            for name, values in sorted(by_type.items())
        },
        "step_coverage": {
            "min": sorted_steps[0],
            "max": sorted_steps[-1],
            "distinct": len(sorted_steps),
            "missing_steps": missing_steps,
        },
        "quality_checks": quality_checks,
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
        quality_markdown.write_text(render_markdown(report), encoding="utf-8")
    return report


def format_number(value: float | int | None, decimals: int = 2) -> str:
    if value is None:
        return "n.a."
    if isinstance(value, int):
        return f"{value:,}"
    return f"{value:,.{decimals}f}"


def render_markdown(report: dict) -> str:
    counts = report["counts"]
    duplicate = report["duplicates"]
    accounts = report["accounts"]
    amount = report["amount_summary"]
    coverage = report["step_coverage"]
    lines = [
        "# Reporte de calidad — Silver transaccional",
        "",
        "Archivo generado por `scripts/build_silver.py`; se regenera con cada",
        "construcción de Silver. Los originales de Bronze no se modifican.",
        "",
        "## Fuente y salida",
        "",
        f"- Entrada: `{Path(report['source']['path']).name}`",
        f"- Tamaño: {report['source']['size_bytes']:,} bytes",
        f"- SHA-256: `{report['source']['sha256']}`",
        f"- Huella esperada coincide: {report['quality_checks']['source_sha256_matches']}",
        f"- Salida: `{report['output']['path']}` (Parquet, compresión snappy)",
        f"- Alcance: `{report['scope']}`",
        "",
        "## Recuentos",
        "",
        "| Métrica | Valor |",
        "| --- | ---: |",
        f"| Filas de Bronze | {counts['bronze_rows']:,} |",
        f"| Filas en Silver | {counts['silver_rows']:,} |",
        f"| Filas rechazadas | {counts['rejected_rows']:,} |",
        "",
        "### Rechazos por causa",
        "",
        "| Causa | Filas |",
        "| --- | ---: |",
    ]
    if counts["rejected_by_issue"]:
        lines += [
            f"| `{cause}` | {rows:,} |"
            for cause, rows in counts["rejected_by_issue"].items()
        ]
    else:
        lines.append("| _(sin rechazos)_ | 0 |")

    lines += [
        "",
        "## Controles",
        "",
        "| Control | Resultado |",
        "| --- | --- |",
    ]
    for name, passed in report["quality_checks"].items():
        if passed is None:
            result = "no aplica"
        else:
            result = "OK" if passed else "REVISAR"
        lines.append(f"| `{name}` | {result} |")

    lines += [
        "",
        "## Duplicados y cuentas",
        "",
        f"- Filas exactas duplicadas en Silver: **{duplicate['exact_duplicate_rows']:,}** "
        f"(política: {duplicate['policy']}; {duplicate['method']})",
        f"- Cuentas origen únicas: {accounts['unique_origins']:,}",
        f"- Cuentas destino únicas: {accounts['unique_destinations']:,}",
        f"- Cuentas únicas (unión): {accounts['unique_accounts']:,}",
        "",
        "## Distribución de `amount` en Silver",
        "",
        "| Métrica | Valor |",
        "| --- | ---: |",
        f"| Mínimo | {format_number(amount['min'])} |",
        f"| Promedio | {format_number(amount['mean'])} |",
        f"| Máximo | {format_number(amount['max'])} |",
    ]
    lines += [
        f"| Percentil {key[1:]} | {format_number(value)} |"
        for key, value in amount["quantiles"].items()
    ]

    lines += [
        "",
        "## Cobertura por `step`",
        "",
        "| Métrica | Valor |",
        "| --- | ---: |",
        f"| Step mínimo | {coverage['min']:,} |",
        f"| Step máximo | {coverage['max']:,} |",
        f"| Steps distintos | {coverage['distinct']:,} |",
        f"| Steps ausentes | {len(coverage['missing_steps']):,} |",
        "",
        "## Fraude por tipo de transacción",
        "",
        "| Tipo | Filas | Fraudes | Monto total |",
        "| --- | ---: | ---: | ---: |",
    ]
    lines += [
        f"| `{name}` | {values['rows']:,} | {values['fraud']:,} | "
        f"{format_number(values['amount'])} |"
        for name, values in report["by_type"].items()
    ]

    lines += [
        "",
        "## Límites",
        "",
        "- `step` es un paso de simulación de PaySim, no una fecha calendario.",
        "- Los datos provienen de una simulación; los resultados no representan",
        "  operaciones bancarias reales.",
        "- Las filas rechazadas se excluyen de Silver y quedan registradas por causa",
        "  en este reporte; Bronze permanece intacto.",
        "- Los duplicados exactos se conservan por política mientras el equipo no",
        "  defina una regla de eliminación: no existe identificador de transacción",
        "  en la fuente.",
        "",
    ]
    return "\n".join(lines)
