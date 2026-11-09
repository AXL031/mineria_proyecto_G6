"""Pruebas de la comparación de alertas de red frente a la referencia por volumen.

El fixture se calculó a mano (percentil 80 en los tres indicadores):

Aristas (origen -> destino, monto, fraude):
  1 C1->C2 100 | 2 C1->C3 200 | 3 C1->C4 300 F | 4 C1->C5 400 | 5 C2->C6 50
  6 C3->C6 60  | 7 C4->C6 70 F | 8 C5->M7 10    | 9 C6->M7 20

Indicadores activos: C1 {fan-out, flujo}, M7 {fan-in, flujo}, C6 {fan-in},
C4 {flujo}, C5 {flujo}, C2 y C3 sin indicador.  Con el PageRank fijado a mano
el ranking de red es M7, C1, C6, C4, C5, C2, C3.
Volumen (enviado + recibido): C1 1000, C5 410, C4 370, C3 260, C6 200,
C2 150, M7 30.  Positivas: C1, C4 y C6 (extremos de las filas 3 y 7).
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pandas as pd

from bankshield.evaluation.graph import (
    NETWORK_METHOD,
    REFERENCE_METHOD,
    build_comparison_report,
    build_universe,
    comparison_config,
    edges_fingerprint,
    effective_budgets,
    evaluate_selection,
    positive_accounts,
    rank_network,
    rank_volume,
    render_comparison_markdown,
    validate_budgets,
)
from bankshield.features.graph import build_transaction_graph, compute_node_metrics

HAND_PAGERANK = {
    "C1": 0.10, "M7": 0.20, "C4": 0.15, "C5": 0.15,
    "C6": 0.30, "C2": 0.05, "C3": 0.05,
}
CONFIG = {
    "default_sample_limit": 10000,
    "budgets": [2, 3, 100],
    "fanout_percentile": 80,
    "fanin_percentile": 80,
    "flow_percentile": 80,
}
SOURCE = {"path": "fixture.csv", "sha256": "0" * 64, "size_bytes": 1}


def fixture_edges(fraud_rows=(3, 7)) -> pd.DataFrame:
    rows = [
        ("C1", "C2", 100.0), ("C1", "C3", 200.0), ("C1", "C4", 300.0),
        ("C1", "C5", 400.0), ("C2", "C6", 50.0), ("C3", "C6", 60.0),
        ("C4", "C6", 70.0), ("C5", "M7", 10.0), ("C6", "M7", 20.0),
    ]
    return pd.DataFrame({
        "step": list(range(1, 10)),
        "type": ["TRANSFER"] * 9,
        "amount": [r[2] for r in rows],
        "nameOrig": [r[0] for r in rows],
        "nameDest": [r[1] for r in rows],
        "isFraud": [1 if i + 1 in fraud_rows else 0 for i in range(9)],
    })


def prepared(edges: pd.DataFrame, hand_pagerank: bool = True):
    G = build_transaction_graph(edges)
    metrics = compute_node_metrics(G)
    if hand_pagerank:
        metrics["pagerank"] = pd.Series(HAND_PAGERANK)
    return G, metrics


def percentiles(value=80):
    return dict(fanout_percentile=value, fanin_percentile=value, flow_percentile=value)


class RankingTests(unittest.TestCase):
    def test_network_ranking_matches_hand_calculation(self):
        edges = fixture_edges()
        G, metrics = prepared(edges)
        ranking = rank_network(build_universe(edges), G, metrics, **percentiles())
        self.assertEqual(
            ranking["account"].tolist(),
            ["M7", "C1", "C6", "C4", "C5", "C2", "C3"],
        )
        self.assertEqual(ranking["pattern_count"].tolist(), [2, 2, 1, 1, 1, 0, 0])

    def test_volume_reference_matches_hand_calculation(self):
        edges = fixture_edges()
        G, metrics = prepared(edges)
        ranking = rank_volume(build_universe(edges), G, metrics)
        self.assertEqual(
            ranking["account"].tolist(),
            ["C1", "C5", "C4", "C3", "C6", "C2", "M7"],
        )
        self.assertEqual(
            ranking["total_volume"].tolist(),
            [1000.0, 410.0, 370.0, 260.0, 200.0, 150.0, 30.0],
        )

    def test_ties_are_resolved_by_account_id(self):
        # C4/C5 empatan en indicadores y PageRank; C2/C3 también.
        edges = fixture_edges()
        G, metrics = prepared(edges)
        order = rank_network(build_universe(edges), G, metrics, **percentiles())[
            "account"
        ].tolist()
        self.assertLess(order.index("C4"), order.index("C5"))
        self.assertLess(order.index("C2"), order.index("C3"))

    def test_accounts_without_indicator_stay_in_universe(self):
        edges = fixture_edges()
        G, metrics = prepared(edges)
        ranking = rank_network(build_universe(edges), G, metrics, **percentiles(100))
        self.assertEqual(len(ranking), 7)
        self.assertTrue((ranking["pattern_count"] == 0).all())
        # Sin indicadores, el orden es PageRank descendente y luego ID.
        self.assertEqual(ranking["account"].iloc[0], "C6")

    def test_changing_only_labels_keeps_universe_scores_order_and_k(self):
        base = fixture_edges((3, 7))
        other = fixture_edges((1, 5, 8))
        results = []
        for edges in (base, other):
            G, metrics = prepared(edges, hand_pagerank=False)
            universe = build_universe(edges)
            results.append((
                universe,
                rank_network(universe, G, metrics, **percentiles()),
                rank_volume(universe, G, metrics),
            ))
        self.assertEqual(results[0][0], results[1][0])
        pd.testing.assert_frame_equal(results[0][1], results[1][1])
        pd.testing.assert_frame_equal(results[0][2], results[1][2])

        reports = [
            build_comparison_report(e, *prepared(e, False), config=CONFIG,
                                    source=SOURCE, requested_limit=9)
            for e in (base, other)
        ]
        self.assertEqual(reports[0]["rankings"], reports[1]["rankings"])
        self.assertEqual(reports[0]["budgets"], reports[1]["budgets"])
        # Las métricas sí cambian con las etiquetas.
        self.assertNotEqual(reports[0]["comparisons"], reports[1]["comparisons"])

    def test_graph_and_sample_must_share_the_same_accounts(self):
        edges = fixture_edges()
        G, metrics = prepared(edges)
        with self.assertRaises(ValueError):
            rank_volume(build_universe(edges) + ["C99"], G, metrics)


class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.edges = fixture_edges()
        self.positives = positive_accounts(self.edges)

    def test_positive_accounts_use_origin_or_destination_of_fraud_rows(self):
        self.assertEqual(self.positives, {"C1", "C4", "C6"})

    def test_hand_metrics_for_network_k2(self):
        m = evaluate_selection(self.edges, ["M7", "C1"], self.positives)
        self.assertEqual(m["positive_accounts_selected"], 1)
        self.assertEqual(m["covered_transactions"], 6)
        self.assertEqual(m["covered_fraud_transactions"], 1)
        self.assertEqual(m["account_precision"]["value"], 0.5)
        self.assertAlmostEqual(m["account_recall"]["value"], 1 / 3)
        self.assertAlmostEqual(m["covered_transaction_precision"]["value"], 1 / 6)
        self.assertEqual(m["fraud_coverage"]["value"], 0.5)

    def test_transaction_with_both_ends_selected_is_counted_once(self):
        # La fila 4 (C1->C5) tiene ambos extremos seleccionados.
        m = evaluate_selection(self.edges, ["C1", "C5"], self.positives)
        self.assertEqual(m["covered_transactions"], 5)
        self.assertEqual(m["covered_transaction_precision"]["denominator"], 5)

    def test_numerators_and_denominators_are_stored(self):
        m = evaluate_selection(self.edges, ["C1", "C5", "C4"], self.positives)
        self.assertEqual(
            (m["fraud_coverage"]["numerator"], m["fraud_coverage"]["denominator"]), (2, 2)
        )
        self.assertEqual(
            (m["account_recall"]["numerator"], m["account_recall"]["denominator"]), (2, 3)
        )

    def test_duplicate_accounts_in_selection_are_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_selection(self.edges, ["C1", "C1"], self.positives)

    def test_unique_accounts_even_if_repeated_across_edges(self):
        # C1 aparece en cuatro aristas pero es una sola cuenta del universo.
        self.assertEqual(len(build_universe(self.edges)), 7)

    def test_no_positives_gives_null_with_reason(self):
        edges = fixture_edges(fraud_rows=())
        m = evaluate_selection(edges, ["C1"], positive_accounts(edges))
        self.assertIsNone(m["account_recall"]["value"])
        self.assertIn("positivas", m["account_recall"]["null_reason"])
        self.assertIsNone(m["fraud_coverage"]["value"])
        self.assertEqual(m["account_precision"]["value"], 0.0)
        self.assertEqual(m["covered_transaction_precision"]["value"], 0.0)

    def test_no_covered_transactions_gives_null_with_reason(self):
        m = evaluate_selection(self.edges, ["C99"], self.positives)
        self.assertEqual(m["covered_transactions"], 0)
        self.assertIsNone(m["covered_transaction_precision"]["value"])
        self.assertIn("cubierta", m["covered_transaction_precision"]["null_reason"])


class BudgetTests(unittest.TestCase):
    def test_effective_budgets_are_min_k_n_without_duplicates(self):
        effective, mapping = effective_budgets([10, 50, 100], 7)
        self.assertEqual(effective, [7])
        self.assertEqual(mapping, {10: 7, 50: 7, 100: 7})
        effective, _ = effective_budgets([10, 50, 100], 60)
        self.assertEqual(effective, [10, 50, 60])
        self.assertEqual(effective_budgets([10], 0), ([], {}))

    def test_invalid_budgets_are_rejected(self):
        for bad in (None, [], [0], [-1], [True], ["10"], "10"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_budgets(bad)
        self.assertEqual(validate_budgets([10, 10, 50]), [10, 50])

    def test_config_requires_comparison_block(self):
        with self.assertRaises(ValueError):
            comparison_config({"sample_limit": 1})
        with self.assertRaises(ValueError):
            comparison_config({"comparison": {**CONFIG, "fanout_percentile": 120}})
        self.assertEqual(comparison_config({"comparison": CONFIG})["budgets"], [2, 3, 100])

    def test_repo_config_is_valid(self):
        path = Path(__file__).resolve().parents[2] / "configs/graph.json"
        cfg = comparison_config(json.loads(path.read_text(encoding="utf-8")))
        self.assertEqual(cfg["budgets"], [10, 50, 100])
        self.assertEqual(cfg["default_sample_limit"], 10000)


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.edges = fixture_edges()
        self.report = build_comparison_report(
            self.edges, *prepared(self.edges), config=CONFIG, source=SOURCE,
            requested_limit=9,
        )

    def test_both_methods_return_exactly_k_distinct_accounts(self):
        self.assertEqual(self.report["budgets"]["effective"], [2, 3, 7])
        for k in (2, 3, 7):
            for method in (NETWORK_METHOD, REFERENCE_METHOD):
                chosen = self.report["rankings"][method]["selected_by_budget"][str(k)]
                self.assertEqual((len(chosen), len(set(chosen))), (k, k))

    def test_report_values_match_hand_calculation(self):
        by_k = {c["k"]: c for c in self.report["comparisons"]}
        self.assertEqual(by_k[2]["requested_budgets"], [2])
        self.assertEqual(by_k[7]["requested_budgets"], [100])
        self.assertEqual(by_k[2][NETWORK_METHOD]["covered_transactions"], 6)
        self.assertEqual(by_k[2][REFERENCE_METHOD]["covered_transactions"], 5)
        self.assertEqual(by_k[3][NETWORK_METHOD]["covered_transactions"], 9)
        self.assertEqual(by_k[3][REFERENCE_METHOD]["covered_transactions"], 6)
        self.assertAlmostEqual(
            by_k[3]["difference"]["covered_transaction_precision"], 2 / 9 - 2 / 6
        )
        # Con k = N ambos métodos seleccionan todo el universo.
        self.assertEqual(by_k[7][NETWORK_METHOD]["fraud_coverage"]["value"], 1.0)
        self.assertEqual(by_k[7]["difference"]["account_precision"], 0.0)

    def test_requested_budgets_are_kept_when_effective_ones_collapse(self):
        report = build_comparison_report(
            self.edges, *prepared(self.edges), config={**CONFIG, "budgets": [7, 10, 100]},
            source=SOURCE, requested_limit=9,
        )
        self.assertEqual(report["budgets"]["requested"], [7, 10, 100])
        self.assertEqual(report["budgets"]["effective"], [7])
        self.assertEqual(len(report["comparisons"]), 1)
        self.assertEqual(report["comparisons"][0]["requested_budgets"], [7, 10, 100])

    def test_report_documents_source_sample_and_limits(self):
        sample = self.report["sample"]
        self.assertEqual(sample["requested_limit"], 9)
        self.assertEqual((sample["rows_read"], sample["min_step"], sample["max_step"]), (9, 1, 9))
        self.assertEqual(sample["rows_fingerprint_sha256"], edges_fingerprint(self.edges))
        self.assertIn("Prefijo", sample["sampling_rule"])
        self.assertEqual(self.report["source"]["sha256"], SOURCE["sha256"])
        self.assertEqual(self.report["universe"]["size"], 7)
        self.assertEqual(self.report["universe"]["account_types"], {"cliente": 6, "comercio": 1})
        self.assertTrue(self.report["simulation_data"])
        self.assertEqual(self.report["scope"], "sample_retrospective")
        self.assertTrue(self.report["limitations"])
        self.assertIn("networkx", self.report["versions"])

    def test_report_is_deterministic_and_serializable(self):
        again = build_comparison_report(
            self.edges, *prepared(self.edges), config=CONFIG, source=SOURCE,
            requested_limit=9, generated_at=self.report["generated_at"],
        )
        self.assertEqual(again, self.report)
        json.dumps(self.report)
        other_limit = build_comparison_report(
            self.edges, *prepared(self.edges), config=CONFIG, source=SOURCE,
            requested_limit=50,
        )
        self.assertNotEqual(other_limit["analysis_id"], self.report["analysis_id"])

    def test_fingerprint_depends_on_rows_and_order(self):
        self.assertNotEqual(
            edges_fingerprint(self.edges), edges_fingerprint(self.edges.iloc[::-1])
        )

    def test_empty_sample_produces_empty_report(self):
        empty = self.edges.iloc[0:0]
        report = build_comparison_report(
            empty, None, None, config=CONFIG, source=SOURCE, requested_limit=1000,
        )
        self.assertEqual(report["universe"]["size"], 0)
        self.assertEqual(report["budgets"]["effective"], [])
        self.assertEqual(report["comparisons"], [])
        self.assertIsNone(report["sample"]["min_step"])
        self.assertIn("Sin presupuestos", render_comparison_markdown(report))

    def test_sample_without_fraud_reports_nulls(self):
        edges = fixture_edges(fraud_rows=())
        report = build_comparison_report(
            edges, *prepared(edges), config=CONFIG, source=SOURCE, requested_limit=9,
        )
        for comp in report["comparisons"]:
            self.assertIsNone(comp[NETWORK_METHOD]["fraud_coverage"]["value"])
            self.assertIsNone(comp["difference"]["fraud_coverage"])
        self.assertIn("n/d", render_comparison_markdown(report))

    def test_markdown_is_generated_from_report_content(self):
        text = render_comparison_markdown(self.report)
        self.assertIn(self.report["analysis_id"], text)
        self.assertIn("## k = 2", text)
        self.assertIn("1/6", text)
        self.assertIn("Datos de PaySim", text)


if __name__ == "__main__":
    unittest.main()
