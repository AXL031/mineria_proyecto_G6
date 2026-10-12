"""Entrena, calibra y evalúa el modelo de riesgo crediticio."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankshield.models.credit import CreditConfig, train_credit


def main():
    parser = argparse.ArgumentParser(description="Entrenamiento de crédito")
    parser.add_argument("--input", type=Path, default=ROOT / "data/silver/credit/credit.parquet")
    parser.add_argument("--quality", type=Path, default=ROOT / "artifacts/reports/credit/silver_quality.json")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/credit.json")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/models/credit")
    parser.add_argument("--markdown", type=Path, default=ROOT / "docs/credito/resultados-modelo.md")
    args = parser.parse_args()
    try:
        config = CreditConfig(**json.loads(args.config.read_text(encoding="utf-8")))
        report = train_credit(args.input, args.quality, config, args.output, args.markdown)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    main_test = report["test"]["hist_gradient_boosting:application:calibrated"]
    print(f"Prueba (calibrado): ROC-AUC {main_test['roc_auc']:.4f}, AP {main_test['average_precision']:.4f}, "
          f"Brier {main_test['brier']:.4f}, ECE {main_test['ece']:.4f}")
    print(f"Modelo: {args.output}")


if __name__ == "__main__":
    main()
