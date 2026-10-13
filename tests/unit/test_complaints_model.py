"""Partición temporal, métricas y entrenamiento del clasificador de reclamos con datos sintéticos."""

import csv
import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from bankshield.ingestion.complaints_profile import FIELDS
from bankshield.models.complaints import (MAIN_KEY, STOP_WORDS, ComplaintsConfig, evaluate_predictions,
                                          select_narratives, split_temporal, train_complaints)
from bankshield.transforms.silver_complaints import build_silver_complaints

VOCABULARY = {
    "Mortgage": ["house", "escrow", "foreclosure", "payment", "lender", "refinance", "property", "closing"],
    "Credit card": ["card", "interest", "purchase", "statement", "limit", "rewards", "charge", "annual"],
    "Debt collection": ["collector", "calls", "harassment", "validation", "debt", "threats", "agency", "owed"],
}
COMMON = ["account", "told", "never", "received", "please", "years", "company", "letter"]
TEST_CONFIG = ComplaintsConfig(min_words=3, min_df=2, c_candidates=(1.0, 5.0), top_terms=3)


def synthetic_rows(per_product=70, seed=0):
    rng = np.random.default_rng(seed)
    start = date(2015, 3, 20)
    rows, cid = [], 0
    for product, words in VOCABULARY.items():
        for _ in range(per_product):
            cid += 1
            text = " ".join(rng.choice(words, 9).tolist() + rng.choice(COMMON, 4).tolist())
            day = start + timedelta(days=int(rng.integers(0, 300)))
            rows.append({"date_received": day.strftime("%m/%d/%Y"), "product": product, "sub_product": "",
                         "issue": "x", "sub_issue": "", "consumer_complaint_narrative": text,
                         "company_public_response": "", "company": "Acme", "state": "CA", "zipcode": "90210",
                         "tags": "", "consumer_consent_provided": "Consent provided", "submitted_via": "Web",
                         "date_sent_to_company": day.strftime("%m/%d/%Y"),
                         "company_response_to_consumer": "Closed", "timely_response": "Yes",
                         "consumer_disputed?": "No", "complaint_id": str(cid)})
    return rows


class SplitTests(unittest.TestCase):
    def frame(self, rows):
        return pd.DataFrame(rows).assign(date_received=lambda d: pd.to_datetime(d["date_received"]))

    def test_select_excludes_missing_and_short_narratives(self):
        silver = pd.DataFrame({"has_narrative": [True, True, False], "clean_word_count": [10, 2, 0]})
        selected, ex = select_narratives(silver, ComplaintsConfig(min_words=5))
        self.assertEqual((len(selected), ex["too_short"], ex["without_narrative"]), (1, 1, 1))

    def test_split_is_chronological_disjoint_and_text_safe(self):
        rows = []
        for i in range(100):
            rows.append({"complaint_id": i, "product": "A" if i % 2 else "B",
                         "date_received": date(2015, 1, 1) + timedelta(days=i), "narrative_clean": f"text {i}"})
        # Mismo texto en una fecha temprana y otra tardía: debe quedar entero en entrenamiento.
        rows.append({"complaint_id": 100, "product": "A", "date_received": date(2015, 12, 31),
                     "narrative_clean": "text 0"})
        data = self.frame(rows)
        parts, cuts = split_temporal(data, ComplaintsConfig())
        train, valid, test = parts["train"], parts["validation"], parts["test"]
        self.assertEqual(len(train) + len(valid) + len(test), len(data))
        # La fila 100 repite un texto temprano: se asigna a entrenamiento aunque su fecha sea tardía.
        self.assertIn(100, set(train["complaint_id"]))
        train = train[train["complaint_id"] != 100]
        self.assertLess(train["date_received"].max(), valid["date_received"].min())
        self.assertLess(valid["date_received"].max(), test["date_received"].min())
        self.assertFalse(set(train["narrative_clean"]) & set(test["narrative_clean"]))
        self.assertLess(cuts["train_until"], cuts["validation_until"])

    def test_empty_partition_is_rejected(self):
        data = self.frame([{"complaint_id": i, "product": "A" if i % 2 else "B",
                            "date_received": date(2015, 1, 1), "narrative_clean": f"t{i}"} for i in range(10)])
        with self.assertRaises(ValueError):
            split_temporal(data, ComplaintsConfig())


