"""Construye la tabla analítica compartida D1 desde el Silver transaccional."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankshield.transforms.analytical_transactions import (
    BIN_COLUMNS,
    build_analytics_transactions,
    build_fixture,
    default_config,
    git_state,
)


def resolve(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Construye D1 (row_id, particiones y bins) desde el Silver "
            "transaccional, sin modificar Silver, segmentos ni fraude."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "analytics.json",
        help="Configuración. Valor predeterminado: configs/analytics.json",
    )
    parser.add_argument("--input", type=Path, help="Parquet de entrada en Silver")
    parser.add_argument(
        "--silver-quality", type=Path, help="Reporte JSON de calidad del Silver"
    )
    parser.add_argument("--output", type=Path, help="Parquet de salida D1")
    parser.add_argument(
        "--dataset-report", type=Path, help="Reporte JSON del dataset (metadatos)"
    )
    parser.add_argument(
        "--discretization-report",
        type=Path,
        help="Reporte JSON del esquema de discretización",
    )
    parser.add_argument("--chunksize", type=int, help="Filas procesadas por bloque")
    parser.add_argument(
        "--allow-partial-silver",
        action="store_true",
        help="No exigir el reporte de calidad Silver (solo para fixtures)",
    )
    parser.add_argument(
        "--write-fixture",
        type=Path,
        help="Genera un fixture D1 pequeño y determinista en la carpeta indicada",
    )
    args = parser.parse_args()

    if args.write_fixture is not None:
        report = build_fixture(args.write_fixture)
        print(f"Fixture D1: {args.write_fixture}")
        print(
            f"Filas: {report['counts']['rows_out']:,} | "
            f"Dataset SHA-256: {report['output']['sha256']}"
        )
        return

    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Error al leer la configuración: {exc}\n")

    merged = default_config()
    merged.update(config)

    input_path = resolve(ROOT, args.input or merged["input"])
    quality_value = args.silver_quality or merged.get("silver_quality")
    silver_quality = resolve(ROOT, quality_value) if quality_value else None
    output_path = resolve(ROOT, args.output or merged["output"])
    dataset_report = resolve(ROOT, args.dataset_report or merged["dataset_report"])
    discretization_report = resolve(
        ROOT, args.discretization_report or merged["discretization_report"]
    )
    chunksize = (
        args.chunksize if args.chunksize is not None else merged.get("chunksize", 500_000)
    )
    cuts = merged["partitions"]
    discretization = merged["discretization"]
    require_quality = bool(merged.get("require_silver_quality", True)) and not (
        args.allow_partial_silver
    )
    state = git_state(ROOT)

    try:
        report = build_analytics_transactions(
            input_path,
            output_path,
            dataset_report_path=dataset_report,
            discretization_report_path=discretization_report,
            silver_quality_path=silver_quality if silver_quality and silver_quality.is_file() else None,
            chunksize=chunksize,
            train_end_step=cuts["train_end_step"],
            validation_end_step=cuts["validation_end_step"],
            test_end_step=cuts["test_end_step"],
            max_step=cuts["max_step"],
            bin_columns=tuple(discretization.get("columns", BIN_COLUMNS)),
            quantiles=tuple(discretization["quantiles"]),
            require_silver_quality=require_quality,
            base_dir=ROOT,
            git_commit=state["commit"],
            git_tree_dirty=state["tree_dirty"],
        )
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")

    print(f"Entrada Silver: {report['source']['path']}")
    print(f"Salida D1: {report['output']['path']}")
    print(
        f"Filas: {report['counts']['rows_out']:,} | "
        f"Excluidas: {report['counts']['rows_excluded']:,}"
    )
    for name, values in report["partitions"].items():
        print(
            f"  {name}: {values['rows']:,} filas "
            f"(steps {values['min_step']}-{values['max_step']})"
        )
    for column, spec in report["discretization"]["columns"].items():
        edges = ", ".join(f"{value:,.2f}" for value in spec["interior_edges"]) or "(sin cortes)"
        print(f"Bins {column} -> {spec['output_column']}: {spec['labels']} | {edges}")
    print(f"Dataset SHA-256: {report['output']['sha256']}")
    print(f"Discretización SHA-256: {report['discretization']['sha256']}")
    print(f"Reporte del dataset: {dataset_report}")
    print(f"Reporte de discretización: {discretization_report}")


if __name__ == "__main__":
    main()
