"""Pruebas del servicio y los endpoints HTTP de segmentos.

Usan artefactos sintéticos en un directorio temporal para no depender del
Parquet completo generado localmente (excluido de Git).
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pandas as pd
from fastapi.testclient import TestClient

from api.main import app
from bankshield.services import segments as segments_service


def _write_artifacts(directory: Path) -> tuple[Path, Path]:
    parquet = directory / "account_segments.parquet"
    report = directory / "segments.json"
    pd.DataFrame(
        {
            "account": ["D0", "D1", "D2"],
            "segment": [0, 0, 1],
            "n_received": [30, 25, 12],
            "fraud_rate_received": [0.0, 0.04, 0.0],
        }
    ).to_parquet(parquet, index=False)
    report.write_text(
        json.dumps(
            {
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
        ),
        encoding="utf-8",
    )
    return parquet, report


class SegmentsServiceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.parquet, self.report = _write_artifacts(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_load_and_summary(self):
        summary = segments_service.get_summary(self.report)
        self.assertEqual(summary["total_accounts"], 3)
        self.assertEqual(summary["metrics"]["chosen_k"], 2)
        self.assertEqual(len(summary["profiles"]), 2)

    def test_accounts_by_segment_with_pagination(self):
        frame = segments_service.get_accounts_by_segment(
            0, limit=1, parquet_path=self.parquet
        )
        self.assertEqual(len(frame), 1)
        self.assertEqual(frame.iloc[0]["account"], "D0")

    def test_accounts_are_sorted_by_activity_and_offset(self):
        frame = segments_service.get_accounts_by_segment(0, parquet_path=self.parquet)
        self.assertEqual(frame["account"].tolist(), ["D0", "D1"])
        second = segments_service.get_accounts_by_segment(
            0, limit=1, offset=1, parquet_path=self.parquet
        )
        self.assertEqual(second["account"].tolist(), ["D1"])

    def test_get_account(self):
        record = segments_service.get_account(1, "D2", parquet_path=self.parquet)
        self.assertEqual(record["account"], "D2")
        self.assertEqual(record["segment"], 1)

    def test_unknown_segment_raises_keyerror(self):
        with self.assertRaises(KeyError):
            segments_service.get_accounts_by_segment(9, parquet_path=self.parquet)

    def test_missing_artifact_raises(self):
        with self.assertRaises(segments_service.SegmentsArtifactError):
            segments_service.load_segments(Path(self._tmp.name) / "nope.parquet")


class SegmentsApiTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.parquet, self.report = _write_artifacts(Path(self._tmp.name))
        self._saved = {
            key: os.environ.get(key)
            for key in ("BANKSHIELD_SEGMENTS_PARQUET", "BANKSHIELD_SEGMENTS_REPORT")
        }
        os.environ["BANKSHIELD_SEGMENTS_PARQUET"] = str(self.parquet)
        os.environ["BANKSHIELD_SEGMENTS_REPORT"] = str(self.report)
        self.client = TestClient(app)

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._tmp.cleanup()

    def test_health_lists_segments(self):
        body = self.client.get("/").json()
        self.assertIn("segments", body["modules"])

    def test_summary_endpoint(self):
        response = self.client.get("/api/segments/summary")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_accounts"], 3)

    def test_accounts_endpoint_and_pagination(self):
        response = self.client.get("/api/segments/0/accounts?limit=1")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["segment"], 0)
        self.assertEqual(body["count"], 1)

    def test_unknown_segment_returns_404(self):
        response = self.client.get("/api/segments/9/accounts")
        self.assertEqual(response.status_code, 404)

    def test_unknown_account_returns_404(self):
        response = self.client.get("/api/segments/0/account/INEXISTENTE")
        self.assertEqual(response.status_code, 404)

    def test_missing_artifact_returns_503(self):
        os.environ["BANKSHIELD_SEGMENTS_PARQUET"] = str(
            Path(self._tmp.name) / "nope.parquet"
        )
        response = self.client.get("/api/segments/0/accounts")
        self.assertEqual(response.status_code, 503)

    def test_invalid_limit_returns_422(self):
        response = self.client.get("/api/segments/0/accounts?limit=0")
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
