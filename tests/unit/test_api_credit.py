"""Contrato HTTP de crédito con un artefacto entrenado sobre datos sintéticos."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app
from api.routers.credit import _load_scorer
from bankshield.models.credit import CreditConfig, train_credit
from bankshield.transforms.silver_credit import build_silver_credit
from tests.unit.test_credit_pipeline import synthetic_bronze

APPLICATION = {"person_age": 30, "person_income": 50000, "person_home_ownership": "RENT",
               "person_emp_length": 4, "loan_intent": "PERSONAL", "loan_amnt": 10000,
               "cb_person_default_on_file": "N", "cb_person_cred_hist_length": 5}


class CreditAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        root = Path(cls.work.name)
        synthetic_bronze().to_csv(root / "c.csv", index=False)
        build_silver_credit(root / "c.csv", root / "c.parquet", root / "q.json")
        train_credit(root / "c.parquet", root / "q.json", CreditConfig(max_iter=20), root / "model")
        cls.model = root / "model" / "model.joblib"

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def setUp(self):
        _load_scorer.cache_clear()
        self.addCleanup(_load_scorer.cache_clear)
        env = patch.dict(os.environ, {"BANKSHIELD_CREDIT_MODEL": str(self.model)})
        env.start()
        self.addCleanup(env.stop)
        self.client = TestClient(app)

    def test_predict_returns_calibrated_probability_factors_and_no_credit_limit(self):
        response = self.client.post("/api/credit/predict", json=APPLICATION)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(0 <= body["default_probability"] <= 1)
        self.assertEqual(body["high_risk"], body["default_probability"] >= body["threshold"])
        self.assertLessEqual(len(body["factors"]), 5)
        self.assertFalse(body["explanation_is_causal"])
        self.assertFalse(body["label_semantics_confirmed"])
        self.assertIsNone(body["credit_limit_recommended"])

    def test_missing_employment_length_is_accepted(self):
        response = self.client.post("/api/credit/predict", json={**APPLICATION, "person_emp_length": None})
        self.assertEqual(response.status_code, 200)

    def test_invalid_inputs_return_422_without_echoing_values(self):
        cases = [{"person_age": 17}, {"person_income": 0}, {"loan_amnt": -5}, {"person_age": 20, "person_emp_length": 30},
                 {"loan_intent": "CRYPTO"}, {"loan_grade": "A"}, {"loan_int_rate": 9.5}, {"person_income": "55000"},
                 {"person_income": float("nan")}]
        for change in cases:
            with self.subTest(change=change):
                payload = {**APPLICATION, **change}
                response = self.client.post("/api/credit/predict", content=__import__("json").dumps(payload),
                                            headers={"content-type": "application/json"})
                self.assertEqual(response.status_code, 422)
                self.assertTrue(all("input" not in item for item in response.json()["detail"]))

    def test_model_endpoint_exposes_embedded_metrics(self):
        body = self.client.get("/api/credit/model").json()
        self.assertIn("hist_gradient_boosting:application:calibrated", body["test"])
        self.assertEqual(body["main_model"]["feature_set"], "application")
        self.assertIn("label_semantics_unconfirmed", body["limitations"])

    def test_missing_model_returns_503(self):
        with patch.dict(os.environ, {"BANKSHIELD_CREDIT_MODEL": str(Path(self.work.name) / "nope.joblib")}):
            self.assertEqual(self.client.post("/api/credit/predict", json=APPLICATION).status_code, 503)
            self.assertEqual(self.client.get("/api/credit/model").status_code, 503)

    def test_health_lists_credit_module(self):
        self.assertIn("credit", self.client.get("/").json()["modules"])


if __name__ == "__main__":
    unittest.main()
