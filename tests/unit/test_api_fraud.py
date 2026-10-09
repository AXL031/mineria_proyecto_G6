"""Contrato HTTP y carga real de un artefacto pequeño, independiente del modelo local."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import joblib
import pandas as pd
from fastapi.testclient import TestClient
from sklearn.dummy import DummyClassifier

from api.main import app
from api.routers.fraud import _load_scorer, get_scorer
from bankshield.features.fraud import MODEL_FEATURES, build_fraud_feature_frame


class FraudAPITests(unittest.TestCase):
    def setUp(self):
        parent = Path(__file__).resolve().parents[2] / "artifacts/reports"
        parent.mkdir(parents=True, exist_ok=True)
        work = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(work.cleanup)
        self.model = Path(work.name) / "model.joblib"
        self.record = {"type": "TRANSFER", "amount": 1000, "oldbalanceOrg": 500}
        features = build_fraud_feature_frame(pd.DataFrame([self.record] * 2))
        pipeline = DummyClassifier(strategy="prior").fit(features, [0, 1])
        joblib.dump({"artifact_version": 1, "pipeline": pipeline, "threshold": 0.5,
                     "feature_columns": list(MODEL_FEATURES),
                     "metadata": {"source": {"sha256": "fixture"}, "test": {"fixture": True}}}, self.model)
        self.addCleanup(_load_scorer.cache_clear)
        self.addCleanup(app.dependency_overrides.clear)
        self.env = patch.dict(os.environ, {"BANKSHIELD_FRAUD_MODEL": str(self.model)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client = TestClient(app)

    def test_scoring_equality_at_threshold_and_model_metrics(self):
        response = self.client.post("/api/fraud/predict", json=self.record)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["score"], result["threshold"])
        self.assertTrue(result["alert"])
        self.assertFalse(result["score_is_calibrated"])
        self.assertTrue(result["simulation_data"])
        evaluation = self.client.get("/api/fraud/model").json()
        self.assertEqual(result["model_id"], evaluation["model_id"])
        self.assertEqual(evaluation["test"], {"fixture": True})
        self.assertEqual(self.client.post("/api/fraud/predict", json={**self.record, "oldbalanceOrg": 0}).status_code, 200)

    def test_invalid_inputs(self):
        cases = [
            {**self.record, "type": "UNKNOWN"},
            {key: value for key, value in self.record.items() if key != "amount"},
            {**self.record, "amount": -1}, {**self.record, "oldbalanceOrg": -1},
            {**self.record, "amount": "nan"}, {**self.record, "amount": "Infinity"},
            {**self.record, "amount": True},
        ]
        for field in ("isFraud", "isFlaggedFraud", "newbalanceOrig", "nameOrig", "step"):
            cases.append({**self.record, field: 1})
        for record in cases:
            with self.subTest(record=record):
                self.assertEqual(self.client.post("/api/fraud/predict", json=record).status_code, 422)
        # JSON no estándar con número no finito: no debe llegar al scorer.
        response = self.client.post("/api/fraud/predict", content=json.dumps({**self.record, "amount": float("inf")}),
                                    headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 422)

    def test_missing_corrupt_and_incompatible_model_leave_health_available(self):
        for content in (None, b"invalid", {"artifact_version": 999}):
            _load_scorer.cache_clear()
            if content is None:
                self.model.unlink()
            elif isinstance(content, bytes):
                self.model.write_bytes(content)
            else:
                joblib.dump(content, self.model)
            with self.subTest(content=content), self.assertLogs("api.routers.fraud", level="ERROR"):
                response = self.client.post("/api/fraud/predict", json=self.record)
            self.assertEqual(response.status_code, 503)
            self.assertNotIn(str(self.model), response.text)
            self.assertEqual(self.client.get("/").status_code, 200)

    def test_unexpected_scoring_error_remains_server_error(self):
        class BrokenScorer:
            def score(self, records):
                raise RuntimeError("fixture failure")
        app.dependency_overrides[get_scorer] = lambda: BrokenScorer()
        client = TestClient(app, raise_server_exceptions=False)
        self.assertEqual(client.post("/api/fraud/predict", json=self.record).status_code, 500)


if __name__ == "__main__":
    unittest.main()
