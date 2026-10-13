"""Entrena y evalúa el clasificador de producto de reclamos desde Silver."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankshield.models.complaints import MAIN_KEY, ComplaintsConfig, train_complaints


def main():
    parser = argparse.ArgumentParser(description="Entrenamiento NLP de reclamos")
    parser.add_argument("--input", type=Path, default=ROOT / "data/silver/complaints/complaints.parquet")
    parser.add_argument("--quality", type=Path, default=ROOT / "artifacts/reports/complaints/silver_quality.json")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/complaints.json")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/models/complaints")
    parser.add_argument("--markdown", type=Path, default=ROOT / "docs/reclamos/resultados-modelo.md")
    args = parser.parse_args()
    try:
        config = ComplaintsConfig(**json.loads(args.config.read_text(encoding="utf-8")))
        report = train_complaints(args.input, args.quality, config, args.output, args.markdown)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    for key in ("prior", "naive_bayes", MAIN_KEY):
        r = report["test"][key]
        print(f"Prueba {key}: exactitud {r['accuracy']:.4f}, macro-F1 {r['macro_f1']:.4f}, top-3 {r['top3_accuracy']:.4f}")
    print(f"Modelo: {args.output}")


if __name__ == "__main__":
    main()