class MetricsTests(unittest.TestCase):
    def test_known_predictions(self):
        classes = ["A", "B", "C"]
        y = ["A", "A", "B", "B"]
        proba = np.array([[.8, .1, .1], [.2, .7, .1], [.1, .8, .1], [.3, .6, .1]])
        r = evaluate_predictions(y, proba, classes)
        self.assertAlmostEqual(r["accuracy"], 0.75)
        self.assertAlmostEqual(r["per_class"]["A"]["recall"], 0.5)
        self.assertAlmostEqual(r["per_class"]["B"]["precision"], 2 / 3)
        self.assertNotIn("C", r["per_class"])          # sin soporte: no entra al promedio
        self.assertAlmostEqual(r["macro_f1"], (r["per_class"]["A"]["f1"] + r["per_class"]["B"]["f1"]) / 2)
        self.assertEqual(r["top3_accuracy"], 1.0)

    def test_rejects_invalid_probabilities(self):
        with self.assertRaises(ValueError):
            evaluate_predictions(["A"], np.array([[np.nan, 1.0]]), ["A", "B"])
        with self.assertRaises(ValueError):
            evaluate_predictions(["A", "B"], np.array([[1.0, 0.0]]), ["A", "B"])


class ConfigTests(unittest.TestCase):
    def test_invalid_values(self):
        for bad in ({"train_fraction": 0.9, "validation_fraction": 0.2}, {"min_df": 0}, {"max_df": 0},
                    {"nb_alpha": -1.0}, {"c_candidates": ()}, {"c_candidates": (0.0,)}):
            with self.assertRaises(ValueError):
                ComplaintsConfig(**bad)

    def test_marker_tokens_are_stop_words(self):
        for token in ("fecha", "monto", "censurado", "the"):
            self.assertIn(token, STOP_WORDS)


class TrainingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        bronze = self.root / "complaints.csv"
        with bronze.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(synthetic_rows())
        self.silver = self.root / "silver.parquet"
        self.quality = self.root / "quality.json"
        build_silver_complaints(bronze, self.silver, self.quality)

    def train(self, **kwargs):
        return train_complaints(self.silver, self.quality, TEST_CONFIG, self.root / "model", **kwargs)

    def test_main_model_beats_references_and_writes_artifacts(self):
        markdown = self.root / "resultados.md"
        report = self.train(markdown_path=markdown)
        test = report["test"]
        self.assertGreater(test[MAIN_KEY]["macro_f1"], test["prior"]["macro_f1"])
        self.assertGreater(test[MAIN_KEY]["accuracy"], 0.9)
        self.assertGreaterEqual(test[MAIN_KEY]["macro_f1"], test["naive_bayes"]["macro_f1"] - 0.05)
        beats = all(test[MAIN_KEY]["macro_f1"] > test[k]["macro_f1"] for k in ("prior", "naive_bayes"))
        self.assertEqual(report["main_beats_references_on_test"], beats)
        self.assertEqual(sum(p["rows"] for p in report["partitions"].values()), report["exclusions"]["selected"])
        self.assertIn(report["main_model"]["C"], TEST_CONFIG.c_candidates)
        self.assertEqual(len(report["top_terms"]["Mortgage"]), TEST_CONFIG.top_terms)
        bundle = joblib.load(self.root / "model" / "model.joblib")
        predicted = bundle["pipeline"].predict(["foreclosure escrow lender payment house closing"])
        self.assertEqual(predicted[0], "Mortgage")
        saved = json.loads((self.root / "model" / "metrics.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["training_input"]["sha256"], report["training_input"]["sha256"])
        self.assertIn("Resultados del análisis NLP", markdown.read_text(encoding="utf-8"))

    def test_training_is_deterministic(self):
        first, second = self.train(), self.train()
        self.assertEqual(first["test"][MAIN_KEY]["accuracy"], second["test"][MAIN_KEY]["accuracy"])
        self.assertEqual(first["c_selection"], second["c_selection"])

    def test_changed_silver_is_rejected(self):
        frame = pd.read_parquet(self.silver)
        frame.loc[0, "product"] = "Other"
        frame.to_parquet(self.silver, index=False)
        with self.assertRaises(ValueError):
            self.train()


if __name__ == "__main__":
    unittest.main()
