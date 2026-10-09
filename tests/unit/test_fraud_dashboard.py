"""Interacciones de la página: contrato API, persistencia y errores de conexión."""

import json
from pathlib import Path
import unittest
from unittest.mock import patch

import requests
from streamlit.testing.v1 import AppTest

PAGE = Path(__file__).resolve().parents[2] / "dashboard/pages/01_fraude.py"


def response(status, payload):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(payload).encode("utf-8")
    return result


class FraudDashboardTests(unittest.TestCase):
    def test_form_sends_transaction_and_keeps_result_when_loading_metrics(self):
        result = {"score": 0.25, "threshold": 0.1, "alert": True,
                  "score_is_calibrated": False, "simulation_data": True, "model_id": "fixture"}
        app = AppTest.from_file(str(PAGE)).run()
        with patch("requests.request", return_value=response(200, result)) as request:
            app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(request.call_args.kwargs["json"],
                         {"type": "TRANSFER", "amount": 1000.0, "oldbalanceOrg": 500.0})
        self.assertEqual(request.call_args.kwargs["timeout"], 20)
        self.assertEqual([metric.value for metric in app.metric], ["0.250000", "0.100000", "Sí"])
        with patch("requests.request", return_value=response(200, {"model_id": "fixture", "test": {}})):
            app.button[1].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.metric), 3)

    def test_unavailable_api_and_missing_model_show_errors_without_scores(self):
        for failure in (requests.ConnectionError("offline"), response(503, {"detail": "missing"})):
            app = AppTest.from_file(str(PAGE)).run()
            options = {"side_effect": failure} if isinstance(failure, Exception) else {"return_value": failure}
            with self.subTest(failure=failure), patch("requests.request", **options):
                app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.error), 1)
            self.assertEqual(len(app.metric), 0)


if __name__ == "__main__":
    unittest.main()
