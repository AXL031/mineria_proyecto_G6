import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pandas as pd

from bankshield.transforms.temporal_transactions import (
    GOLD_COLUMNS,
    aggregate_temporal_transactions,
    build_temporal_gold,
)


class TemporalTransactionsTests(unittest.TestCase):
    def test_aggregates_one_row_per_step(self):
        transactions = pd.DataFrame(
            {
                "step": [2, 1, 1, 2],
                "amount": [80.0, 100.0, 50.0, 20.0],
                "isFraud": [0, 0, 1, 1],
            }
        )

        gold = aggregate_temporal_transactions(transactions)

        self.assertEqual(gold.columns.tolist(), list(GOLD_COLUMNS))
        self.assertEqual(gold["step"].tolist(), [1, 2])
        self.assertEqual(gold["transaction_count"].tolist(), [2, 2])
        self.assertEqual(gold["total_amount"].tolist(), [150.0, 100.0])
        self.assertEqual(gold["average_amount"].tolist(), [75.0, 50.0])
        self.assertEqual(gold["fraud_count"].tolist(), [1, 1])
        self.assertEqual(gold["fraud_rate"].tolist(), [0.5, 0.5])

    def test_fills_missing_steps_with_zero_activity(self):
        transactions = pd.DataFrame(
            {
                "step": [1, 3],
                "amount": [10.0, 20.0],
                "isFraud": [0, 0],
            }
        )

        gold = aggregate_temporal_transactions(transactions)

        self.assertEqual(gold["step"].tolist(), [1, 2, 3])
        empty_hour = gold.loc[gold["step"] == 2].iloc[0]
        self.assertEqual(empty_hour["transaction_count"], 0)
        self.assertEqual(empty_hour["total_amount"], 0.0)
        self.assertEqual(empty_hour["average_amount"], 0.0)
        self.assertEqual(empty_hour["fraud_rate"], 0.0)

    def test_rejects_invalid_input(self):
        with self.assertRaisesRegex(ValueError, "Faltan columnas"):
            aggregate_temporal_transactions(pd.DataFrame({"step": [1]}))
        with self.assertRaisesRegex(ValueError, "vacío"):
            aggregate_temporal_transactions(
                pd.DataFrame(columns=["step", "amount", "isFraud"])
            )
        with self.assertRaisesRegex(ValueError, "amount"):
            aggregate_temporal_transactions(
                pd.DataFrame({"step": [1], "amount": [-1], "isFraud": [0]})
            )
        with self.assertRaisesRegex(ValueError, "isFraud"):
            aggregate_temporal_transactions(
                pd.DataFrame({"step": [1], "amount": [1], "isFraud": [2]})
            )

    def test_build_writes_gold_and_quality_reports(self):
        root = Path(__file__).resolve().parents[2]
        parent = root / "artifacts" / "reports" / "forecast-tests"
        parent.mkdir(parents=True, exist_ok=True)
        workdir = parent / uuid.uuid4().hex
        workdir.mkdir()
        self.addCleanup(shutil.rmtree, workdir, True)

        silver = workdir / "silver.parquet"
        gold_path = workdir / "gold.parquet"
        quality_json = workdir / "quality.json"
        quality_markdown = workdir / "quality.md"
        pd.DataFrame(
            {
                "step": [1, 1, 2],
                "amount": [100.0, 50.0, 25.0],
                "isFraud": [0, 1, 0],
            }
        ).to_parquet(silver, index=False)

        report = build_temporal_gold(
            silver,
            gold_path,
            quality_json=quality_json,
            quality_markdown=quality_markdown,
            base_dir=root,
        )

        self.assertTrue(gold_path.exists())
        self.assertEqual(report["counts"]["input_transactions"], 3)
        self.assertEqual(report["counts"]["gold_rows"], 2)
        self.assertTrue(all(report["quality_checks"].values()))
        stored = json.loads(quality_json.read_text(encoding="utf-8"))
        self.assertEqual(stored["totals"]["fraud"], 1)
        self.assertIn(
            "# Calidad de la tabla Gold temporal",
            quality_markdown.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
