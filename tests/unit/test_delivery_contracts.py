import unittest
from pathlib import Path
import json
import tempfile
from unittest.mock import patch
import requests

from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from api.main import app


class DeliveryContractTests(unittest.TestCase):
    def test_registered_modules_capabilities_and_openapi_agree(self):
        client = TestClient(app)
        root = client.get("/").json()
        self.assertEqual(set(root["modules"]), {"fraud", "credit", "graphs", "forecast", "segments", "complaints", "regression"})
        self.assertEqual(set(root["capabilities"]), {"association_mining", "graph_comparison", "numeric_regression"})
        paths = client.get("/openapi.json").json()["paths"]
        for path in ("/api/regression/model", "/api/regression/predict", "/api/regression/examples",
                     "/api/fraud/associations", "/api/fraud/patterns", "/api/graphs/evaluation"):
            self.assertIn(path, paths)

    def test_homepage_lists_regression_and_associations(self):
        page = AppTest.from_file(str(Path(__file__).resolve().parents[2] / "dashboard/app.py"), default_timeout=30).run()
        self.assertFalse(page.exception)
        content = " ".join(item.value for item in page.markdown)
        self.assertIn("Regresión", content)
        self.assertIn("asociaciones descubiertas", content)

    def test_verifier_failure_preserves_profile_optional_status_and_error(self):
        from scripts.verify_demo import verify
        response = requests.Response()
        response.status_code = 503
        response._content = b'{"detail":"missing"}'
        with tempfile.TemporaryDirectory() as tmp, patch("requests.get", return_value=response):
            output = Path(tmp) / "verification.json"
            with self.assertRaises(RuntimeError):
                verify("http://127.0.0.1:9999", output, pages=False)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["profile"], "full")
            self.assertEqual(report["optional"]["model_performance_monitoring"], "skipped_optional")
            self.assertIn("error", report)
