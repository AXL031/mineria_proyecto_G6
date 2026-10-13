"""Interacciones de la página de segmentos: contrato API y errores de conexión."""

import json
from pathlib import Path
import unittest
from unittest.mock import patch

import requests
from streamlit.testing.v1 import AppTest

PAGE = Path(__file__).resolve().parents[2] / "dashboard/pages/06_segmentos.py"


def response(status, payload):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(payload).encode("utf-8")
    return result


def summary_payload():
    return {
        "schema_version": 1,
        "source": "synthetic",
        "min_transactions": 10,
        "total_accounts": 3,
        "metrics": {
            "chosen_k": 2,
            "silhouette": 0.23,
            "silhouette_by_k": {"2": 0.23, "3": 0.18},
            "mean_stability_ari": 0.7,
            "stability_ari": [0.7, 0.6, 0.8],
        },
        "profiles": [
            {"segment": 0, "size": 2, "n_received": 27.5},
            {"segment": 1, "size": 1, "n_received": 12.0},
        ],
        "baseline_profiles": [
            {"segment": 0, "size": 2, "mean_n_received": 14.0},
            {"segment": 1, "size": 1, "mean_n_received": 25.0},
        ],
    }


def accounts_payload():
    return {
        "segment": 0,
        "count": 2,
        "accounts": [
            {"account": "D0", "segment": 0, "n_received": 30},
            {"account": "D1", "segment": 0, "n_received": 25},
        ],
    }


class SegmentsDashboardTests(unittest.TestCase):
    def _fake_get(self, url, timeout=20):
        if url.endswith("/summary"):
            return response(200, summary_payload())
        if "/accounts" in url:
            return response(200, accounts_payload())
        return response(404, {"detail": "no"})

    def test_summary_and_accounts_render(self):
        with patch("requests.get", side_effect=self._fake_get):
            app = AppTest.from_file(str(PAGE)).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.metric), 4)
        self.assertEqual([metric.value for metric in app.metric][:2], ["3", "2"])

    def test_missing_artifact_shows_error(self):
        with patch("requests.get", return_value=response(503, {"detail": "missing"})):
            app = AppTest.from_file(str(PAGE)).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.error), 1)

    def test_offline_api_shows_error(self):
        with patch("requests.get", side_effect=requests.ConnectionError("offline")):
            app = AppTest.from_file(str(PAGE)).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.error), 1)


if __name__ == "__main__":
    unittest.main()
