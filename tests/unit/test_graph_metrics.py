"""Pruebas unitarias para construcción de grafos y métricas de red."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import networkx as nx
import pandas as pd

from bankshield.features.graph import (
    build_transaction_graph,
    compute_node_metrics,
    compute_graph_summary,
    extract_subgraph,
)


def _sample_edges() -> pd.DataFrame:
    """Crea un DataFrame de aristas de prueba."""
    return pd.DataFrame({
        "step": [1, 1, 2, 2, 3, 3],
        "type": ["PAYMENT", "TRANSFER", "TRANSFER", "CASH_OUT", "PAYMENT", "TRANSFER"],
        "amount": [1000.0, 2000.0, 5000.0, 3000.0, 500.0, 1500.0],
        "nameOrig": ["C100", "C100", "C100", "C300", "C400", "C500"],
        "nameDest": ["M200", "C300", "C400", "C500", "M200", "C100"],
        "isFraud": [0, 0, 1, 0, 0, 0],
    })


class TestBuildTransactionGraph(unittest.TestCase):
    """Pruebas de construcción del grafo."""

    def setUp(self):
        self.edges = _sample_edges()
        self.G = build_transaction_graph(self.edges)

    def test_graph_is_directed(self):
        """El grafo es dirigido."""
        self.assertIsInstance(self.G, nx.DiGraph)

    def test_node_count(self):
        """El número de nodos es correcto."""
        # C100, M200, C300, C400, C500
        self.assertEqual(self.G.number_of_nodes(), 5)

    def test_edge_count(self):
        """Las aristas se agregan por par único."""
        # C100→M200, C100→C300, C100→C400, C300→C500, C400→M200, C500→C100
        self.assertEqual(self.G.number_of_edges(), 6)

    def test_edge_attributes(self):
        """Las aristas tienen los atributos esperados."""
        edge = self.G[("C100")]["M200"]
        self.assertEqual(edge["weight"], 1)
        self.assertAlmostEqual(edge["total_amount"], 1000.0)
        self.assertEqual(edge["fraud_count"], 0)

    def test_fraud_edge(self):
        """Las aristas con fraude registran el conteo."""
        edge = self.G["C100"]["C400"]
        self.assertEqual(edge["fraud_count"], 1)

    def test_node_account_type(self):
        """Los nodos tienen tipo de cuenta correcto."""
        self.assertEqual(self.G.nodes["M200"]["account_type"], "comercio")
        self.assertEqual(self.G.nodes["C100"]["account_type"], "cliente")

    def test_empty_dataframe_raises(self):
        """Un DataFrame vacío lanza error."""
        empty = pd.DataFrame(columns=self.edges.columns)
        with self.assertRaises(ValueError):
            build_transaction_graph(empty)

    def test_missing_columns_raises(self):
        """Columnas faltantes lanzan error."""
        bad = self.edges.drop(columns=["nameOrig"])
        with self.assertRaises(ValueError):
            build_transaction_graph(bad)

    def test_multiple_transactions_same_pair(self):
        """Múltiples transacciones del mismo par se agregan."""
        edges = pd.DataFrame({
            "step": [1, 2],
            "type": ["PAYMENT", "PAYMENT"],
            "amount": [100.0, 200.0],
            "nameOrig": ["C1", "C1"],
            "nameDest": ["C2", "C2"],
            "isFraud": [0, 0],
        })
        G = build_transaction_graph(edges)
        self.assertEqual(G.number_of_edges(), 1)
        self.assertEqual(G["C1"]["C2"]["weight"], 2)
        self.assertAlmostEqual(G["C1"]["C2"]["total_amount"], 300.0)


class TestComputeNodeMetrics(unittest.TestCase):
    """Pruebas de métricas de nodo."""

    def setUp(self):
        self.G = build_transaction_graph(_sample_edges())
        self.metrics = compute_node_metrics(self.G)

    def test_all_nodes_have_metrics(self):
        """Cada nodo aparece en el DataFrame de métricas."""
        self.assertEqual(len(self.metrics), self.G.number_of_nodes())

    def test_metric_columns_exist(self):
        """Las columnas de métricas esperadas están presentes."""
        expected = {
            "account_type", "transactions_sent", "transactions_received",
            "weighted_in_degree", "weighted_out_degree",
            "in_degree_centrality", "out_degree_centrality",
            "pagerank", "unique_destinations", "unique_sources",
            "total_amount_sent", "total_amount_received", "net_flow",
        }
        self.assertTrue(expected.issubset(set(self.metrics.columns)))

    def test_pagerank_sums_to_one(self):
        """Los valores de PageRank suman aproximadamente 1."""
        total = self.metrics["pagerank"].sum()
        self.assertAlmostEqual(total, 1.0, places=4)

    def test_empty_graph_raises(self):
        """Un grafo vacío lanza error."""
        with self.assertRaises(ValueError):
            compute_node_metrics(nx.DiGraph())


class TestComputeGraphSummary(unittest.TestCase):
    """Pruebas del resumen global del grafo."""

    def setUp(self):
        self.G = build_transaction_graph(_sample_edges())
        self.summary = compute_graph_summary(self.G)

    def test_summary_keys(self):
        """El resumen contiene las claves esperadas."""
        expected_keys = {
            "nodos", "aristas_unicas", "densidad",
            "componentes_debiles", "nodos_mayor_componente",
            "grado_salida_medio", "grado_salida_maximo",
            "grado_entrada_medio", "grado_entrada_maximo",
            "nodos_por_tipo", "simulacion",
        }
        self.assertTrue(expected_keys.issubset(set(self.summary.keys())))

    def test_density_range(self):
        """La densidad está entre 0 y 1."""
        self.assertGreater(self.summary["densidad"], 0)
        self.assertLessEqual(self.summary["densidad"], 1)

    def test_simulation_flag(self):
        """El resumen marca los datos como simulados."""
        self.assertTrue(self.summary["simulacion"])


class TestExtractSubgraph(unittest.TestCase):
    """Pruebas de extracción de subgrafos."""

    def setUp(self):
        self.G = build_transaction_graph(_sample_edges())

    def test_subgraph_contains_center(self):
        """El subgrafo incluye la cuenta central."""
        sub = extract_subgraph(self.G, "C100", depth=1)
        self.assertIn("C100", sub.nodes())

    def test_center_is_marked(self):
        """La cuenta central está marcada como is_center."""
        sub = extract_subgraph(self.G, "C100", depth=1)
        self.assertTrue(sub.nodes["C100"].get("is_center", False))

    def test_subgraph_depth_1(self):
        """A profundidad 1, solo incluye vecinos directos."""
        sub = extract_subgraph(self.G, "C300", depth=1)
        # C300 tiene arista hacia C500 y desde C100
        self.assertIn("C500", sub.nodes())
        self.assertIn("C100", sub.nodes())

    def test_invalid_account_raises(self):
        """Una cuenta inexistente lanza error."""
        with self.assertRaises(ValueError):
            extract_subgraph(self.G, "INEXISTENTE", depth=1)

    def test_invalid_depth_raises(self):
        """Una profundidad menor a 1 lanza error."""
        with self.assertRaises(ValueError):
            extract_subgraph(self.G, "C100", depth=0)


if __name__ == "__main__":
    unittest.main()
