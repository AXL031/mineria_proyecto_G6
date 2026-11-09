import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from analytics_fixtures import dataset_fixture, regression_config
from api.main import app
from api.routers.regression import _load
from bankshield.models.regression import train


class RegressionAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.tmp.name)
        dataset = dataset_fixture(cls.directory / "data")
        train(dataset, regression_config(), cls.directory / "model")

    @classmethod
    def tearDownClass(cls):
        _load.cache_clear()
        cls.tmp.cleanup()

    def setUp(self):
        _load.cache_clear()
        self.client = TestClient(app)
        env = patch.dict(os.environ, BANKSHIELD_REGRESSION_MODEL=str(self.directory / "model/model.joblib"))
        env.start()
        self.addCleanup(env.stop)

    def test_prediction_and_metadata_share_identity(self):
        prediction = self.client.post("/api/regression/predict", json={"type": "TRANSFER", "oldbalanceOrg": 0.})
        self.assertEqual(prediction.status_code, 200)
        self.assertGreaterEqual(prediction.json()["prediction"], 0)
        self.assertEqual(prediction.json()["model_id"], self.client.get("/api/regression/model").json()["model_id"])

    def test_invalid_inputs_are_422(self):
        for payload in ({"type": "INVALID", "oldbalanceOrg": 1}, {"type": "TRANSFER", "oldbalanceOrg": -1},
                        {"type": "TRANSFER", "oldbalanceOrg": True}, {"type": "TRANSFER", "oldbalanceOrg": "100"},
                        {"type": "TRANSFER", "oldbalanceOrg": 1, "amount": 10}):
            self.assertEqual(self.client.post("/api/regression/predict", json=payload).status_code, 422)
        for value in ("NaN", "Infinity", "-Infinity"):
            response = self.client.post("/api/regression/predict", content='{"type":"TRANSFER","oldbalanceOrg":' + value + '}', headers={"Content-Type": "application/json"})
            self.assertEqual(response.status_code, 422)

    def test_examples_and_invalid_pagination(self):
        result = self.client.get("/api/regression/examples?limit=1").json()
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual(result["model_id"], result["rows"][0]["model_id"])
        self.assertEqual(self.client.get("/api/regression/examples?offset=10000").json()["rows"], [])
        for query in ("limit=0", "limit=101", "offset=-1"):
            self.assertEqual(self.client.get("/api/regression/examples?" + query).status_code, 422)

    def test_missing_model_does_not_prevent_startup(self):
        with patch.dict(os.environ, BANKSHIELD_REGRESSION_MODEL=str(self.directory / "absent.joblib")):
            self.assertEqual(self.client.get("/api/regression/model").status_code, 503)
            self.assertEqual(self.client.get("/").status_code, 200)

    def test_replaced_model_with_stale_metrics_is_503(self):
        import shutil
        replacement = self.directory / "replacement"
        replacement.mkdir(exist_ok=True)
        for name in ("model.joblib", "metrics.json"):
            shutil.copy2(self.directory / "model" / name, replacement / name)
        with (replacement / "model.joblib").open("ab") as handle:
            handle.write(b"changed-model")
        with patch.dict(os.environ, BANKSHIELD_REGRESSION_MODEL=str(replacement / "model.joblib")):
            self.assertEqual(self.client.get("/api/regression/model").status_code, 503)

    def test_changed_examples_are_503_and_prediction_remains_available(self):
        path = self.directory / "model/examples.json"
        original = path.read_bytes()
        try:
            path.write_bytes(original + b" ")
            self.assertEqual(self.client.get("/api/regression/examples").status_code, 503)
            self.assertEqual(self.client.get("/api/regression/model").status_code, 200)
        finally:
            path.write_bytes(original)
