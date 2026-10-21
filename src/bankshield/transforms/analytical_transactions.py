"""Tabla analítica compartida D1 para asociaciones y regresión.

Construye un Parquet con **una fila por transacción** del Silver, más una
partición temporal, un identificador ordinal estable y dos variables
discretizadas por terciles. Los cortes de la discretización se ajustan
únicamente con ``train`` y se aplican sin cambios a ``validation``, ``test`` y
``stress``.

El archivo no reemplaza al mart de segmentos ni al Gold temporal: es una
entrega de datos para que otros módulos (asociaciones y regresión) trabajen
sobre el mismo universo y las mismas particiones. No modifica Bronze ni Silver
y no usa ``isFraud`` para nada distinto de conservarla como etiqueta.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from bankshield.ingestion.paysim_profile import TRANSACTION_TYPES
from bankshield.transforms.silver_transactions import SILVER_SCHEMA, file_sha256

ANALYTICS_COLUMNS = (
    "row_id",
    "step",
    "type",
    "amount",
    "oldbalanceOrg",
    "isFraud",
    "partition",
    "amount_bin",
    "origin_balance_bin",
)

ANALYTICS_SCHEMA = pa.schema(
    [
        ("row_id", pa.int64()),
        ("step", pa.int64()),
        ("type", pa.string()),
        ("amount", pa.float64()),
        ("oldbalanceOrg", pa.float64()),
        ("isFraud", pa.int8()),
        ("partition", pa.string()),
        ("amount_bin", pa.string()),
        ("origin_balance_bin", pa.string()),
    ]
)

REQUIRED_SILVER_COLUMNS = ("step", "type", "amount", "oldbalanceOrg", "isFraud")
BIN_COLUMNS = ("amount", "oldbalanceOrg")
BIN_OUTPUT_COLUMNS = {
    "amount": "amount_bin",
    "oldbalanceOrg": "origin_balance_bin",
}
PARTITION_NAMES = ("train", "validation", "test", "stress")

DEFAULT_QUANTILES = (1.0 / 3.0, 2.0 / 3.0)
DEFAULT_CUTS = {
    "train_end_step": 323,
    "validation_end_step": 378,
    "test_end_step": 718,
    "max_step": 743,
}

LIMITATIONS = [
    "Los datos provienen de la simulación PaySim; no representan operaciones reales.",
    "`step` es un paso de simulación, no una fecha calendario.",
    "`row_id` identifica filas del Silver y nunca debe usarse como predictor.",
    "`amount_bin` describe el monto y tiene prohibido usarse para predecir el monto.",
    "La partición `stress` (steps 719-743) se informa aparte y no selecciona modelos, bins, reglas ni umbrales.",
    "La discretización usa terciles exactos de `train`; con cortes repetidos puede quedar un solo intervalo.",
]


def default_config() -> dict:
    """Configuración por defecto, compartida por el CLI y las pruebas."""
    return {
        "input": "data/silver/transactions/transactions.parquet",
        "silver_quality": "artifacts/reports/transactions_silver.json",
        "output": "data/gold/analytics/transactions.parquet",
        "dataset_report": "artifacts/reports/analytics/dataset.json",
        "discretization_report": "artifacts/reports/analytics/discretization.json",
        "chunksize": 500_000,
        "require_silver_quality": True,
        "partitions": dict(DEFAULT_CUTS),
        "discretization": {
            "columns": list(BIN_COLUMNS),
            "quantiles": list(DEFAULT_QUANTILES),
        },
    }


def canonical_json(payload: object) -> str:
    """Serialización canónica para calcular huellas reproducibles."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest().upper()


def schema_sha256(schema: pa.Schema = ANALYTICS_SCHEMA) -> str:
    """Huella canónica de nombres y tipos del esquema de salida."""
    shape = [
        {"name": field.name, "type": str(field.type), "nullable": field.nullable}
        for field in schema
    ]
    return canonical_sha256({"schema_version": 1, "fields": shape})


