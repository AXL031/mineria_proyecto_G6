"""Pruebas unitarias para la ingesta de datos de grafos."""

import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pandas as pd

from bankshield.ingestion.graph_dataset import (
    read_transaction_edges,
    summarize_edges,
)


def _create_test_csv(rows, path):
    """Crea un CSV de prueba con cabecera PaySim."""
    header = [
        "step", "type", "amount", "nameOrig", "oldbalanceOrg",
        "newbalanceOrig", "nameDest", "oldbalanceDest",
        "newbalanceDest", "isFraud", "isFlaggedFraud",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


SAMPLE_ROWS = [
    [1, "PAYMENT", "1000.00", "C100", "5000.0", "4000.0", "M200", "0.0", "1000.0", 0, 0],
    [1, "TRANSFER", "2000.00", "C100", "4000.0", "2000.0", "C300", "100.0", "2100.0", 0, 0],
    [2, "TRANSFER", "5000.00", "C100", "2000.0", "0.0", "C400", "0.0", "5000.0", 1, 0],
    [2, "CASH_OUT", "3000.00", "C300", "2100.0", "0.0", "C500", "0.0", "3000.0", 0, 0],
    [3, "PAYMENT", "500.00", "C400", "5000.0", "4500.0", "M200", "1000.0", "1500.0", 0, 0],
    [3, "TRANSFER", "1500.00", "C500", "3000.0", "1500.0", "C100", "0.0", "1500.0", 0, 0],
]


class TestReadTransactionEdges(unittest.TestCase):
    """Pruebas de lectura de aristas transaccionales."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.csv_path = Path(self.tmpdir) / "test_transactions.csv"
        _create_test_csv(SAMPLE_ROWS, self.csv_path)

    def test_read_all_rows(self):
        """Lee todas las filas del CSV de prueba."""
        edges = read_transaction_edges(self.csv_path)
        self.assertEqual(len(edges), 6)
        self.assertIn("nameOrig", edges.columns)
        self.assertIn("nameDest", edges.columns)
        self.assertIn("amount", edges.columns)

    def test_read_with_limit(self):
        """Respeta el límite de filas."""
        edges = read_transaction_edges(self.csv_path, limit=3)
        self.assertEqual(len(edges), 3)

    def test_columns_are_correct(self):
        """Las columnas devueltas son las de arista, sin saldos."""
        edges = read_transaction_edges(self.csv_path)
        expected = {"step", "type", "amount", "nameOrig", "nameDest", "isFraud"}
        self.assertEqual(set(edges.columns), expected)

    def test_no_balance_columns(self):
        """No incluye columnas de saldos posteriores."""
        edges = read_transaction_edges(self.csv_path)
        for col in ("oldbalanceOrg", "newbalanceOrig", "oldbalanceDest",
                     "newbalanceDest", "isFlaggedFraud"):
            self.assertNotIn(col, edges.columns)

    def test_invalid_limit_raises(self):
        """Un límite no positivo lanza error."""
        with self.assertRaises(ValueError):
            read_transaction_edges(self.csv_path, limit=0)

    def test_lfs_reference_raises(self):
        """Detecta una referencia Git LFS en lugar del CSV completo."""
        lfs_path = Path(self.tmpdir) / "lfs_ref.csv"
        lfs_path.write_text(
            "version https://git-lfs.github.com/spec/v1\n"
            "oid sha256:abc123\nsize 12345\n",
            encoding="utf-8",
        )
        with self.assertRaises(ValueError, msg="referencia Git LFS"):
            read_transaction_edges(lfs_path)

    def test_fraud_values_are_binary(self):
        """Los valores de isFraud son 0 o 1."""
        edges = read_transaction_edges(self.csv_path)
        self.assertTrue(edges["isFraud"].isin([0, 1]).all())


class TestSummarizeEdges(unittest.TestCase):
    """Pruebas del resumen estadístico de aristas."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.csv_path = Path(self.tmpdir) / "test_transactions.csv"
        _create_test_csv(SAMPLE_ROWS, self.csv_path)
        self.edges = read_transaction_edges(self.csv_path)

    def test_total_edges(self):
        """El total de aristas coincide con las filas leídas."""
        summary = summarize_edges(self.edges)
        self.assertEqual(summary["total_aristas"], 6)

    def test_unique_accounts(self):
        """Cuenta correctamente las cuentas únicas."""
        summary = summarize_edges(self.edges)
        # C100, C300, C400, C500 como origen; M200, C300, C400, C500, C100 como destino
        # Total únicas: C100, C300, C400, C500, M200
        self.assertEqual(summary["cuentas_totales_unicas"], 5)

    def test_fraud_rate(self):
        """La tasa de fraude se calcula correctamente."""
        summary = summarize_edges(self.edges)
        self.assertAlmostEqual(summary["tasa_fraude"], 1 / 6)

    def test_by_type_present(self):
        """El desglose por tipo tiene las claves esperadas."""
        summary = summarize_edges(self.edges)
        self.assertIn("PAYMENT", summary["por_tipo"])
        self.assertIn("TRANSFER", summary["por_tipo"])

    def test_amounts_are_positive(self):
        """Los montos agregados son positivos."""
        summary = summarize_edges(self.edges)
        self.assertGreater(summary["monto_total"], 0)
        self.assertGreater(summary["monto_medio"], 0)


if __name__ == "__main__":
    unittest.main()
