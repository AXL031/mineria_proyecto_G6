"""Construye la tabla Gold temporal utilizada por el módulo de pronósticos."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankshield.transforms.temporal_transactions import build_temporal_gold


def resolve(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Construye Gold temporal desde el Parquet Silver."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "forecast.json",
        help="Configuración. Valor predeterminado: configs/forecast.json",
    )
    parser.add_argument("--input", type=Path, help="Parquet de entrada en Silver")
    parser.add_argument("--output", type=Path, help="Parquet temporal de salida en Gold")
    parser.add_argument("--quality-json", type=Path, help="Reporte de calidad JSON")
    parser.add_argument(
        "--quality-markdown", type=Path, help="Resumen de calidad Markdown"
    )
    args = parser.parse_args()

    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Error al leer la configuración: {exc}\n")

    input_path = resolve(ROOT, args.input or config["input"])
    output_path = resolve(ROOT, args.output or config["output"])
    quality_json = resolve(ROOT, args.quality_json or config["quality_json"])
    quality_markdown = resolve(
        ROOT, args.quality_markdown or config["quality_markdown"]
    )

    try:
        report = build_temporal_gold(
            input_path,
            output_path,
            quality_json=quality_json,
            quality_markdown=quality_markdown,
            base_dir=ROOT,
        )
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")

    counts = report["counts"]
    steps = report["step_coverage"]
    print(f"Entrada Silver: {report['source']['path']}")
    print(f"Salida Gold: {report['output']['path']}")
    print(
        f"Transacciones: {counts['input_transactions']:,} | "
        f"Filas temporales: {counts['gold_rows']:,}"
    )
    print(f"Cobertura: step {steps['min']} a {steps['max']}")
    print(f"Reporte JSON: {quality_json}")
    print(f"Resumen Markdown: {quality_markdown}")


if __name__ == "__main__":
    main()
