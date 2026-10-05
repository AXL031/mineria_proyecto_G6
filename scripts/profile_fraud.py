"""CLI del perfilado inicial de fraude; solo usa la biblioteca estándar."""

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankshield.ingestion.paysim_profile import profile_paysim, write_reports


def main() -> None:
    parser = argparse.ArgumentParser(description="Perfilar PaySim sin modificar Bronze")
    parser.add_argument("--input", type=Path, default=ROOT / "data/bronze/transactions/PS_20174392719_1491204439457_log.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/reports/fraud/paysim_profile.json")
    parser.add_argument("--markdown", type=Path, help="Ruta opcional para el informe Markdown")
    parser.add_argument("--limit", type=int, help="Máximo de filas; sin este argumento se lee todo el CSV")
    args = parser.parse_args()
    try:
        profile = profile_paysim(args.input, args.limit)
        write_reports(profile, args.output, args.markdown)
    except (OSError, ValueError, csv.Error) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(f"Filas: {profile['rows']:,}; inválidas: {profile['invalid_rows']:,}; "
          f"fraudes: {profile['label_counts']['1']:,}; alcance: {profile['scope']}")
    print(f"JSON: {args.output}")
    if args.markdown:
        print(f"Markdown: {args.markdown}")


if __name__ == "__main__":
    main()
