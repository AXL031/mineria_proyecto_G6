"""Construye Silver de reclamos desde Bronze con controles de calidad."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankshield.transforms.silver_complaints import build_silver_complaints


def main():
    parser = argparse.ArgumentParser(description="Bronze -> Silver de reclamos")
    parser.add_argument("--input", type=Path, default=ROOT / "data/bronze/complaints/consumer_complaints.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data/silver/complaints/complaints.parquet")
    parser.add_argument("--quality", type=Path, default=ROOT / "artifacts/reports/complaints/silver_quality.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "docs/reclamos/calidad-silver.md")
    args = parser.parse_args()
    try:
        report = build_silver_complaints(args.input, args.output, args.quality, args.markdown)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    c = report["counts"]
    print(f"Bronze {c['bronze_rows']:,} -> Silver {c['silver_rows']:,} "
          f"(rechazadas {c['rejected_rows']}, duplicados {c['duplicate_ids_removed']}); "
          f"narrativas {c['silver_narratives']:,}")


if __name__ == "__main__":
    main()
