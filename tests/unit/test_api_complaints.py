"""Contratos NLP sobre un artefacto sintético, independientes del modelo completo."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from api.main import app
from api.routers.complaints import _load_scorer, _load_summary


class ComplaintsAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        cls.root = Path(cls.work.name)
        texts = ["credit report incorrect account dispute", "credit bureau wrong report information",
                 "mortgage loan payment home foreclosure", "mortgage lender home payment problems",
                 "bank checking account overdraft deposit", "bank account checking fees deposit"]
        labels = ["Credit reporting"] * 2 + ["Mortgage"] * 2 + ["Bank account"] * 2
        pipeline = Pipeline([("tfidf", TfidfVectorizer()), ("model", LogisticRegression())]).fit(texts, labels)
        joblib.dump({"artifact_version": 1, "pipeline": pipeline, "classes": list(pipeline.classes_),
                     "metadata": {"config": {"min_words": 5}, "training_input": {"sha256": "fixture"}, "test": {}}}, cls.root / "model.joblib")
        pd.DataFrame({"date_received": pd.to_datetime(["2015-01-02", "2015-02-03"]),
                      "product": ["Mortgage", "Credit reporting"], "has_narrative": [False, True]}).to_parquet(cls.root / "silver.parquet")
        (cls.root / "examples.json").write_text(json.dumps({"model_input_sha256": "fixture", "test_rows": 10,
            "errors": 2, "correct_examples": [], "high_confidence_errors": []}), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def setUp(self):
        _load_scorer.cache_clear()
        _load_summary.cache_clear()
        self.addCleanup(_load_scorer.cache_clear)
        self.addCleanup(_load_summary.cache_clear)
        env = patch.dict(os.environ, {"BANKSHIELD_COMPLAINTS_MODEL": str(self.root / "model.joblib"),
            "BANKSHIELD_COMPLAINTS_SILVER": str(self.root / "silver.parquet"),
            "BANKSHIELD_COMPLAINTS_EXAMPLES": str(self.root / "examples.json")})
        env.start()
        self.addCleanup(env.stop)
        self.client = TestClient(app)

    def test_prediction_and_metrics_use_the_same_artifact(self):
        result = self.client.post("/api/complaints/predict", json={"narrative": "My credit report contains incorrect account information"})
        self.assertEqual(result.status_code, 200)
        body = result.json()
        self.assertEqual(body["product"], "Credit reporting")
        self.assertFalse(body["scores_calibrated"])
        self.assertEqual(len(body["alternatives"]), 3)
        self.assertEqual(body["model_id"], self.client.get("/api/complaints/model").json()["model_id"])

    def test_empty_short_unrecognized_and_extra_inputs_are_rejected(self):
        for payload in ({"narrative": ""}, {"narrative": "short text here"},
                        {"narrative": "zzzz aaaa qqqq vvvv kkkk"},
                        {"narrative": "My credit report contains incorrect information", "product": "Mortgage"}):
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post("/api/complaints/predict", json=payload).status_code, 422)

    def test_missing_model_preserves_health(self):
        with patch.dict(os.environ, {"BANKSHIELD_COMPLAINTS_MODEL": str(self.root / "absent.joblib")}):
            self.assertEqual(self.client.get("/api/complaints/model").status_code, 503)
            self.assertEqual(self.client.get("/").status_code, 200)

    def test_summary_includes_all_records_and_separate_narrative_coverage(self):
        response = self.client.get("/api/complaints/summary")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total_complaints"], 2)
        self.assertEqual(body["with_narrative"], 1)
        self.assertEqual(sum(row["complaints"] for row in body["monthly"]), 2)

    def test_examples_require_matching_training_input(self):
        self.assertEqual(self.client.get("/api/complaints/examples").status_code, 200)
        wrong = self.root / "wrong-examples.json"
        wrong.write_text('{"model_input_sha256": "other"}', encoding="utf-8")
        with patch.dict(os.environ, {"BANKSHIELD_COMPLAINTS_EXAMPLES": str(wrong)}):
            self.assertEqual(self.client.get("/api/complaints/examples").status_code, 503)

    def test_invalid_or_missing_silver_returns_503(self):
        with patch.dict(os.environ, {"BANKSHIELD_COMPLAINTS_SILVER": str(self.root / "absent.parquet")}):
            self.assertEqual(self.client.get("/api/complaints/summary").status_code, 503)
