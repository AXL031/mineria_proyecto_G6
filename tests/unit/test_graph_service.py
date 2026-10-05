"""Pruebas unitarias para el servicio de consulta de grafos."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pandas as pd

from bankshield.features.graph import build_transaction_graph
from bankshield.services.graph import (
    query_account,
    query_subgraph,
    query_top_accounts,
)


def _sample_edges() -> pd.DataFrame:
    """Crea aristas de prueba."""
    return pd.DataFrame({
        "step": [1, 1, 2, 2, 3, 3],
        "type": ["PAYMENT", "TRANSFER", "TRANSFER", "CASH_OUT", "PAYMENT", "TRANSFER"],
        "amount": [1000.0, 2000.0, 5000.0, 3000.0, 500.0, 1500.0],
        "nameOrig": ["C100", "C100", "C100", "C300", "C400", "C500"],
        "nameDest": ["M200", "C300", "C400", "C500", "M200", "C100"],
        "isFraud": [0, 0, 1, 0, 0, 0],
    })


class TestQueryAccount(unittest.TestCase):
    """Pruebas de consulta de cuentas individuales."""

    def setUp(self):
        self.G = build_transaction_graph(_sample_edges())

    def test_valid_account(self):
        """Consulta una cuenta existente."""
        result = query_account(self.G, "C100")
        self.assertEqual(result["account"], "C100")
        self.assertEqual(result["account_type"], "cliente")

    def test_outgoing_connections(self):
        """Incluye conexiones salientes."""
        result = query_account(self.G, "C100")
        self.assertEqual(result["unique_destinations"], 3)
        self.assertGreater(len(result["outgoing_connections"]), 0)

    def test_incoming_connections(self):
        """Incluye conexiones entrantes."""
        result = query_account(self.G, "C100")
        # C500 envía a C100
        self.assertEqual(result["unique_sources"], 1)

    def test_simulation_flag(self):
        """La respuesta indica que los datos son simulados."""
        result = query_account(self.G, "C100")
        self.assertTrue(result["simulation_data"])

    def test_invalid_account_raises(self):
        """Una cuenta inexistente lanza error."""
        with self.assertRaises(ValueError):
            query_account(self.G, "INEXISTENTE")

    def test_net_flow(self):
        """El flujo neto se calcula correctamente."""
        result = query_account(self.G, "C100")
        expected_net = result["total_amount_received"] - result["total_amount_sent"]
        self.assertAlmostEqual(result["net_flow"], expected_net)

    def test_merchant_account(self):
        """Consulta una cuenta de tipo comercio."""
        result = query_account(self.G, "M200")
        self.assertEqual(result["account_type"], "comercio")


class TestQuerySubgraph(unittest.TestCase):
    """Pruebas de consulta de subgrafos."""

    def setUp(self):
        self.G = build_transaction_graph(_sample_edges())

    def test_subgraph_structure(self):
        """El subgrafo tiene la estructura esperada."""
        result = query_subgraph(self.G, "C100", depth=1)
        self.assertIn("nodes", result)
        self.assertIn("edges", result)
        self.assertEqual(result["center_account"], "C100")
        self.assertGreater(result["node_count"], 0)

    def test_center_node_marked(self):
        """El nodo central está marcado en la respuesta."""
        result = query_subgraph(self.G, "C100", depth=1)
        center_nodes = [n for n in result["nodes"] if n.get("is_center")]
        self.assertEqual(len(center_nodes), 1)
        self.assertEqual(center_nodes[0]["id"], "C100")

    def test_simulation_flag(self):
        """La respuesta indica datos simulados."""
        result = query_subgraph(self.G, "C100", depth=1)
        self.assertTrue(result["simulation_data"])

    def test_edge_format(self):
        """Las aristas tienen source y target."""
        result = query_subgraph(self.G, "C100", depth=1)
        if result["edges"]:
            edge = result["edges"][0]
            self.assertIn("source", edge)
            self.assertIn("target", edge)
            self.assertIn("weight", edge)

    def test_invalid_account_raises(self):
        """Una cuenta inexistente lanza error."""
        with self.assertRaises(ValueError):
            query_subgraph(self.G, "INEXISTENTE")


class TestQueryTopAccounts(unittest.TestCase):
    """Pruebas de consulta de cuentas top."""

    def setUp(self):
        self.G = build_transaction_graph(_sample_edges())

    def test_default_metric(self):
        """Devuelve un ranking por PageRank por defecto."""
        result = query_top_accounts(self.G, metric="pagerank", top_n=3)
        self.assertLessEqual(len(result), 3)
        self.assertGreater(len(result), 0)

    def test_result_format(self):
        """Cada resultado tiene las claves esperadas."""
        result = query_top_accounts(self.G, metric="pagerank", top_n=3)
        for item in result:
            self.assertIn("account", item)
            self.assertIn("account_type", item)
            self.assertIn("pagerank", item)

    def test_invalid_metric_raises(self):
        """Una métrica inválida lanza error."""
        with self.assertRaises(ValueError):
            query_top_accounts(self.G, metric="invalid_metric")

    def test_different_metrics(self):
        """Funciona con distintas métricas válidas."""
        for metric in ("weighted_in_degree", "total_amount_sent", "unique_destinations"):
            result = query_top_accounts(self.G, metric=metric, top_n=2)
            self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main()
