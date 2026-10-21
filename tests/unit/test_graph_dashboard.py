"""Pruebas unitarias para la interfaz de Streamlit de redes (03_redes.py)."""

import json
from pathlib import Path
import unittest
from unittest.mock import patch

import requests
from streamlit.testing.v1 import AppTest

PAGE = Path(__file__).resolve().parents[2] / "dashboard/pages/03_redes.py"


def mock_response(status, payload):
    resp = requests.Response()
    resp.status_code = status
    resp._content = json.dumps(payload).encode("utf-8")
    return resp


class GraphDashboardTests(unittest.TestCase):
    def setUp(self):
        self.summary_payload = {
            "status": "success",
            "simulation_data": True,
            "graph_summary": {
                "nodos": 100,
                "aristas_unicas": 150,
                "densidad": 0.015,
                "pares_con_fraude": 2,
            },
            "edges_summary": {
                "monto_total": 500000.0,
                "tasa_fraude": 0.02,
            },
        }
        self.top_payload = {
            "status": "success",
            "results": [
                {"account": "C100", "pagerank": 0.05, "transactions_sent": 2, "transactions_received": 1}
            ],
        }

    def test_dashboard_renders_metrics_from_api(self):
        """Verifica que el dashboard consuma los endpoints de la API al iniciar."""
        def fake_get(url, **kwargs):
            if "summary" in url:
                return mock_response(200, self.summary_payload)
            if "top" in url:
                return mock_response(200, self.top_payload)
            return mock_response(200, {})

        with patch("requests.get", side_effect=fake_get) as mock_req:
            app = AppTest.from_file(str(PAGE)).run()
            self.assertFalse(app.exception)
            # Debe haber consultado la API (summary y top)
            called_urls = [call.args[0] for call in mock_req.call_args_list]
            self.assertTrue(any("summary" in u for u in called_urls))
            # Verificar KPIs renderizados
            metric_values = [m.value for m in app.metric]
            self.assertIn("100", metric_values)
            self.assertIn("150", metric_values)

    def test_api_offline_displays_error(self):
        """Si la API no responde, se muestra un mensaje de error claro."""
        with patch("requests.get", side_effect=requests.ConnectionError("API Offline")):
            app = AppTest.from_file(str(PAGE)).run()
            self.assertFalse(app.exception)
            self.assertTrue(len(app.error) >= 1)

    def test_real_subgraph_renders_with_inline_resources_and_consistent_sample(self):
        from bankshield.features.graph import build_transaction_graph
        from bankshield.services.graph import query_account, query_subgraph
        from tests.unit.test_api_graphs import _mock_edges_df
        graph = build_transaction_graph(_mock_edges_df())
        calls = []
        def fake_get(url, **kwargs):
            calls.append(kwargs["params"]["limit"])
            if "summary" in url:
                return mock_response(200, self.summary_payload)
            if "subgraph" in url:
                return mock_response(200, {"data": query_subgraph(graph, "C100")})
            if "account/" in url:
                return mock_response(200, {"data": query_account(graph, "C100")})
            if "top" in url:
                return mock_response(200, self.top_payload)
            return mock_response(200, {"results": [], "total_detected": 0})
        with patch("requests.get", side_effect=fake_get):
            page = AppTest.from_file(str(PAGE)).run()
        self.assertFalse(page.exception)
        self.assertFalse(page.error)
        self.assertGreaterEqual(len(calls), 5)
        self.assertEqual(len(set(calls)), 1)


if __name__ == "__main__":
    unittest.main()
