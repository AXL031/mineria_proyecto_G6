"""CLI del perfilado inicial de reclamos y NLP (CFPB); solo usa la biblioteca estándar."""

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankshield.ingestion.complaints_profile import profile_complaints, write_reports


def main() -> None:
    parser = argparse.ArgumentParser(description="Perfilar consumer_complaints.csv sin modificar Bronze")
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "data/bronze/complaints/consumer_complaints.csv",
        help="Ruta al archivo CSV de reclamos",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/reports/complaints/complaints_profile.json",
        help="Ruta de salida del JSON de perfilado",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=ROOT / "docs/reclamos/perfil-complaints.md",
        help="Ruta opcional para el informe Markdown",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Máximo de filas a procesar (para pruebas rápidas)",
    )
    args = parser.parse_args()

    print(f"Iniciando perfilado de reclamos desde: {args.input}")
    try:
        profile = profile_complaints(args.input, args.limit)
        write_reports(profile, args.output, args.markdown)
    except (OSError, ValueError, csv.Error) as exc:
        parser.exit(1, f"Error durante el perfilado: {exc}\n")

    nm = profile["narrative_metrics"]
    print(
        f"Completado exitosamente.\n"
        f"Filas procesadas: {profile['rows']:,} (Válidas: {profile['valid_rows']:,}, Inválidas: {profile['invalid_rows']:,})\n"
        f"Reclamos con narrativa: {nm['count']:,} ({nm['coverage_rate']:.2%})\n"
        f"Alcance: {profile['scope']}\n"
        f"JSON guardado en: {args.output}"
    )
    if args.markdown:
        print(f"Markdown guardado en: {args.markdown}")


if __name__ == "__main__":
    main()
