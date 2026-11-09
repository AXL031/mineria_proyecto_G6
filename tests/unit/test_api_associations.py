import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from analytics_fixtures import association_config
from test_associations import MemoryDataset, small_frame
from api.main import app
from bankshield.analytics_contract import write_json_atomic
from bankshield.models.associations import mine


class AssociationAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.tmp.name) / "rules.json"
        cls.report = mine(MemoryDataset(small_frame()), association_config())
        write_json_atomic(cls.path, cls.report)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.client = TestClient(app)
        self.env = patch.dict(os.environ, BANKSHIELD_ASSOCIATIONS_REPORT=str(self.path))
        self.env.start()
        self.addCleanup(self.env.stop)
        write_json_atomic(self.path, self.report)

    def test_pagination_and_identity(self):
        first = self.client.get("/api/fraud/associations?limit=1").json()
        second = self.client.get("/api/fraud/associations?limit=1&offset=1").json()
        self.assertEqual(first["analysis_id"], second["analysis_id"])
        self.assertNotEqual(first["rules"][0]["id"], second["rules"][0]["id"])
        self.assertEqual(self.client.get("/api/fraud/associations?offset=9999").json()["rules"], [])

    def test_invalid_parameters(self):
        for query in ("partition=other", "limit=0", "limit=101", "offset=-1"):
            self.assertEqual(self.client.get("/api/fraud/associations?" + query).status_code, 422)

    def test_missing_incompatible_and_altered_report(self):
        for payload in ({**self.report, "schema_version": 99}, {**self.report, "analysis_id": "wrong"}):
            write_json_atomic(self.path, payload)
            self.assertEqual(self.client.get("/api/fraud/associations").status_code, 503)
        self.path.unlink()
        self.assertEqual(self.client.get("/api/fraud/associations").status_code, 503)
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_empty_selection_returns_200(self):
        report = mine(MemoryDataset(small_frame()), {**association_config(), "min_antecedent_count": 999})
        write_json_atomic(self.path, report)
        response = self.client.get("/api/fraud/associations")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["rules"], [])
