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


class GraphComparisonPanelTests(unittest.TestCase):
    """El panel de comparación muestra la muestra correcta y aísla sus fallos."""

    @classmethod
    def setUpClass(cls):
        from bankshield.evaluation.graph import build_comparison_report
        from bankshield.services.graph import comparison_response
        from tests.unit.test_graph_comparison import CONFIG, SOURCE, fixture_edges, prepared

        edges = fixture_edges()
        report = build_comparison_report(
            edges, *prepared(edges), config=CONFIG, source=SOURCE, requested_limit=50_000,
        )
        cls.payload = comparison_response(report, 50_000)

    def setUp(self):
        self.summary_payload = {
            "status": "success",
            "simulation_data": True,
            "graph_summary": {"nodos": 100, "aristas_unicas": 150, "densidad": 0.015,
                              "pares_con_fraude": 2},
            "edges_summary": {"monto_total": 500000.0, "tasa_fraude": 0.02},
        }
        self.top_payload = {"status": "success", "results": []}
        self.calls = []

    def run_page(self, comparison_response):
        def fake_get(url, **kwargs):
            self.calls.append((url, kwargs["params"]["limit"]))
            if "evaluation" in url:
                return comparison_response
            if "summary" in url:
                return mock_response(200, self.summary_payload)
            if "top" in url:
                return mock_response(200, self.top_payload)
            return mock_response(200, {"results": [], "total_detected": 0})

        with patch("requests.get", side_effect=fake_get):
            return AppTest.from_file(str(PAGE)).run(timeout=60)

    def test_comparison_is_shown_with_sample_levels_and_limitations(self):
        page = self.run_page(mock_response(200, self.payload))
        self.assertFalse(page.exception)
        self.assertFalse(page.error)
        text = " ".join(m.value for m in page.markdown)
        self.assertIn(self.payload["analysis_id"], text)
        self.assertIn("50,000", text)
        self.assertIn("7 cuentas", text)
        frames = [d.value for d in page.dataframe if "Referencia por volumen" in d.value.columns]
        self.assertEqual(len(frames), 1)
        table = frames[0]
        self.assertEqual(set(table["k"]), {2, 3, 7})
        self.assertEqual(set(table["Nivel"]), {"cuenta", "transacción"})
        row = table[(table["k"] == 2) & (table["Métrica"] == "Cobertura de fraude")].iloc[0]
        self.assertEqual(row["Red (indicadores)"], "50.00% (1/2)")
        self.assertEqual(row["Referencia por volumen"], "50.00% (1/2)")
        self.assertEqual(row["Diferencia (pp)"], "+0.00")

    def test_comparison_uses_the_same_sample_as_other_queries(self):
        self.run_page(mock_response(200, self.payload))
        limits = {limit for _, limit in self.calls}
        self.assertEqual(limits, {50_000})
        self.assertTrue(any("evaluation" in url for url, _ in self.calls))

    def test_other_sample_shows_specific_notice_and_keeps_other_queries(self):
        detail = {"code": "sample_mismatch",
                  "message": "El reporte corresponde a una muestra solicitada de 10000 filas, no de 50,000. Regenere la comparación para esa muestra."}
        page = self.run_page(mock_response(503, {"detail": detail}))
        self.assertFalse(page.exception)
        self.assertFalse(page.error)
        text = " ".join(m.value for m in page.markdown)
        self.assertIn("El reporte no corresponde a esta muestra", text)
        self.assertIn("Regenere la comparación", text)
        self.assertIn("100", [m.value for m in page.metric])
        self.assertFalse([d for d in page.dataframe if "Referencia por volumen" in d.value.columns])

    def test_missing_and_incompatible_reports_have_their_own_notice(self):
        cases = {
            "report_missing": "Comparación no disponible",
            "incompatible_version": "Reporte de comparación con versión incompatible",
        }
        for code, title in cases.items():
            with self.subTest(code=code):
                page = self.run_page(mock_response(503, {"detail": {"code": code, "message": "Detalle."}}))
                self.assertFalse(page.exception)
                self.assertFalse(page.error)
                self.assertIn(title, " ".join(m.value for m in page.markdown))

    def test_unreachable_api_for_comparison_does_not_break_page(self):
        def fake_get(url, **kwargs):
            if "evaluation" in url:
                raise requests.ConnectionError("sin conexión")
            if "summary" in url:
                return mock_response(200, self.summary_payload)
            return mock_response(200, {"results": [], "total_detected": 0})

        with patch("requests.get", side_effect=fake_get):
            page = AppTest.from_file(str(PAGE)).run(timeout=60)
        self.assertFalse(page.exception)
        self.assertIn("API no disponible", " ".join(m.value for m in page.markdown))

    def test_null_metrics_show_reason_instead_of_a_number(self):
        payload = json.loads(json.dumps(self.payload))
        metric = payload["comparisons"][0]["network_indicators"]["fraud_coverage"]
        metric.update(value=None, null_reason="la muestra no tiene transacciones fraudulentas")
        page = self.run_page(mock_response(200, payload))
        table = [d.value for d in page.dataframe if "Referencia por volumen" in d.value.columns][0]
        row = table[(table["k"] == payload["comparisons"][0]["k"]) & (table["Métrica"] == "Cobertura de fraude")].iloc[0]
        self.assertIn("n/d (la muestra no tiene transacciones fraudulentas)", row["Red (indicadores)"])


if __name__ == "__main__":
    unittest.main()
