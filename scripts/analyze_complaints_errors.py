"""Extrae ejemplos de revisión del clasificador de reclamos en la partición de prueba."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankshield.models.complaints_review import build_error_review, write_review


def main():
    parser = argparse.ArgumentParser(description="Revisión de ejemplos de reclamos")
    parser.add_argument("--model", type=Path, default=ROOT / "artifacts/models/complaints/model.joblib")
    parser.add_argument("--input", type=Path, default=ROOT / "data/silver/complaints/complaints.parquet")
    parser.add_argument("--quality", type=Path, default=ROOT / "artifacts/reports/complaints/silver_quality.json")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/reports/complaints/error_examples.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "docs/reclamos/revision-ejemplos.md")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    try:
        review = build_error_review(args.model, args.input, args.quality, seed=args.seed)
        write_review(review, args.output, args.markdown)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(f"Prueba: {review['test_rows']:,} reclamos, {review['errors']:,} errores")
    print(f"JSON: {args.output}\nMarkdown: {args.markdown}")


if __name__ == "__main__":
    main()
