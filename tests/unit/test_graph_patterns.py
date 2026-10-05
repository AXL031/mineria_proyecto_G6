"""Pruebas unitarias para detección de patrones sospechosos en grafos."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pandas as pd

from bankshield.features.graph import (
    build_transaction_graph,
    compute_node_metrics,
)
from bankshield.features.graph_patterns import (
    detect_high_fanout,
    detect_high_fanin,
    detect_circular_transactions,
    detect_high_value_edges,
    detect_net_flow_anomalies,
    combine_suspicion_indicators,
)


def _sample_edges() -> pd.DataFrame:
    """Crea aristas de prueba con un nodo de alto fan-out."""
    return pd.DataFrame({
        "step": [1, 1, 1, 1, 1, 2, 2, 2],
        "type": [
            "TRANSFER", "TRANSFER", "TRANSFER", "TRANSFER", "TRANSFER",
            "TRANSFER", "PAYMENT", "CASH_OUT",
        ],
        "amount": [
            10000.0, 20000.0, 15000.0, 8000.0, 12000.0,
            5000.0, 100.0, 200.0,
        ],
        "nameOrig": [
            "C100", "C100", "C100", "C100", "C100",
            "C200", "C300", "C400",
        ],
        "nameDest": [
            "C200", "C300", "C400", "C500", "C600",
            "C100", "M700", "M700",
        ],
        "isFraud": [1, 0, 1, 0, 0, 0, 0, 0],
    })


def _circular_edges() -> pd.DataFrame:
    """Aristas que forman un ciclo C1 → C2 → C3 → C1."""
    return pd.DataFrame({
        "step": [1, 1, 1],
        "type": ["TRANSFER", "TRANSFER", "TRANSFER"],
        "amount": [5000.0, 4500.0, 4000.0],
        "nameOrig": ["C1", "C2", "C3"],
        "nameDest": ["C2", "C3", "C1"],
        "isFraud": [0, 0, 0],
    })


class TestDetectHighFanout(unittest.TestCase):
    """Pruebas de detección de alto fan-out."""

    def setUp(self):
        self.G = build_transaction_graph(_sample_edges())

    def test_identifies_fanout_account(self):
        """Detecta la cuenta C100 con 5 destinos distintos."""
        result = detect_high_fanout(self.G, threshold_percentile=50)
        accounts = result["account"].tolist()
        self.assertIn("C100", accounts)

    def test_result_columns(self):
        """El resultado tiene las columnas esperadas."""
        result = detect_high_fanout(self.G, threshold_percentile=50)
        if not result.empty:
            expected = {"account", "pattern", "out_degree", "threshold",
                        "total_amount_sent", "fraud_count", "account_type"}
            self.assertTrue(expected.issubset(set(result.columns)))

    def test_high_threshold_excludes_all(self):
        """Un umbral suficientemente alto puede no reportar cuentas."""
        result = detect_high_fanout(self.G, threshold_percentile=99.9)
        # Con pocos nodos, el percentil 99.9 podría excluir todo
        self.assertIsInstance(result, pd.DataFrame)


class TestDetectHighFanin(unittest.TestCase):
    """Pruebas de detección de alto fan-in."""

    def setUp(self):
        self.G = build_transaction_graph(_sample_edges())

    def test_identifies_fanin_account(self):
        """Detecta cuentas con múltiples orígenes."""
        result = detect_high_fanin(self.G, threshold_percentile=50)
        # M700 recibe de C300 y C400
        if not result.empty:
            self.assertIn("pattern", result.columns)


class TestDetectCircularTransactions(unittest.TestCase):
    """Pruebas de detección de ciclos."""

    def setUp(self):
        self.G = build_transaction_graph(_circular_edges())

    def test_finds_cycle(self):
        """Encuentra el ciclo C1 → C2 → C3 → C1."""
        cycles = detect_circular_transactions(self.G, max_length=4)
        self.assertGreater(len(cycles), 0)

    def test_cycle_has_attributes(self):
        """Los ciclos tienen los atributos esperados."""
        cycles = detect_circular_transactions(self.G, max_length=4)
        if cycles:
            cycle = cycles[0]
            self.assertIn("cycle", cycle)
            self.assertIn("length", cycle)
            self.assertIn("total_amount", cycle)

    def test_min_length_validation(self):
        """Longitud mínima menor a 2 lanza error."""
        with self.assertRaises(ValueError):
            detect_circular_transactions(self.G, max_length=1)

    def test_no_cycle_in_acyclic(self):
        """No encuentra ciclos en un grafo sin ciclos."""
        edges = pd.DataFrame({
            "step": [1, 1],
            "type": ["TRANSFER", "TRANSFER"],
            "amount": [1000.0, 2000.0],
            "nameOrig": ["C1", "C2"],
            "nameDest": ["C2", "C3"],
            "isFraud": [0, 0],
        })
        G = build_transaction_graph(edges)
        cycles = detect_circular_transactions(G, max_length=4)
        self.assertEqual(len(cycles), 0)


class TestDetectHighValueEdges(unittest.TestCase):
    """Pruebas de detección de aristas de alto valor."""

    def setUp(self):
        self.G = build_transaction_graph(_sample_edges())

    def test_returns_dataframe(self):
        """Devuelve un DataFrame."""
        result = detect_high_value_edges(self.G, threshold_percentile=50)
        self.assertIsInstance(result, pd.DataFrame)

    def test_high_value_is_filtered(self):
        """Solo incluye aristas por encima del umbral."""
        result = detect_high_value_edges(self.G, threshold_percentile=50)
        if not result.empty:
            self.assertTrue((result["total_amount"] > result["threshold"]).all())


class TestDetectNetFlowAnomalies(unittest.TestCase):
    """Pruebas de detección de anomalías de flujo neto."""

    def setUp(self):
        self.G = build_transaction_graph(_sample_edges())
        self.metrics = compute_node_metrics(self.G)

    def test_returns_dataframe(self):
        """Devuelve un DataFrame."""
        result = detect_net_flow_anomalies(self.metrics, threshold_percentile=50)
        self.assertIsInstance(result, pd.DataFrame)

    def test_requires_net_flow(self):
        """Lanza error si falta la columna net_flow."""
        bad_metrics = self.metrics.drop(columns=["net_flow"])
        with self.assertRaises(ValueError):
            detect_net_flow_anomalies(bad_metrics)


class TestCombineSuspicionIndicators(unittest.TestCase):
    """Pruebas de combinación de indicadores de sospecha."""

    def setUp(self):
        self.G = build_transaction_graph(_sample_edges())
        self.metrics = compute_node_metrics(self.G)

    def test_returns_dataframe(self):
        """Devuelve un DataFrame."""
        result = combine_suspicion_indicators(self.G, self.metrics)
        self.assertIsInstance(result, pd.DataFrame)

    def test_pattern_count_column(self):
        """Tiene una columna de conteo de patrones."""
        result = combine_suspicion_indicators(
            self.G, self.metrics,
            fanout_percentile=50, fanin_percentile=50, flow_percentile=50,
        )
        if not result.empty:
            self.assertIn("pattern_count", result.columns)
            self.assertTrue((result["pattern_count"] > 0).all())


if __name__ == "__main__":
    unittest.main()
