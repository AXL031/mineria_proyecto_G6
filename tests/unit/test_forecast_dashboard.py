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
    def page(self):
        # El arranque en frío importa pandas/Arrow y carga los recursos locales.
        return AppTest.from_file(str(PAGE), default_timeout=30).run()

    def test_requests_projection_and_displays_metrics(self):
        app = self.page()
        with patch("requests.get", return_value=response(200, PROJECTION)) as request:
            app.button[0].click().run()

        self.assertFalse(app.exception)
        self.assertEqual(request.call_args.kwargs["params"]["target"], "transaction_count")
        self.assertEqual([metric.value for metric in app.metric], ["8", "743", "naive"])

    def test_requests_monitoring_and_handles_unavailable_artifact(self):
        app = self.page()
        with patch("requests.get", return_value=response(200, MONITORING)):
            app.button[1].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.warning), 1)
        self.assertEqual(len(app.metric), 4)

        unavailable = self.page()
        with patch("requests.get", return_value=response(503, {})):
            unavailable.button[0].click().run()
        self.assertFalse(unavailable.exception)
        self.assertEqual(len(unavailable.error), 1)
        with patch("requests.get", return_value=response(503, {})):
            unavailable.button[1].click().run()
        self.assertFalse(unavailable.exception)
        self.assertEqual(len(unavailable.error), 1)

    def test_amount_and_horizon_controls_are_sent_to_api(self):
        app = self.page()
        app.selectbox[0].select("Monto total").run()
        app.slider[0].set_value(72).run()
        app.slider[1].set_value(24).run()
        with patch("requests.get", return_value=response(200, {**PROJECTION, "target": "total_amount"})) as request:
            app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(request.call_args.kwargs["params"], {
            "target": "total_amount", "horizon": 72, "history_steps": 24,
        })
        self.assertEqual(app.metric[0].value, "8.00")

    def test_connection_and_invalid_json_show_actionable_errors(self):
        invalid_json = response(200, {})
        invalid_json._content = b"not-json"
        cases = (
            {"side_effect": requests.ConnectionError("API detenida")},
            {"return_value": invalid_json},
            {"return_value": response(500, {})},
        )
        for request_mock in cases:
            with self.subTest(case=request_mock):
                app = self.page()
                with patch("requests.get", **request_mock):
                    app.button[0].click().run()
                self.assertFalse(app.exception)
                self.assertEqual(len(app.error), 1)
                self.assertIn("Comprueba que esté iniciada", app.error[0].value)

    def test_changed_horizon_warns_that_projection_is_stale(self):
        app = self.page()
        with patch("requests.get", return_value=response(200, PROJECTION)):
            app.button[0].click().run()
        app.slider[0].set_value(72).run()
        self.assertFalse(app.exception)
        self.assertTrue(any("controles anteriores" in item.value for item in app.warning))


if __name__ == "__main__":
    unittest.main()
