"""Contrato HTTP de regresión con un artefacto entrenado sobre D1 sintético."""

import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.main import app as central_app
from api.routers.regression import _load, router
from bankshield.models.regression import RegressionConfig, train_regression
from tests.unit.test_regression_training import synthetic_d1

# Mismo manejador 422 que la API central, que no devuelve los valores de entrada.
app = FastAPI(exception_handlers=central_app.exception_handlers)
app.include_router(router, prefix="/api")
VALID = {"type": "TRANSFER", "oldbalanceOrg": 500.0}


class RegressionAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        cls.root = Path(cls.work.name)
        path, report, _ = synthetic_d1(cls.root)
        train_regression(RegressionConfig(max_train_rows=1000, examples_rows=150), path, report, cls.root / "model")
        cls.model = cls.root / "model" / "model.joblib"

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def setUp(self):
        _load.cache_clear()
        self.addCleanup(_load.cache_clear)
        env = patch.dict(os.environ, {"BANKSHIELD_REGRESSION_MODEL": str(self.model)})
        env.start()
        self.addCleanup(env.stop)
        self.client = TestClient(app)

    def test_predict_returns_contract(self):
        response = self.client.post("/api/regression/predict", json=VALID)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["target"], "amount")
        self.assertGreaterEqual(body["prediction"], 0)
        self.assertTrue(body["simulation_data"])
        self.assertEqual(body["limitations"], ["Estimación académica; no constituye una alerta de fraude."])
        zero = self.client.post("/api/regression/predict", json={**VALID, "oldbalanceOrg": 0})
        self.assertEqual(zero.status_code, 200)

    def test_invalid_inputs_return_422(self):
        cases = [{"type": "NOPE", "oldbalanceOrg": 1.0}, {"type": "DEBIT", "oldbalanceOrg": -1.0},
                 {"type": "DEBIT", "oldbalanceOrg": True}, {"type": "DEBIT", "oldbalanceOrg": "5"},
                 {**VALID, "step": 3}, {"type": "DEBIT"}, {"oldbalanceOrg": 1.0}]
        for body in cases:
            with self.subTest(body=body):
                self.assertEqual(self.client.post("/api/regression/predict", json=body).status_code, 422)
        for raw in ('{"type": "DEBIT", "oldbalanceOrg": NaN}', '{"type": "DEBIT", "oldbalanceOrg": Infinity}'):
            response = self.client.post("/api/regression/predict", content=raw,
                                        headers={"content-type": "application/json"})
            self.assertEqual(response.status_code, 422)

    def test_model_endpoint_shares_identity(self):
        body = self.client.get("/api/regression/model").json()
        self.assertEqual(body["model_id"], self.client.post("/api/regression/predict", json=VALID).json()["model_id"])
        self.assertEqual(body["input_fields"], ["type", "oldbalanceOrg"])
        self.assertIn("comparison", body)

    def test_examples_pagination(self):
        page = self.client.get("/api/regression/examples?limit=20&offset=0").json()
        self.assertEqual(len(page["rows"]), 20)
        self.assertEqual(page["total"], 150)
        beyond = self.client.get("/api/regression/examples?limit=20&offset=1000")
        self.assertEqual(beyond.status_code, 200)
        self.assertEqual(beyond.json()["rows"], [])
        for query in ("limit=0", "limit=101", "offset=-1"):
            self.assertEqual(self.client.get(f"/api/regression/examples?{query}").status_code, 422)

    def test_missing_model_gives_503(self):
        with patch.dict(os.environ, {"BANKSHIELD_REGRESSION_MODEL": str(self.root / "missing.joblib")}):
            for call in (lambda: self.client.post("/api/regression/predict", json=VALID),
                         lambda: self.client.get("/api/regression/model"),
                         lambda: self.client.get("/api/regression/examples")):
                self.assertEqual(call().status_code, 503)

    def test_changed_model_breaks_identity_with_old_metrics_and_examples(self):
        copy = self.root / "other"
        shutil.copytree(self.root / "model", copy, dirs_exist_ok=True)
        with open(copy / "model.joblib", "ab") as handle:
            handle.write(b"\0")
        with patch.dict(os.environ, {"BANKSHIELD_REGRESSION_MODEL": str(copy / "model.joblib")}):
            self.assertEqual(self.client.post("/api/regression/predict", json=VALID).status_code, 503)
        stale = self.root / "stale"
        shutil.copytree(self.root / "model", stale, dirs_exist_ok=True)
        examples = json.loads((stale / "examples.json").read_text(encoding="utf-8"))
        examples["model_id"] = "0" * 64
        (stale / "examples.json").write_text(json.dumps(examples), encoding="utf-8")
        with patch.dict(os.environ, {"BANKSHIELD_REGRESSION_MODEL": str(stale / "model.joblib")}):
            self.assertEqual(self.client.get("/api/regression/examples").status_code, 503)


if __name__ == "__main__":
    unittest.main()
