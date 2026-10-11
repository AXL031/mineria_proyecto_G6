import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pandas as pd

from bankshield.features.fraud import MODEL_FEATURES
from bankshield.transforms.gold_transactions import (
    GOLD_COLUMNS,
    build_gold_transactions,
    transform_transactions,
)


def sample_silver():
    return pd.DataFrame(
        {
            "step": [1, 1, 2],
            "type": ["PAYMENT", "TRANSFER", "CASH_OUT"],
            "amount": [100.0, 200.0, 50.0],
            "nameOrig": ["C1", "C2", "C3"],
            "oldbalanceOrg": [500.0, 100.0, 800.0],
            "newbalanceOrig": [400.0, 0.0, 750.0],
            "nameDest": ["M1", "C3", "C1"],
            "oldbalanceDest": [0.0, 50.0, 300.0],
            "newbalanceDest": [100.0, 250.0, 350.0],
            "isFraud": [0, 1, 0],
            "isFlaggedFraud": [0, 0, 1],
        }
    )


class GoldTransactionsTests(unittest.TestCase):
    def test_transform_builds_one_row_per_transaction(self):
        gold = transform_transactions(sample_silver())

        self.assertEqual(gold.columns.tolist(), list(GOLD_COLUMNS))
        self.assertEqual(len(gold), 3)
        self.assertEqual(gold["step"].tolist(), [1, 1, 2])
        self.assertEqual(gold["isFraud"].tolist(), [0, 1, 0])
        self.assertEqual(gold["isFlaggedFraud"].tolist(), [0, 0, 1])
        self.assertEqual(gold["exceeds_origin_balance"].tolist(), [0, 1, 0])

    def test_predictors_reuse_fraud_contract(self):
        gold = transform_transactions(sample_silver())

        for column in MODEL_FEATURES:
            self.assertIn(column, gold.columns)
        expected = 200.0 / (100.0 + 1.0)
        self.assertAlmostEqual(gold["amount_to_origin_balance"].iloc[1], expected, places=9)

    def test_balance_residuals_are_descriptive(self):
        gold = transform_transactions(sample_silver())

        self.assertEqual(gold["origin_balance_delta"].tolist(), [0.0, 100.0, 0.0])
        self.assertEqual(gold["destination_balance_delta"].tolist(), [0.0, 0.0, 0.0])

    def test_rejects_invalid_input(self):
        with self.assertRaisesRegex(ValueError, "Faltan columnas"):
            transform_transactions(pd.DataFrame({"step": [1]}))
        with self.assertRaisesRegex(ValueError, "vacío"):
            transform_transactions(
                pd.DataFrame(columns=[
                    "step", "type", "amount", "nameOrig", "oldbalanceOrg",
                    "newbalanceOrig", "nameDest", "oldbalanceDest",
                    "newbalanceDest", "isFraud", "isFlaggedFraud",
                ])
            )
        bad_label = sample_silver()
        bad_label.loc[0, "isFraud"] = 2
        with self.assertRaisesRegex(ValueError, "isFraud"):
            transform_transactions(bad_label)
        missing = sample_silver()
        missing.loc[0, "newbalanceDest"] = None
        with self.assertRaisesRegex(ValueError, "ausentes"):
            transform_transactions(missing)

    def test_build_writes_gold_and_quality_reports(self):
        root = Path(__file__).resolve().parents[2]
        parent = root / "artifacts" / "reports" / "transactions-gold-tests"
        parent.mkdir(parents=True, exist_ok=True)
        workdir = parent / uuid.uuid4().hex
        workdir.mkdir()
        self.addCleanup(shutil.rmtree, workdir, True)

        silver = workdir / "silver.parquet"
        gold_path = workdir / "gold.parquet"
        quality_json = workdir / "quality.json"
        quality_markdown = workdir / "quality.md"
        sample_silver().to_parquet(silver, index=False)

        report = build_gold_transactions(
            silver,
            gold_path,
            quality_json=quality_json,
            quality_markdown=quality_markdown,
            chunksize=2,
            base_dir=root,
        )

        self.assertTrue(gold_path.exists())
        self.assertEqual(report["counts"]["input_rows"], 3)
        self.assertEqual(report["counts"]["output_rows"], 3)
        self.assertTrue(all(report["quality_checks"].values()))
        self.assertEqual(report["totals"]["fraud"], 1)
        self.assertEqual(report["totals"]["origin_residuals_nonzero"], 1)
        stored = pd.read_parquet(gold_path)
        self.assertEqual(stored.columns.tolist(), list(GOLD_COLUMNS))
        self.assertEqual(len(stored), 3)
        written = json.loads(quality_json.read_text(encoding="utf-8"))
        self.assertEqual(written["predictor_columns"], list(MODEL_FEATURES))
        self.assertIn(
            "# Calidad del mart transaccional Gold",
            quality_markdown.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
