"""Interacciones de la página de crédito: contrato API y manejo de errores."""

import json
from pathlib import Path
import unittest
from unittest.mock import patch

import requests
from streamlit.testing.v1 import AppTest

PAGE = Path(__file__).resolve().parents[2] / "dashboard/pages/02_credito.py"


def response(status, payload):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(payload).encode("utf-8")
    return result


RESULT = {"default_probability": 0.3, "high_risk": True, "threshold": 0.15, "model_id": "fixture",
          "factors": [{"feature": "loan_amnt", "value": 10000.0, "reference": 8000.0, "effect": 0.05}],
          "explanation_method": "occlusion", "explanation_is_causal": False}


class CreditDashboardTests(unittest.TestCase):
    def test_form_sends_application_and_shows_metrics(self):
        app = AppTest.from_file(str(PAGE)).run()
        with patch("requests.request", return_value=response(200, RESULT)) as request:
            app.button[0].click().run()
        self.assertFalse(app.exception)
        sent = request.call_args.kwargs["json"]
        self.assertEqual(sent["person_age"], 30)
        self.assertEqual(sent["person_emp_length"], 4.0)
        self.assertNotIn("loan_grade", sent)
        self.assertNotIn("loan_int_rate", sent)
        self.assertEqual([m.value for m in app.metric], ["30.0%", "15.0%", "Alto riesgo"])
        with patch("requests.request", return_value=response(200, {"model_id": "fixture", "test": {}})):
            app.button[1].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.metric), 3)

    def test_unknown_employment_sends_null(self):
        app = AppTest.from_file(str(PAGE)).run()
        app.checkbox[0].check()
        with patch("requests.request", return_value=response(200, RESULT)) as request:
            app.button[0].click().run()
        self.assertIsNone(request.call_args.kwargs["json"]["person_emp_length"])

    def test_api_failures_show_errors_without_scores(self):
        for failure in (requests.ConnectionError("offline"), response(503, {}), response(422, {})):
            app = AppTest.from_file(str(PAGE)).run()
            options = {"side_effect": failure} if isinstance(failure, Exception) else {"return_value": failure}
            with self.subTest(failure=failure), patch("requests.request", **options):
                app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.error), 1)
            self.assertEqual(len(app.metric), 0)


if __name__ == "__main__":
    unittest.main()
