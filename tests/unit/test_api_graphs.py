"""Pruebas unitarias para los endpoints de la API de grafos."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from fastapi.testclient import TestClient
import pandas as pd

from api.main import app
from api.routers.graphs import _GRAPH_CACHE
from bankshield.features.graph import build_transaction_graph, compute_graph_summary
from bankshield.ingestion.graph_dataset import summarize_edges


def _mock_edges_df() -> pd.DataFrame:
    return pd.DataFrame({
        "step": [1, 1, 2, 2, 3],
        "type": ["PAYMENT", "TRANSFER", "TRANSFER", "CASH_OUT", "TRANSFER"],
        "amount": [1000.0, 2000.0, 5000.0, 3000.0, 1500.0],
        "nameOrig": ["C100", "C100", "C100", "C300", "C500"],
        "nameDest": ["M200", "C300", "C400", "C500", "C100"],
        "isFraud": [0, 0, 1, 0, 0],
    })


class TestGraphAPIEndpoints(unittest.TestCase):
    """Pruebas funcionales de los endpoints de grafos."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Inyectar mock en cache para aislar pruebas sin leer todo el CSV
        mock_edges = _mock_edges_df()
        mock_graph = build_transaction_graph(mock_edges)
        _GRAPH_CACHE["graph"] = mock_graph
        _GRAPH_CACHE["summary"] = compute_graph_summary(mock_graph)
        _GRAPH_CACHE["edges_summary"] = summarize_edges(mock_edges)

    def test_health_check(self):
        """Verifica que el endpoint de salud responda 200."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "online")

    def test_get_graph_summary(self):
        """Verifica el resumen global de la topología."""
        response = self.client.get("/api/graphs/summary")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["simulation_data"])
        self.assertIn("graph_summary", data)
        self.assertEqual(data["graph_summary"]["nodos"], 5)

    def test_get_existing_account(self):
        """Consulta una cuenta existente en el grafo mockeado."""
        response = self.client.get("/api/graphs/account/C100")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["data"]["account"], "C100")
        self.assertEqual(body["data"]["unique_destinations"], 3)

    def test_get_nonexistent_account_returns_404(self):
        """Una cuenta no encontrada responde con código 404."""
        response = self.client.get("/api/graphs/account/C_INEXISTENTE")
        self.assertEqual(response.status_code, 404)

    def test_get_account_subgraph(self):
        """Consulta el subgrafo ego alrededor de una cuenta."""
        response = self.client.get("/api/graphs/subgraph/C100?depth=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["center_account"], "C100")
        self.assertIn("nodes", data)
        self.assertIn("edges", data)

    def test_get_top_accounts(self):
        """Consulta el ranking de cuentas por métrica."""
        response = self.client.get("/api/graphs/top?metric=pagerank&top_n=3")
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertLessEqual(len(results), 3)
        self.assertGreater(len(results), 0)

    def test_get_top_invalid_metric_returns_400(self):
        """Una métrica inválida devuelve código 400."""
        response = self.client.get("/api/graphs/top?metric=metrica_falsa")
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
