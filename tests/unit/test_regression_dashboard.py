"""Página de regresión: contrato API, evaluación y errores."""

import json
from pathlib import Path
import unittest
from unittest.mock import patch

import requests
from streamlit.testing.v1 import AppTest

PAGE = Path(__file__).resolve().parents[2] / "dashboard/pages/07_regresion.py"


def response(status, payload):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(payload).encode("utf-8")
    return result


def score(mae):
    return {"n": 10, "mae": mae, "rmse": mae * 2, "r2": 0.1, "mean_bias": -1.0}


PREDICTION = {"model_id": "fixture", "target": "amount", "prediction": 1234.5, "selected_model": "reference",
              "simulation_data": True, "limitations": ["Estimación académica; no constituye una alerta de fraude."]}
MODEL = {"model_id": "fixture", "selected_model": "reference", "selection_rule": "r", "train_sample": {},
         "partitions": {}, "versions": {}, "limitations": [],
         "comparison": {"reference": {"validation": score(1.0), "test": score(2.0), "stress": score(3.0)}}}
EXAMPLES = {"model_id": "fixture", "total": 1,
            "rows": [{"row_id": 1, "type": "PAYMENT", "actual": 10.0, "prediction": 12.0}]}


def route(method, url, **kwargs):
    if url.endswith("/predict"):
        return response(200, PREDICTION)
    return response(200, EXAMPLES if url.endswith("/examples") else MODEL)


class RegressionDashboardTests(unittest.TestCase):
    def test_form_sends_exact_fields_and_persists_prediction(self):
        app = AppTest.from_file(str(PAGE)).run()
        with patch("requests.request", side_effect=route) as request:
            app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(request.call_args.kwargs["json"], {"type": "TRANSFER", "oldbalanceOrg": 500.0})
        self.assertEqual([m.value for m in app.metric], ["1,234.50"])
        with patch("requests.request", side_effect=route):
            app.button[1].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.metric), 1)
        self.assertGreaterEqual(len(app.dataframe), 3)

    def test_api_failures_show_errors_without_estimate(self):
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
