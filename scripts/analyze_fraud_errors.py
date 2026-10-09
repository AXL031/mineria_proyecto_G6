"""Revisa ejemplos TP/FP/FN/TN de prueba sin ajustar el modelo ni el umbral."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pyarrow.parquet as pq

from bankshield.ingestion.paysim_profile import _sha256
from bankshield.services.fraud import FraudScorer


def analyze(input_path, model_path, output_path, examples=3):
    if examples < 1:
        raise ValueError("examples debe ser positivo")
    scorer = FraudScorer(model_path)
    training = scorer.metadata.get("training_input", {})
    if training.get("format") != "silver" or training.get("sha256", "").lower() != _sha256(input_path).lower():
        raise ValueError("Se requiere el Silver exacto registrado en este modelo")
    cut = scorer.metadata["config"]["validation_end_step"]
    counts = Counter({key: 0 for key in ("tp", "fp", "fn", "tn")})
    cases = {key: [] for key in counts}
    offset = 0
    for batch in pq.ParquetFile(input_path).iter_batches(batch_size=100_000):
        frame = batch.to_pandas()
        frame.index = range(offset, offset + len(frame))
        offset += len(frame)
        test = frame.loc[frame["step"] > cut]
        if test.empty:
            continue
        records = test[["type", "amount", "oldbalanceOrg"]].to_dict(orient="records")
        results = scorer.score(records)
        for (index, row), result in zip(test.iterrows(), results):
            label = bool(row["isFraud"])
            key = ("tp" if label else "fp") if result["alert"] else ("fn" if label else "tn")
            counts[key] += 1
            if len(cases[key]) < examples:
                cases[key].append({"source_row_zero_based": int(index), "step": int(row["step"]),
                                   "input": {"type": row["type"], "amount": float(row["amount"]),
                                             "oldbalanceOrg": float(row["oldbalanceOrg"])},
                                   "isFraud": int(label), **result,
                                   "observed_conditions": {
                                       "amount_to_origin_balance": float(row["amount"] / (row["oldbalanceOrg"] + 1)),
                                       "exceeds_origin_balance": bool(row["amount"] > row["oldbalanceOrg"])}})
    expected = scorer.metadata["test"]["classifier_selected"]["confusion"]
    if dict(counts) != expected:
        raise ValueError("La matriz de confusión no coincide con la evaluación embebida")
    report = {"model_id": scorer.model_id, "training_input": training,
              "threshold": scorer.threshold, "confusion": dict(counts), "examples": cases,
              "selection": "first_rows_per_outcome_in_frozen_test_partition",
              "limitations": ["examples_are_not_representative", "conditions_are_not_model_attributions",
                              "test_cases_must_not_be_used_to_tune_this_model"]}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/silver/transactions/transactions.parquet")
    parser.add_argument("--model", type=Path, default=ROOT / "artifacts/models/fraud-silver/model.joblib")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/reports/fraud-silver-errors.json")
    parser.add_argument("--examples", type=int, default=3)
    args = parser.parse_args()
    try:
        report = analyze(args.input, args.model, args.output, args.examples)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(f"Confusión: {report['confusion']} | Ejemplos: {args.output}")


if __name__ == "__main__":
    main()
