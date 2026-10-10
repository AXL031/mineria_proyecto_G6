import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from bankshield.evaluation.forecast import run_forecast_baseline_evaluation


def evaluation_config():
    return {
        "experiment_id": "fixture-baselines",
        "targets": ["transaction_count", "total_amount"],
        "operational_period": {"start_step": 1, "end_step": 8},
        "monitoring_period": {"start_step": 9, "end_step": 12},
        "horizon": 2,
        "backtest_windows": [
            {
                "id": "W01",
                "train_start_step": 1,
                "train_end_step": 4,
                "test_start_step": 5,
                "test_end_step": 6,
            },
            {
                "id": "W02",
                "train_start_step": 1,
                "train_end_step": 6,
                "test_start_step": 7,
                "test_end_step": 8,
            },
        ],
        "models": {"naive": {}, "seasonal_naive": {"lag": 2}},
        "metrics": {"primary": "mae", "secondary": ["rmse", "smape"]},
    }


def small_series():
    return pd.DataFrame(
        {
            "step": list(range(1, 13)),
            "transaction_count": [10, 20] * 4 + [1000, 2000] * 2,
            "total_amount": [100.0, 200.0] * 4 + [10000.0, 20000.0] * 2,
        }
    )


class ForecastBacktestingTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[2]
        parent = root / "artifacts" / "reports" / "forecast-backtest-tests"
        parent.mkdir(parents=True, exist_ok=True)
        self.workdir = parent / uuid.uuid4().hex
        self.workdir.mkdir()
        self.addCleanup(shutil.rmtree, self.workdir, True)

    def test_runs_both_models_on_the_same_windows_and_writes_report(self):
        input_path = self.workdir / "gold.parquet"
        output_path = self.workdir / "baselines.json"
        input_path.write_bytes(b"small-parquet-fixture")

        with patch(
            "bankshield.evaluation.forecast.pd.read_parquet",
            return_value=small_series(),
        ) as read_parquet:
            report = run_forecast_baseline_evaluation(
                input_path,
                output_path,
                evaluation_config(),
                base_dir=Path(__file__).resolve().parents[2],
            )

        read_parquet.assert_called_once_with(
            input_path,
            columns=["step", "transaction_count", "total_amount"],
        )
        self.assertEqual(len(report["windows"]), 2)
        for window in report["windows"]:
            self.assertEqual(window["test"]["rows"], 2)
            self.assertEqual(
                set(window["results"]["transaction_count"]),
                {"naive", "seasonal_naive"},
            )

        count_aggregates = report["aggregates"]["transaction_count"]
        amount_aggregates = report["aggregates"]["total_amount"]
        self.assertEqual(count_aggregates["seasonal_naive"]["mae"], 0.0)
        self.assertEqual(amount_aggregates["seasonal_naive"]["mae"], 0.0)
        self.assertEqual(count_aggregates["naive"]["mae"], 5.0)
        self.assertEqual(amount_aggregates["naive"]["mae"], 50.0)

        stored = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(stored["experiment_id"], "fixture-baselines")
        self.assertEqual(stored["protocol"]["monitoring_period"]["start_step"], 9)
        self.assertEqual(stored["series_coverage"]["max_step"], 12)
        self.assertEqual(stored["windows"][-1]["test"]["end_step"], 8)
        self.assertEqual(len(stored["source"]["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
