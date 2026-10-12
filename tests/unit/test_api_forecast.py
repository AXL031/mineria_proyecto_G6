import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from api.routers.forecast import monitoring, projection


class ForecastAPITests(unittest.TestCase):
    def test_projection_exposes_service_contract(self):
        series = pd.DataFrame(
            {
                "step": range(1, 31),
                "transaction_count": range(1, 31),
                "total_amount": [float(value * 10) for value in range(1, 31)],
            }
        )

        body = projection(
            target="transaction_count",
            horizon=2,
            history_steps=24,
            series=series,
        )

        self.assertEqual(body["selected_model"], "naive")
        self.assertEqual(body["forecast"][0]["step"], 31)
        self.assertTrue(body["simulation_data"])

    def test_monitoring_exposes_compatible_report(self):
        report = {
            "experiment_id": "fixture",
            "reference": {},
            "observed": {},
            "changes": {},
            "type_mix": {},
            "thresholds": {},
            "alerts": {},
            "alert_count": 1,
            "status": "change_detected",
            "limitations": [],
            "ignored": "not exposed",
        }

        body = monitoring(report=report)

        self.assertEqual(body["status"], "change_detected")
        self.assertNotIn("ignored", body)


if __name__ == "__main__":
    unittest.main()