def write_json_atomic(path: Path, payload: dict) -> None:
    """Escribe JSON estricto mediante archivo temporal y reemplazo final."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    tmp_path.replace(path)


def git_state(root: Path) -> dict:
    """Registra commit y si el árbol tenía cambios al construir el dataset."""

    def run(arguments: list[str]) -> str | None:
        try:
            result = subprocess.run(
                ["git", *arguments],
                cwd=str(root),
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return None
        return result.stdout.strip() if result.returncode == 0 else None

    commit = run(["rev-parse", "HEAD"])
    status = run(["status", "--porcelain"])
    return {
        "commit": commit,
        "tree_dirty": None if status is None else bool(status),
    }


def validate_cuts(
    train_end_step: int,
    validation_end_step: int,
    test_end_step: int,
    max_step: int,
) -> tuple[int, int, int, int]:
    """Comprueba que los cortes sean crecientes y cubran steps 1..max_step."""
    cuts = (train_end_step, validation_end_step, test_end_step, max_step)
    if not all(isinstance(value, int) for value in cuts):
        raise ValueError("Los cortes de partición deben ser enteros")
    if not (0 < train_end_step < validation_end_step < test_end_step < max_step):
        raise ValueError(
            "Los cortes deben cumplir 0 < train < validation < test < max_step"
        )
    return cuts


def validate_quantiles(quantiles) -> tuple[float, ...]:
    values = tuple(float(value) for value in quantiles)
    if not values:
        raise ValueError("Se requiere al menos un cuantil para discretizar")
    if any(not np.isfinite(value) or not (0 < value < 1) for value in values):
        raise ValueError("Los cuantiles deben ser números finitos entre 0 y 1")
    if list(values) != sorted(values) or len(set(values)) != len(values):
        raise ValueError("Los cuantiles deben ser estrictamente crecientes")
    return values


def assign_partitions(
    steps: np.ndarray,
    train_end_step: int,
    validation_end_step: int,
    test_end_step: int,
) -> np.ndarray:
    """Asigna una partición exclusiva por `step`, sin mirar la etiqueta."""
    steps = np.asarray(steps, dtype="int64")
    partitions = np.full(steps.shape, "stress", dtype=object)
    partitions[steps <= train_end_step] = "train"
    mask = (steps > train_end_step) & (steps <= validation_end_step)
    partitions[mask] = "validation"
    mask = (steps > validation_end_step) & (steps <= test_end_step)
    partitions[mask] = "test"
    return partitions


def fit_bins(values: np.ndarray, quantiles) -> dict:
    """Ajusta terciles exactos y conserva solo cortes interiores únicos."""
    values = np.asarray(values, dtype="float64")
    if values.size == 0:
        raise ValueError("No hay valores de train para ajustar la discretización")
    if not np.isfinite(values).all():
        raise ValueError("La discretización recibió valores no finitos")
    low = float(values.min())
    high = float(values.max())
    edges: list[float] = []
    for quantile in validate_quantiles(quantiles):
        edge = float(np.quantile(values, quantile))
        if not np.isfinite(edge):
            raise ValueError("Un cuantil produjo un valor no finito")
        if not (low < edge < high):
            continue
        if edges and edge <= edges[-1]:
            continue
        edges.append(edge)
    return {
        "interior_edges": edges,
        "labels": [f"b{index}" for index in range(len(edges) + 1)],
        "train_min": low,
        "train_max": high,
        "train_rows": int(values.size),
    }


def apply_bins(values: np.ndarray, interior_edges, labels) -> np.ndarray:
    """Aplica intervalos cerrados a la derecha ``(-inf, c1], (c1, c2], ...``."""
    values = np.asarray(values, dtype="float64")
    edges = np.asarray(list(interior_edges), dtype="float64")
    names = np.asarray(list(labels), dtype=object)
    index = np.searchsorted(edges, values, side="left")
    return names[index]


def validate_silver_quality(quality: dict, source_sha256: str) -> None:
    """Exige un reporte completo, sin rechazos y con huella coincidente."""
    if quality.get("scope") != "complete_file":
        raise ValueError("El reporte de calidad Silver no cubre el archivo completo")
    counts = quality.get("counts", {})
    if counts.get("rejected_rows") != 0:
        raise ValueError("El reporte de calidad Silver registra filas rechazadas")
    checks = quality.get("quality_checks", {})
    if not checks:
        raise ValueError("El reporte de calidad Silver no incluye controles")
    failed = sorted(name for name, value in checks.items() if value is not True)
    if failed:
        raise ValueError(
            "Controles de calidad Silver no aprobados: " + ", ".join(failed)
        )
    expected = str(quality.get("output", {}).get("sha256", ""))
    if expected.lower() != str(source_sha256).lower():
        raise ValueError(
            "El Parquet Silver no coincide con la huella registrada en su reporte"
        )


def validate_batch(frame: pd.DataFrame, max_step: int) -> None:
    """Valida tipos y rangos; detiene la construcción sin descartar filas."""
    values = frame.loc[:, list(REQUIRED_SILVER_COLUMNS)]
    if values.isna().any().any():
        columns = sorted(values.columns[values.isna().any()].tolist())
        raise ValueError(f"Silver contiene valores ausentes en: {columns}")

    steps = pd.to_numeric(values["step"], errors="coerce").to_numpy(dtype="float64")
    if not np.isfinite(steps).all():
        raise ValueError("step contiene valores no numéricos o no finitos")
    if (steps % 1 != 0).any() or (steps < 1).any() or (steps > max_step).any():
        raise ValueError(f"step debe ser un entero entre 1 y {max_step}")

    unknown = sorted(set(values["type"].astype(str)) - TRANSACTION_TYPES)
    if unknown:
        raise ValueError(f"type contiene valores desconocidos: {unknown}")

    for column in BIN_COLUMNS:
        numeric = pd.to_numeric(values[column], errors="coerce").to_numpy(
            dtype="float64"
        )
        if not np.isfinite(numeric).all():
            raise ValueError(f"{column} contiene valores no numéricos o no finitos")
        if (numeric < 0).any():
            raise ValueError(f"{column} contiene valores negativos")

    labels = pd.to_numeric(values["isFraud"], errors="coerce")
    if labels.isna().any() or not labels.isin([0, 1]).all():
        raise ValueError("isFraud debe contener únicamente 0 o 1")


def _new_totals() -> dict:
    return {"rows": 0, "amount": 0.0, "fraud": 0, "by_type": {}}


def _accumulate(totals: dict, frame: pd.DataFrame) -> None:
    totals["rows"] += int(len(frame))
    totals["amount"] += float(frame["amount"].sum())
    totals["fraud"] += int(frame["isFraud"].sum())
    counts = frame["type"].astype(str).value_counts().to_dict()
    for name, count in counts.items():
        totals["by_type"][name] = totals["by_type"].get(name, 0) + int(count)


def _prepare_batch(
    frame: pd.DataFrame,
    row_offset: int,
    cuts: tuple[int, int, int, int],
    discretization: dict,
) -> pd.DataFrame:
    train_end, validation_end, test_end, _ = cuts
    steps = pd.to_numeric(frame["step"], errors="raise").to_numpy(dtype="int64")
    amounts = pd.to_numeric(frame["amount"], errors="raise").to_numpy(dtype="float64")
    old_balances = pd.to_numeric(frame["oldbalanceOrg"], errors="raise").to_numpy(
        dtype="float64"
    )
    labels = pd.to_numeric(frame["isFraud"], errors="raise").to_numpy(dtype="int8")

    output = pd.DataFrame(index=frame.index)
    output["row_id"] = np.arange(
        row_offset + 1, row_offset + 1 + len(frame), dtype="int64"
    )
    output["step"] = steps
    output["type"] = frame["type"].astype(str).to_numpy()
    output["amount"] = amounts
    output["oldbalanceOrg"] = old_balances
    output["isFraud"] = labels
    output["partition"] = assign_partitions(
        steps, train_end, validation_end, test_end
    ).astype(str)
    for column in BIN_COLUMNS:
        spec = discretization[column]
        output[BIN_OUTPUT_COLUMNS[column]] = apply_bins(
            pd.to_numeric(frame[column], errors="raise").to_numpy(dtype="float64"),
            spec["interior_edges"],
            spec["labels"],
        ).astype(str)
    return output.loc[:, list(ANALYTICS_COLUMNS)]


def _quantile_pass(
    input_path: Path,
    chunksize: int,
    train_end_step: int,
    bin_columns: tuple[str, ...],
) -> dict[str, np.ndarray]:
    """Primera pasada: lee solo `step` y las columnas a discretizar."""
    collected: dict[str, list[np.ndarray]] = {column: [] for column in bin_columns}
    columns = ["step", *bin_columns]
    with pq.ParquetFile(input_path) as parquet:
        for batch in parquet.iter_batches(batch_size=chunksize, columns=columns):
            frame = batch.to_pandas()
            train_mask = pd.to_numeric(frame["step"], errors="raise").to_numpy(
                dtype="int64"
            ) <= train_end_step
            if not train_mask.any():
                continue
            for column in bin_columns:
                collected[column].append(
                    pd.to_numeric(
                        frame.loc[train_mask, column], errors="raise"
                    ).to_numpy(dtype="float64")
                )
    return {
        column: (np.concatenate(blocks) if blocks else np.empty(0, dtype="float64"))
        for column, blocks in collected.items()
    }


def build_analytics_transactions(
    input_path: Path,
    output_path: Path,
    dataset_report_path: Path | None = None,
    discretization_report_path: Path | None = None,
    silver_quality_path: Path | None = None,
    chunksize: int = 500_000,
    train_end_step: int = DEFAULT_CUTS["train_end_step"],
    validation_end_step: int = DEFAULT_CUTS["validation_end_step"],
    test_end_step: int = DEFAULT_CUTS["test_end_step"],
    max_step: int = DEFAULT_CUTS["max_step"],
    bin_columns: tuple[str, ...] = BIN_COLUMNS,
    quantiles: tuple[float, ...] = DEFAULT_QUANTILES,
    require_silver_quality: bool = True,
    base_dir: Path | None = None,
    git_commit: str | None = None,
    git_tree_dirty: bool | None = None,
) -> dict:
    """Construye D1 desde el Silver y devuelve el reporte del dataset."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    cuts = validate_cuts(train_end_step, validation_end_step, test_end_step, max_step)
    quantiles = validate_quantiles(quantiles)
    if chunksize < 1:
        raise ValueError("chunksize debe ser un entero positivo")
    bin_columns = tuple(bin_columns)
    if set(bin_columns) != set(BIN_COLUMNS):
        raise ValueError(
            "D1 exige discretizar exactamente: " + ", ".join(BIN_COLUMNS)
        )
    if not input_path.is_file():
        raise ValueError(f"No existe el Parquet Silver: {input_path}")

    parquet = pq.ParquetFile(input_path)
    try:
        missing = sorted(set(REQUIRED_SILVER_COLUMNS) - set(parquet.schema.names))
    finally:
        parquet.close()
    if missing:
        raise ValueError(f"El Parquet Silver no tiene las columnas requeridas: {missing}")

    source_sha = file_sha256(input_path)
    quality = None
    if silver_quality_path is not None:
        quality_path = Path(silver_quality_path)
        if not quality_path.is_file():
            raise ValueError(f"No existe el reporte de calidad Silver: {quality_path}")
        quality = json.loads(quality_path.read_text(encoding="utf-8"))
        validate_silver_quality(quality, source_sha)
    elif require_silver_quality:
        raise ValueError(
            "Se requiere el reporte de calidad Silver para declarar el dataset completo"
        )

    train_values = _quantile_pass(input_path, chunksize, train_end_step, bin_columns)
    discretization: dict[str, dict] = {}
    for column in bin_columns:
        spec = fit_bins(train_values[column], quantiles)
        counts = apply_bins(
            train_values[column], spec["interior_edges"], spec["labels"]
        )
        spec["train_counts"] = {
            label: int((counts == label).sum()) for label in spec["labels"]
        }
        spec["output_column"] = BIN_OUTPUT_COLUMNS[column]
        discretization[column] = spec

    canonical_discretization = {
        "schema_version": 1,
        "fit_partition": "train",
        "fit_step_range": {"min": 1, "max": train_end_step},
        "interval_closure": "right",
        "quantiles": list(quantiles),
        "columns": {
            column: {
                "interior_edges": spec["interior_edges"],
                "labels": spec["labels"],
                "output_column": spec["output_column"],
            }
            for column, spec in discretization.items()
        },
    }
    discretization_sha = canonical_sha256(canonical_discretization)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")

    input_totals = _new_totals()
    output_totals = _new_totals()
    partition_totals = {name: _new_totals() for name in PARTITION_NAMES}
    partition_steps = {name: [None, None] for name in PARTITION_NAMES}
    row_offset = 0
    row_ids_seen = 0
    row_id_bounds = [None, None]
    bin_null_counts = {column: 0 for column in bin_columns}

    writer = pq.ParquetWriter(tmp_path, ANALYTICS_SCHEMA, compression="snappy")
    parquet = pq.ParquetFile(input_path)
    try:
        for batch in parquet.iter_batches(batch_size=chunksize):
            frame = batch.to_pandas()
            validate_batch(frame, max_step)
            prepared = _prepare_batch(frame, row_offset, cuts, discretization)
            validate_batch(prepared, max_step)
            row_ids = prepared["row_id"].to_numpy(dtype="int64")
            if len(np.unique(row_ids)) != len(row_ids):
                raise ValueError("Se repitieron identificadores row_id")
            row_ids_seen += len(row_ids)
            row_id_bounds = [
                int(row_ids.min()) if row_id_bounds[0] is None else min(row_id_bounds[0], int(row_ids.min())),
                int(row_ids.max()) if row_id_bounds[1] is None else max(row_id_bounds[1], int(row_ids.max())),
            ]

            _accumulate(input_totals, frame)
            _accumulate(output_totals, prepared)
            for name in PARTITION_NAMES:
                mask = prepared["partition"] == name
                if not mask.any():
                    continue
                block = prepared.loc[mask]
                _accumulate(partition_totals[name], block)
                steps = block["step"].to_numpy(dtype="int64")
                current = partition_steps[name]
                partition_steps[name] = [
                    int(steps.min()) if current[0] is None else min(current[0], int(steps.min())),
                    int(steps.max()) if current[1] is None else max(current[1], int(steps.max())),
                ]
            for column in bin_columns:
                bin_null_counts[column] += int(
                    prepared[BIN_OUTPUT_COLUMNS[column]].isna().sum()
                )

            row_offset += len(prepared)
            writer.write_table(
                pa.Table.from_pandas(prepared, schema=ANALYTICS_SCHEMA, preserve_index=False)
            )
    except BaseException:
        writer.close()
        tmp_path.unlink(missing_ok=True)
        raise
    else:
        writer.close()
    finally:
        parquet.close()

    if row_offset == 0:
        tmp_path.unlink(missing_ok=True)
        raise ValueError("El dataset analítico quedaría sin registros")
    tmp_path.replace(output_path)

    partitions_report = {}
    for name in PARTITION_NAMES:
        totals = partition_totals[name]
        steps = partition_steps[name]
        partitions_report[name] = {
            "rows": totals["rows"],
            "min_step": steps[0],
            "max_step": steps[1],
            "fraud": totals["fraud"],
            "amount_sum": totals["amount"],
            "by_type": dict(sorted(totals["by_type"].items())),
        }

    checks = {
        "one_row_per_silver_row": input_totals["rows"] == output_totals["rows"],
        "row_ids_contiguous": (
            row_ids_seen == output_totals["rows"]
            and row_id_bounds == [1, output_totals["rows"]]
        ),
        "partitions_cover_all_rows": sum(
            value["rows"] for value in partitions_report.values()
        )
        == output_totals["rows"],
        "amount_total_preserved": bool(
            np.isclose(
                input_totals["amount"],
                output_totals["amount"],
                rtol=1e-12,
                atol=0.01,
            )
        ),
        "fraud_count_preserved": input_totals["fraud"] == output_totals["fraud"],
        "bins_without_nulls": all(count == 0 for count in bin_null_counts.values()),
        "bins_fitted_on_train_only": True,
    }
    if quality is not None:
        checks["silver_contract_approved"] = True
        checks["source_sha256_matches"] = True
    failed = sorted(name for name, passed in checks.items() if passed is not True)
    if failed:
        output_path.unlink(missing_ok=True)
        raise ValueError("Fallaron controles del dataset analítico: " + ", ".join(failed))

    def display(path: Path | None) -> str | None:
        if path is None:
            return None
        path = Path(path)
        if base_dir is None:
            return str(path)
        try:
            return str(path.resolve().relative_to(Path(base_dir).resolve()))
        except ValueError:
            return str(path)

    output_report = {
        "path": display(output_path),
        "format": "parquet",
        "compression": "snappy",
        "rows": row_offset,
        "columns": list(ANALYTICS_COLUMNS),
        "schema_sha256": schema_sha256(),
        "size_bytes": output_path.stat().st_size,
        "sha256": file_sha256(output_path),
    }

    report = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git": {"commit": git_commit, "tree_dirty": git_tree_dirty},
        "source": {
            "path": display(input_path),
            "format": "parquet",
            "sha256": source_sha,
            "rows": input_totals["rows"],
            "columns_used": list(REQUIRED_SILVER_COLUMNS),
        },
        "silver_quality": None
        if quality is None
        else {
            "path": display(silver_quality_path),
            "sha256": file_sha256(Path(silver_quality_path)),
            "quality_checks": quality.get("quality_checks"),
            "duplicates": quality.get("duplicates"),
            "counts": quality.get("counts"),
        },
        "config": {
            "chunksize": chunksize,
            "partitions": {
                "train": [1, train_end_step],
                "validation": [train_end_step + 1, validation_end_step],
                "test": [validation_end_step + 1, test_end_step],
                "stress": [test_end_step + 1, max_step],
            },
            "bin_columns": list(bin_columns),
            "quantiles": list(quantiles),
            "fit_partition": "train",
        },
        "output": output_report,
        "discretization": {
            "path": display(discretization_report_path),
            "sha256": discretization_sha,
            "interval_closure": "right",
            "columns": discretization,
        },
        "counts": {
            "rows_in": input_totals["rows"],
            "rows_out": output_totals["rows"],
            "rows_excluded": input_totals["rows"] - output_totals["rows"],
        },
        "totals": {
            "amount_in": input_totals["amount"],
            "amount_out": output_totals["amount"],
            "fraud_in": input_totals["fraud"],
            "fraud_out": output_totals["fraud"],
            "by_type_in": dict(sorted(input_totals["by_type"].items())),
            "by_type_out": dict(sorted(output_totals["by_type"].items())),
        },
        "partitions": partitions_report,
        "quality_checks": checks,
        "limitations": list(LIMITATIONS),
    }

    if discretization_report_path is not None:
        write_json_atomic(
            Path(discretization_report_path),
            {
                "schema_version": 1,
                "generated_at_utc": report["generated_at_utc"],
                "source_sha256": source_sha,
                "dataset_sha256": output_report["sha256"],
                "discretization_sha256": discretization_sha,
                **canonical_discretization,
                "columns": {
                    column: {
                        **{
                            key: value
                            for key, value in spec.items()
                            if key != "output_column"
                        },
                        "output_column": spec["output_column"],
                    }
                    for column, spec in discretization.items()
                },
                "edges_as_json_null": {
                    "lower": None,
                    "upper": None,
                    "note": "Los extremos abiertos se representan como null, nunca Infinity.",
                },
                "limitations": list(LIMITATIONS),
            },
        )
    if dataset_report_path is not None:
        write_json_atomic(Path(dataset_report_path), report)
    return report


