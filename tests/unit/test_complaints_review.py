"""Revisión de ejemplos del clasificador de reclamos con un modelo entrenado sobre datos sintéticos."""

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from bankshield.ingestion.complaints_profile import FIELDS
from bankshield.models.complaints import ComplaintsConfig, train_complaints
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline

from bankshield.models.complaints_review import (MANUAL_MARKER, build_error_review, near_duplicate_summary,
                                                 review_markdown, write_review)
from bankshield.transforms.silver_complaints import build_silver_complaints

CONFIG = ComplaintsConfig(min_words=3, min_df=2, c_candidates=(1.0,), top_terms=3)
VOCABULARY = {
    "Mortgage": ["house", "escrow", "foreclosure", "payment", "lender"],
    "Credit card": ["card", "interest", "purchase", "statement", "limit"],
}
SHARED = ["account", "told", "never", "received", "please"]


def synthetic_rows():
    import numpy as np
    rng = np.random.default_rng(1)
    rows, cid = [], 0
    for product, words in VOCABULARY.items():
        for i in range(80):
            cid += 1
            # Una de cada diez mezcla vocabulario ajeno para producir errores que revisar.
            pool = words if i % 10 else sum(VOCABULARY.values(), [])
            text = " ".join(rng.choice(pool, 6).tolist() + rng.choice(SHARED, 3).tolist())
            month, day = 3 + (cid * 7) % 9, 1 + (cid * 3) % 27
            date = f"{month:02d}/{day:02d}/2015"
            rows.append({field: "" for field in FIELDS} | {
                "date_received": date, "date_sent_to_company": date, "product": product, "issue": "x",
                "company": "Acme", "state": "CA", "zipcode": "90210", "submitted_via": "Web",
                "company_response_to_consumer": "Closed", "timely_response": "Yes", "consumer_disputed?": "No",
                "consumer_consent_provided": "Consent provided", "complaint_id": str(cid),
                "consumer_complaint_narrative": text})
    return rows


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        bronze = self.root / "c.csv"
        with bronze.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(synthetic_rows())
        self.silver, self.quality = self.root / "s.parquet", self.root / "q.json"
        build_silver_complaints(bronze, self.silver, self.quality)
        train_complaints(self.silver, self.quality, CONFIG, self.root / "model")
        self.model = self.root / "model" / "model.joblib"

    def test_review_structure_and_counts(self):
        review = build_error_review(self.model, self.silver, self.quality, pairs=2, per_pair=2)
        self.assertEqual(review["errors"], round((1 - review["accuracy"]) * review["test_rows"]))
        self.assertEqual(sum(b["rows"] for b in review["confidence_buckets"]), review["test_rows"])
        for pair in review["confused_pairs"]:
            self.assertNotEqual(pair["true"], pair["predicted"])
            self.assertLessEqual(len(pair["examples"]), 2)
            for ex in pair["examples"]:
                self.assertEqual((ex["true"], ex["predicted"]), (pair["true"], pair["predicted"]))
        for ex in review["high_confidence_errors"]:
            self.assertNotEqual(ex["true"], ex["predicted"])
        confidences = [ex["confidence"] for ex in review["high_confidence_errors"]]
        self.assertEqual(confidences, sorted(confidences, reverse=True))

    def test_review_is_reproducible_with_seed(self):
        first = build_error_review(self.model, self.silver, self.quality, seed=7)
        second = build_error_review(self.model, self.silver, self.quality, seed=7)
        self.assertEqual(first, second)

    def test_mismatched_silver_is_rejected(self):
        frame = pd.read_parquet(self.silver)
        frame.loc[0, "product"] = "Other"
        frame.to_parquet(self.silver, index=False)
        with self.assertRaises(ValueError):
            build_error_review(self.model, self.silver, self.quality)

    def test_write_preserves_manual_observations(self):
        review = build_error_review(self.model, self.silver, self.quality)
        json_path, md_path = self.root / "r.json", self.root / "r.md"
        write_review(review, json_path, md_path)
        self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["test_rows"], review["test_rows"])
        text = md_path.read_text(encoding="utf-8")
        self.assertIn(MANUAL_MARKER, text)
        self.assertIn("Pendiente", text)
        md_path.write_text(text.replace("_Pendiente: registrar tras leer los ejemplos._", "Observación escrita a mano."),
                           encoding="utf-8")
        write_review(review, json_path, md_path)
        self.assertIn("Observación escrita a mano.", md_path.read_text(encoding="utf-8"))
        self.assertEqual(md_path.read_text(encoding="utf-8").count(MANUAL_MARKER), 1)

    def test_markdown_keeps_markers_inside_code(self):
        review = build_error_review(self.model, self.silver, self.quality)
        review["high_confidence_errors"][0]["text"] = "paid <monto> on `date`"
        self.assertIn("`paid <monto> on 'date'`", review_markdown(review))


class NearDuplicateTests(unittest.TestCase):
    def test_detects_near_copies_and_splits_accuracy(self):
        train = ["foreclosure escrow lender payment house", "card interest purchase statement limit",
                 "collector calls harassment validation debt"]
        pipeline = Pipeline([("tfidf", TfidfVectorizer().fit(train))])
        test = ["foreclosure escrow lender payment house", "card interest purchase statement limit rewards",
                "completely unrelated words here"]
        summary = near_duplicate_summary(pipeline, train, test, [True, False, True], threshold=0.8)
        self.assertEqual(summary["near_duplicate_rows"], 2)
        self.assertAlmostEqual(summary["share"], 2 / 3)
        self.assertAlmostEqual(summary["accuracy_near"], 0.5)
        self.assertAlmostEqual(summary["accuracy_rest"], 1.0)

    def test_no_near_duplicates(self):
        pipeline = Pipeline([("tfidf", TfidfVectorizer().fit(["alpha beta", "gamma delta"]))])
        summary = near_duplicate_summary(pipeline, ["alpha beta"], ["gamma delta"], [True])
        self.assertEqual(summary["near_duplicate_rows"], 0)
        self.assertIsNone(summary["accuracy_near"])


if __name__ == "__main__":
    unittest.main()
