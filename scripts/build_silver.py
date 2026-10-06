"""Construye la capa Silver del CSV transaccional PaySim.

Lee Bronze en bloques, aplica controles de calidad y escribe un Parquet
tipado en Silver junto con su reporte de calidad. Nunca modifica Bronze.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankshield.transforms.silver_transactions import build_silver


def resolve(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Construye Silver desde Bronze con controles de calidad."
    )
    parser.add_argument(
        "--config", type=Path, default=ROOT / "configs" / "transactions.json",
        help="Archivo de configuración. Valor predeterminado: configs/transactions.json",
    )
    parser.add_argument("--input", type=Path, help="CSV de entrada en Bronze")
    parser.add_argument("--output", type=Path, help="Parquet de salida en Silver")
    parser.add_argument("--quality-json", type=Path, help="Reporte de calidad JSON")
    parser.add_argument("--quality-markdown", type=Path, help="Resumen Markdown de calidad")
    parser.add_argument("--chunksize", type=int, help="Filas leídas en cada bloque")
    parser.add_argument(
        "--limit", type=int,
        help="Filas de Bronze a leer; el informe se marca como muestra",
    )
    args = parser.parse_args()

    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Error al leer la configuración: {exc}\n")

    input_path = resolve(ROOT, args.input or config["input"])
    output_path = resolve(ROOT, args.output or config["output"])
    quality_json = resolve(ROOT, args.quality_json or config["quality_json"])
    quality_markdown = resolve(ROOT, args.quality_markdown or config["quality_markdown"])
    chunksize = args.chunksize if args.chunksize is not None else config.get("chunksize", 500_000)

    try:
        report = build_silver(
            input_path,
            output_path,
            quality_json=quality_json,
            quality_markdown=quality_markdown,
            chunksize=chunksize,
            limit=args.limit,
            expected_sha256=config.get("expected_sha256"),
            base_dir=ROOT,
        )
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")

    counts = report["counts"]
    print(f"Entrada: {report['source']['path']}")
    print(f"Salida: {report['output']['path']}")
    print(
        f"Bronze: {counts['bronze_rows']:,} filas | "
        f"Silver: {counts['silver_rows']:,} | "
        f"Rechazadas: {counts['rejected_rows']:,}"
    )
    print(f"Alcance: {report['scope']}")
    print(f"Reporte JSON: {quality_json}")
    print(f"Resumen Markdown: {quality_markdown}")
    pending = [name for name, passed in report["quality_checks"].items() if passed is False]
    if pending:
        print("Controles a revisar: " + ", ".join(pending))


if __name__ == "__main__":
    main()