def write_fixture_silver(path: Path) -> pd.DataFrame:
    """Escribe un Silver mínimo válido que cubre las cuatro particiones."""
    steps = (1, 160, 323, 324, 378, 379, 500, 718, 719, 743)
    types = sorted(TRANSACTION_TYPES)
    rows = []
    for index, step in enumerate(steps):
        for offset in range(6):
            amount = float(1000 * (index + 1) + 250 * offset)
            old_balance = amount + 5000.0
            rows.append(
                {
                    "step": step,
                    "type": types[(index + offset) % len(types)],
                    "amount": amount,
                    "nameOrig": f"C{index:02d}{offset}",
                    "oldbalanceOrg": old_balance,
                    "newbalanceOrig": old_balance - amount,
                    "nameDest": f"M{index:02d}{offset}",
                    "oldbalanceDest": 0.0,
                    "newbalanceDest": amount,
                    "isFraud": 1 if (index * 6 + offset) % 23 == 0 else 0,
                    "isFlaggedFraud": 0,
                }
            )
    frame = pd.DataFrame(rows)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(frame, schema=SILVER_SCHEMA, preserve_index=False)
    pq.write_table(table, path, compression="snappy")
    return frame


def build_fixture(
    directory: Path,
    quantiles: tuple[float, ...] = DEFAULT_QUANTILES,
    cuts: tuple[int, int, int, int] = (
        DEFAULT_CUTS["train_end_step"],
        DEFAULT_CUTS["validation_end_step"],
        DEFAULT_CUTS["test_end_step"],
        DEFAULT_CUTS["max_step"],
    ),
) -> dict:
    """Genera Silver, D1 y los dos JSON de un fixture pequeño y determinista."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    silver_path = directory / "silver_transactions.parquet"
    write_fixture_silver(silver_path)
    train_end, validation_end, test_end, max_step = cuts
    return build_analytics_transactions(
        silver_path,
        directory / "analytics_transactions.parquet",
        dataset_report_path=directory / "dataset.json",
        discretization_report_path=directory / "discretization.json",
        chunksize=7,
        train_end_step=train_end,
        validation_end_step=validation_end,
        test_end_step=test_end,
        max_step=max_step,
        quantiles=quantiles,
        require_silver_quality=False,
        base_dir=directory,
    )
