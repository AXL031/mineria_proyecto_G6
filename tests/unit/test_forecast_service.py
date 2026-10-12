import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from bankshield.services.forecast import (
    build_forecast_projection,
    monitoring_summary,
)


class ForecastServiceTests(unittest.TestCase):
    def test_builds_naive_projection_after_the_last_observed_step(self):
        series = pd.DataFrame(
            {
                "step": range(1, 31),
                "transaction_count": range(10, 40),
                "total_amount": np.arange(10.0, 40.0) * 100,
            }
        )

        result = build_forecast_projection(
            series,
            target="transaction_count",
            horizon=3,
            history_steps=24,
        )

        self.assertEqual(result["last_observed_step"], 30)
        self.assertEqual(len(result["history"]), 24)
        self.assertEqual([point["step"] for point in result["forecast"]], [31, 32, 33])
        self.assertEqual(
            [point["prediction"] for point in result["forecast"]],
            [39.0, 39.0, 39.0],
        )
        self.assertTrue(
            all(point["lower"] <= point["prediction"] <= point["upper"] for point in result["forecast"])
        )
        self.assertFalse(result["uncertainty"]["calibrated"])

    def test_rejects_invalid_series_and_parameters(self):
        valid = pd.DataFrame({"step": range(1, 5), "transaction_count": [1, 2, 3, 4]})
        calls = [
            lambda: build_forecast_projection(valid, target="fraud_count"),
            lambda: build_forecast_projection(valid, target="transaction_count", horizon=0),
            lambda: build_forecast_projection(
                valid.assign(step=[1, 2, 4, 5]), target="transaction_count"
            ),
            lambda: build_forecast_projection(
                valid.assign(transaction_count=[1, -2, 3, 4]),
                target="transaction_count",
            ),
        ]
        for call in calls:
            with self.subTest(call=call):
                with self.assertRaises(ValueError):
                    call()

    def test_validates_monitoring_report_contract(self):
        report = {
            "experiment_id": "fixture",
            "reference": {},
            "observed": {},
            "changes": {},
            "type_mix": {},
            "thresholds": {},
            "alerts": {},
            "alert_count": 0,
            "status": "stable",
            "limitations": [],
        }
        self.assertEqual(monitoring_summary(report)["status"], "stable")
        with self.assertRaises(ValueError):
            monitoring_summary({**report, "status": "unknown"})


if __name__ == "__main__":
    unittest.main()
