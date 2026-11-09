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
    result._content = json.dumps(payload).encode()
    return result


class RegressionDashboardTests(unittest.TestCase):
    def test_prediction_persists_during_evaluation_and_model_change_is_signaled(self):
        app = AppTest.from_file(str(PAGE), default_timeout=30).run()
        predicted = {"prediction": 100., "model_id": "first", "selected_model": "median_by_type"}
        with patch("requests.request", return_value=response(200, predicted)) as request:
            app.button(key="regression_predict").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(request.call_args.kwargs["json"], {"type": "TRANSFER", "oldbalanceOrg": 500.})
        evaluation = {"model_id": "second", "selected_model": "median_by_type", "dataset": {},
                      "sampling": {}, "selection": {}, "limitations": [],
                      "evaluation": {part: {"median_by_type": {"overall": {"mae": 1}}}
                                     for part in ("validation", "test", "stress")}}
        with patch("requests.request", return_value=response(200, evaluation)):
            app.button(key="regression_evaluation").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "100.00")
        self.assertTrue(any("modelo cambió" in item.value for item in app.warning))

    def test_missing_model_and_disconnection_display_errors(self):
        for option in ({"return_value": response(503, {})}, {"side_effect": requests.ConnectionError()}):
            app = AppTest.from_file(str(PAGE), default_timeout=30).run()
            with patch("requests.request", **option):
                app.button(key="regression_predict").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.error)
            self.assertFalse(app.metric)

    def test_examples_scatter_and_empty_page(self):
        for rows in ([], [{"type": "TRANSFER", "step": 400, "actual": 10., "prediction": 20.}]):
            app = AppTest.from_file(str(PAGE), default_timeout=30).run()
            with patch("requests.request", return_value=response(200, {"rows": rows, "model_id": "fixture"})):
                app.button(key="regression_examples").click().run()
            self.assertFalse(app.exception)
