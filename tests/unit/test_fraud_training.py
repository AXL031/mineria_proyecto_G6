import csv
import json
import sys
import unittest
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from bankshield.features.fraud import build_fraud_features, build_fraud_feature_frame
from bankshield.ingestion.fraud_dataset import derive_split_steps, read_fraud_dataset
from bankshield.ingestion.paysim_profile import FIELDS, profile_paysim, write_reports
from bankshield.models.fraud import FraudConfig, evaluate_scores, select_threshold, train_fraud
from bankshield.services.fraud import FraudScorer


class FraudTrainingTests(unittest.TestCase):
    def setUp(self):
        parent = Path(__file__).resolve().parents[2] / "artifacts/reports/fraud-tests"
        parent.mkdir(parents=True, exist_ok=True)
        self.workdir = parent / uuid.uuid4().hex
        self.workdir.mkdir()
        self.addCleanup(self.cleanup_files)

    def cleanup_files(self):
        for path in self.workdir.iterdir():
            if path.is_dir():
                for child in path.iterdir():
                    child.unlink()
                path.rmdir()
            else:
                path.unlink()
        self.workdir.rmdir()

    def source(self):
        path = self.workdir / "paysim.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            for step in (1, 2, 3):
                for i in range(40):
                    fraud = i % 4 == 0
                    writer.writerow(dict(zip(FIELDS, [step, "TRANSFER", 500 if fraud else 5,
                                                       f"C{i}", 100, 0, f"D{i}", 100, 0,
                                                       int(fraud), 0])))
        return path

    def test_split_derivation_ignores_labels_and_keeps_whole_steps(self):
        steps = [{"step": i, "rows": 10, "fraud": i % 2} for i in range(1, 11)]
        self.assertEqual(derive_split_steps(steps), (7, 9))
        self.assertEqual(derive_split_steps([{**item, "fraud": 10} for item in steps]), (7, 9))
        with self.assertRaises(ValueError):
            derive_split_steps([{"step": 1, "rows": 100}, {"step": 2, "rows": 1}, {"step": 3, "rows": 1}])

    def test_reader_partitions_and_audits_accounts_without_predicting_ids(self):
        partitions, audit = read_fraud_dataset(self.source(), 1, 2, chunksize=17, account_sample_modulus=1)
        for name, step in zip(("train", "validation", "test"), (1, 2, 3)):
            self.assertEqual(set(partitions[name].steps), {step})
            self.assertEqual(len(partitions[name].labels), 40)
            self.assertNotIn("step", partitions[name].features.columns)
            self.assertNotIn("nameOrig", partitions[name].features.columns)
        self.assertEqual(audit["sampled_intersections"]["nameOrig"]["train_test"], 40)

    def test_vector_features_match_single_record_and_ignore_post_transaction_data(self):
        records = [{"type": "TRANSFER", "amount": 5, "oldbalanceOrg": 0, "isFraud": 1,
                    "newbalanceOrig": 999}]
        frame = build_fraud_feature_frame(pd.DataFrame(records))
        self.assertEqual(frame.iloc[0].to_dict(), build_fraud_features(records[0]))
        for value in (np.nan, np.inf, -1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                build_fraud_feature_frame(pd.DataFrame([{**records[0], "amount": value}]))

    def test_threshold_minimizes_cost_with_tied_scores(self):
        labels = np.array([0, 1, 0, 1, 1, 0])
        scores = np.array([0.9, 0.9, 0.3, 0.3, 0.1, 0.0])
        result = select_threshold(labels, scores, 2, 5)
        candidates = np.r_[np.unique(scores), np.nextafter(scores.max(), np.inf)]
        def cost(threshold):
            predicted = scores >= threshold
            return 2 * np.sum(predicted & (labels == 0)) + 5 * np.sum(~predicted & (labels == 1))
        minimum = min(cost(t) for t in candidates)
        self.assertEqual(result["validation_cost_units"], minimum)
        self.assertEqual(result["threshold"], max(t for t in candidates if cost(t) == minimum))

    def test_no_alert_option_is_available_for_constant_scores(self):
        result = select_threshold([0, 0, 0, 1], [0.1] * 4, 1, 1)
        self.assertGreater(result["threshold"], 0.1)
        self.assertEqual(result["validation_cost_units"], 1)

    def test_metrics_report_confusion_and_reject_single_class(self):
        result = evaluate_scores([0, 0, 1, 1], [0.1, 0.8, 0.7, 0.2], 0.5, FraudConfig())
        self.assertEqual(result["confusion"], {"tn": 1, "fp": 1, "fn": 1, "tp": 1})
        with self.assertRaises(ValueError):
            evaluate_scores([0, 0], [0.1, 0.2], 0.5, FraudConfig())

    def test_roundtrip_training_and_scoring_and_changed_source_rejected(self):
        source = self.source()
        profile = self.workdir / "profile.json"
        write_reports(profile_paysim(source), profile)
        config = FraudConfig(train_end_step=1, validation_end_step=2, max_iter=3,
                             min_samples_leaf=2, chunksize=50, threads=1)
        output = self.workdir / "model"
        report = train_fraud(source, config, profile, output)
        self.assertEqual(report["partitions"]["test"]["rows"], 40)
        scorer = FraudScorer(output / "model.joblib")
        records = [{"type": "TRANSFER", "amount": 500, "oldbalanceOrg": 100}]
        first = scorer.score(records)[0]
        changed = scorer.score([{**records[0], "isFraud": 0, "newbalanceOrig": 999}])[0]
        self.assertEqual(first, changed)
        self.assertEqual(first["threshold"], report["threshold_selection"]["threshold"])
        self.assertEqual(first["alert"], first["score"] >= first["threshold"])
        self.assertEqual(scorer.score([]), [])
        source.write_text(source.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "cambió"):
            train_fraud(source, config, profile, output)


if __name__ == "__main__":
    unittest.main()
