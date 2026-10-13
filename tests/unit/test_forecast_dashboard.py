"""Interacciones de la página temporal y su contrato con la API."""

import json
from pathlib import Path
import unittest
from unittest.mock import patch

import requests
from streamlit.testing.v1 import AppTest


PAGE = Path(__file__).resolve().parents[2] / "dashboard/pages/04_pronosticos.py"


def response(status, payload):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(payload).encode("utf-8")
    return result


PROJECTION = {
    "target": "transaction_count",
    "selected_model": "naive",
    "last_observed_step": 743,
    "last_observed_value": 8.0,
    "horizon": 2,
    "history": [{"step": 742, "value": 14.0}, {"step": 743, "value": 8.0}],
    "forecast": [
        {"step": 744, "prediction": 8.0, "lower": 0.0, "upper": 20.0},
        {"step": 745, "prediction": 8.0, "lower": 0.0, "upper": 25.0},
    ],
    "uncertainty": {"calibrated": False},
    "limitations": ["Intervalo no calibrado."],
}

MONITORING = {
    "status": "change_detected",
    "alert_count": 2,
    "reference": {"start_step": 694, "end_step": 718},
    "observed": {
        "start_step": 719,
        "end_step": 743,
        "transaction_count": 296,
        "total_amount": 468962836.94,
        "average_amount": 1584333.91,
        "fraud_rate": 1.0,
    },
    "changes": {
        "transaction_count_relative_change": -0.98,
        "total_amount_relative_change": -0.82,
        "average_amount_relative_change": 9.26,
        "fraud_rate_absolute_change": 0.98,
    },
    "type_mix": {
        "categories": {
            "TRANSFER": {
                "reference_share": 0.1,
                "observed_share": 0.5,
                "percentage_point_change": 0.4,
            }
        }
    },
}


class ForecastDashboardTests(unittest.TestCase):
    def test_requests_projection_and_displays_metrics(self):
        app = AppTest.from_file(str(PAGE)).run()
        with patch("requests.get", return_value=response(200, PROJECTION)) as request:
            app.button[0].click().run()

        self.assertFalse(app.exception)
        self.assertEqual(request.call_args.kwargs["params"]["target"], "transaction_count")
        self.assertEqual([metric.value for metric in app.metric], ["8", "743", "naive"])

    def test_requests_monitoring_and_handles_unavailable_artifact(self):
        app = AppTest.from_file(str(PAGE)).run()
        with patch("requests.get", return_value=response(200, MONITORING)):
            app.button[1].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.warning), 1)
        self.assertEqual(len(app.metric), 4)

        unavailable = AppTest.from_file(str(PAGE)).run()
        with patch("requests.get", return_value=response(503, {})):
            unavailable.button[0].click().run()
        self.assertFalse(unavailable.exception)
        self.assertEqual(len(unavailable.error), 1)


if __name__ == "__main__":
    unittest.main()
