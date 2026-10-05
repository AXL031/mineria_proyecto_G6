"""Predicción local para comprobar el artefacto entrenado."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankshield.services.fraud import FraudScorer


def main():
    parser = argparse.ArgumentParser(description="Scoring de fraude antes de la transacción")
    parser.add_argument("--model", type=Path, default=ROOT / "artifacts/models/fraud/model.joblib")
    parser.add_argument("--type", required=True)
    parser.add_argument("--amount", required=True, type=float)
    parser.add_argument("--origin-balance", required=True, type=float)
    args = parser.parse_args()
    try:
        scorer = FraudScorer(args.model)
        result = scorer.score([{"type": args.type, "amount": args.amount,
                                "oldbalanceOrg": args.origin_balance}])
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(json.dumps(result[0], indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
