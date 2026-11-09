from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from test_regression_dashboard import response

PAGE = Path(__file__).resolve().parents[2] / "dashboard/pages/01_fraude.py"


class AssociationsDashboardTests(unittest.TestCase):
    def test_empty_selection_and_changed_filters_are_visible(self):
        report = {"analysis_id": "fixture", "partition": "test", "offset": 0, "total_rules": 0, "rules": [],
                  "evaluation": {}, "dataset": {}, "config": {}, "diagnostic": "Sin reglas", "limitations": []}
        app = AppTest.from_file(str(PAGE), default_timeout=30).run()
        with patch("requests.request", return_value=response(200, report)) as request:
            app.button(key="associations_query").click().run()
        self.assertEqual(request.call_args.kwargs["params"]["partition"], "test")
        self.assertFalse(app.exception)
        self.assertTrue(any("No hay reglas" in item.value for item in app.info))
        app.selectbox(key="associations_partition").select("stress").run()
        self.assertTrue(any("filtros anteriores" in item.value for item in app.warning))

    def test_unavailable_associations_preserves_fraud_form(self):
        app = AppTest.from_file(str(PAGE), default_timeout=30).run()
        with patch("requests.request", return_value=response(503, {})):
            app.button(key="associations_query").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        self.assertTrue(any(button.label == "Evaluar transacción" for button in app.button))
