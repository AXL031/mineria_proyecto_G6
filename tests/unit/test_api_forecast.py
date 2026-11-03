import sys
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from api.routers.forecast import get_series, monitoring, projection, router


class ForecastAPITests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router, prefix="/api")
        self.series = pd.DataFrame({
            "step": range(1, 201),
            "transaction_count": range(1, 201),
            "total_amount": [float(value * 10) for value in range(1, 201)],
        })
        self.app.dependency_overrides[get_series] = lambda: self.series

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

    def test_http_targets_horizon_limits_and_validation_errors(self):
        with TestClient(self.app) as client:
            for target in ("transaction_count", "total_amount"):
                for horizon in (1, 168):
                    with self.subTest(target=target, horizon=horizon):
                        response = client.get("/api/forecast/projection", params={
                            "target": target, "horizon": horizon, "history_steps": 24,
                        })
                        self.assertEqual(response.status_code, 200)
                        body = response.json()
                        self.assertEqual(len(body["forecast"]), horizon)
                        self.assertEqual(body["forecast"][-1]["step"], 200 + horizon)
            for params in ({"target": "other"}, {"horizon": 0}, {"horizon": 169},
                           {"horizon": "abc"}, {"history_steps": 23}, {"history_steps": 719}):
                with self.subTest(params=params):
                    self.assertEqual(client.get("/api/forecast/projection", params=params).status_code, 422)

    def test_http_missing_artifacts_return_503(self):
        self.app.dependency_overrides.clear()
        with tempfile.TemporaryDirectory() as directory:
            missing = str(Path(directory) / "missing")
            with patch.dict(os.environ, {
                "BANKSHIELD_FORECAST_GOLD": missing,
                "BANKSHIELD_FORECAST_MONITORING": missing,
            }), TestClient(self.app) as client:
                for endpoint in ("projection", "monitoring"):
                    with self.subTest(endpoint=endpoint):
                        response = client.get("/api/forecast/" + endpoint)
                        self.assertEqual(response.status_code, 503)
                        self.assertIn("no disponible", response.json()["detail"])

    def test_http_incompatible_monitoring_returns_503(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "monitoring.json"
            report.write_text('{"status": "unknown"}', encoding="utf-8")
            with patch.dict(os.environ, {"BANKSHIELD_FORECAST_MONITORING": str(report)}), TestClient(self.app) as client:
                response = client.get("/api/forecast/monitoring")
                self.assertEqual(response.status_code, 503)
                self.assertIn("no es compatible", response.json()["detail"])

    def test_http_invalid_gold_returns_contract_error(self):
        self.series.loc[0, "transaction_count"] = -1
        with TestClient(self.app) as client:
            response = client.get("/api/forecast/projection")
        self.assertEqual(response.status_code, 500)
        self.assertIn("no cumple el contrato", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
