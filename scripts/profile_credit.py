"""CLI del perfil del dataset crediticio; no modifica Bronze."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankshield.ingestion.credit_profile import profile_credit, write_reports


def main():
    parser = argparse.ArgumentParser(description="Perfilar credit_risk_dataset.csv")
    parser.add_argument("--input", type=Path, default=ROOT / "data/bronze/credit/credit_risk_dataset.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/reports/credit/credit_profile.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "docs/credito/perfil-credito.md")
    args = parser.parse_args()
    try:
        profile = profile_credit(args.input)
        write_reports(profile, args.output, args.markdown)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(f"Filas: {profile['rows']:,}; duplicados: {profile['exact_duplicate_rows']:,}; "
          f"clase positiva: {profile['label']['positive_rate']:.2%}")
    print(f"JSON: {args.output}\nMarkdown: {args.markdown}")


if __name__ == "__main__":
    main()
