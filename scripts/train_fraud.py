"""Entrena y evalúa la primera versión del módulo de fraude."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankshield.models.fraud import FraudConfig, train_fraud


def main():
    parser = argparse.ArgumentParser(description="Entrenamiento temporal de fraude")
    parser.add_argument("--input", type=Path, default=ROOT / "data/bronze/transactions/PS_20174392719_1491204439457_log.csv")
    parser.add_argument("--input-format", choices=("csv", "silver"), default="csv")
    parser.add_argument("--silver-quality", type=Path,
                        default=ROOT / "artifacts/reports/transactions_silver.json")
    parser.add_argument("--profile", type=Path, default=ROOT / "artifacts/reports/fraud/paysim_profile.json")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/fraud.json")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/models/fraud")
    parser.add_argument("--markdown", type=Path, default=ROOT / "docs/fraude/resultados-entrenamiento.md")
    args = parser.parse_args()
    try:
        config = FraudConfig(**json.loads(args.config.read_text(encoding="utf-8")))
        train_fraud(args.input, config, args.profile, args.output, args.markdown,
                    input_format=args.input_format, silver_quality_path=args.silver_quality)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
