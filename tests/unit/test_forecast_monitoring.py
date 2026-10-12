import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from bankshield.models.monitoring import (
    compare_monitoring_windows,
    run_historical_monitoring,
)


def monitoring_config():
    return {
        "experiment_id": "monitoring-fixture",
        "reference_period": {"start_step": 1, "end_step": 2},
        "observed_period": {"start_step": 3, "end_step": 4},
        "thresholds": {
            "transaction_count_relative_change": 0.25,
            "total_amount_relative_change": 0.25,
            "average_amount_relative_change": 0.25,
            "amount_distribution_tvd": 0.2,
            "type_mix_tvd": 0.2,
            "fraud_rate_absolute_change": 0.2,
        },
    }


def transactions():
    return pd.DataFrame(
        {
            "step": [1, 1, 2, 2, 3, 4],
            "type": ["PAYMENT", "TRANSFER", "PAYMENT", "TRANSFER", "TRANSFER", "TRANSFER"],
            "amount": [10.0, 20.0, 30.0, 40.0, 100.0, 200.0],
            "isFraud": [0, 0, 0, 0, 1, 1],
        }
    )


class ForecastMonitoringTests(unittest.TestCase):
    def test_detects_changes_in_activity_amount_types_and_fraud(self):
        report = compare_monitoring_windows(transactions(), monitoring_config())

        self.assertEqual(report["reference"]["transaction_count"], 4)
        self.assertEqual(report["observed"]["transaction_count"], 2)
        self.assertEqual(report["changes"]["transaction_count_relative_change"], -0.5)
        self.assertEqual(report["changes"]["fraud_rate_absolute_change"], 1.0)
        self.assertEqual(report["type_mix"]["categories"]["PAYMENT"]["observed_share"], 0.0)
        self.assertEqual(report["status"], "change_detected")
        self.assertGreaterEqual(report["alert_count"], 4)

    def test_requires_equal_non_overlapping_windows(self):
        overlapping = monitoring_config()
        overlapping["observed_period"] = {"start_step": 2, "end_step": 3}
        unequal = monitoring_config()
        unequal["observed_period"] = {"start_step": 3, "end_step": 5}

        for config in (overlapping, unequal):
            with self.subTest(config=config):
                with self.assertRaises(ValueError):
                    compare_monitoring_windows(transactions(), config)

    def test_rejects_invalid_transaction_contract(self):
        invalid_frames = [
            transactions().drop(columns="type"),
            transactions().assign(amount=-1.0),
            transactions().assign(isFraud=2),
            transactions().assign(step=1.5),
        ]
        for frame in invalid_frames:
            with self.subTest(columns=list(frame.columns)):
                with self.assertRaises(ValueError):
                    compare_monitoring_windows(frame, monitoring_config())

    def test_writes_json_and_markdown_reports(self):
        root = Path(__file__).resolve().parents[2]
        parent = root / "artifacts" / "reports" / "forecast-monitoring-tests"
        parent.mkdir(parents=True, exist_ok=True)
        workdir = parent / uuid.uuid4().hex
        workdir.mkdir()
        self.addCleanup(shutil.rmtree, workdir, True)
        input_path = workdir / "silver.parquet"
        output_path = workdir / "monitoring.json"
        markdown_path = workdir / "monitoring.md"
        input_path.write_bytes(b"fixture")

        with patch(
            "bankshield.models.monitoring.pd.read_parquet",
            return_value=transactions(),
        ) as read_parquet:
            report = run_historical_monitoring(
                input_path,
                output_path,
                markdown_path,
                monitoring_config(),
                base_dir=root,
            )

        read_parquet.assert_called_once_with(
            input_path,
            columns=["step", "type", "amount", "isFraud"],
            filters=[("step", ">=", 1), ("step", "<=", 4)],
        )
        stored = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(stored["status"], report["status"])
        self.assertEqual(len(stored["source"]["sha256"]), 64)
        self.assertIn("Monitoreo histórico", markdown_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
