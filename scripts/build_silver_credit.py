"""Construye Silver de crédito desde Bronze con controles de calidad."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankshield.transforms.silver_credit import build_silver_credit


def main():
    parser = argparse.ArgumentParser(description="Bronze -> Silver de crédito")
    parser.add_argument("--input", type=Path, default=ROOT / "data/bronze/credit/credit_risk_dataset.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data/silver/credit/credit.parquet")
    parser.add_argument("--quality", type=Path, default=ROOT / "artifacts/reports/credit/silver_quality.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "docs/credito/calidad-silver.md")
    args = parser.parse_args()
    try:
        report = build_silver_credit(args.input, args.output, args.quality, args.markdown)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    c = report["counts"]
    print(f"Bronze {c['bronze_rows']:,} -> Silver {c['silver_rows']:,} "
          f"(rechazadas {c['rejected_rows']}, duplicados {c['exact_duplicates_removed']})")


if __name__ == "__main__":
    main()
