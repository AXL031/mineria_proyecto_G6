import csv
import json
import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from bankshield.features.fraud import MODEL_FEATURES, build_fraud_features
from bankshield.ingestion.paysim_profile import FIELDS, profile_paysim, write_reports


def transaction(**changes):
    row = dict(zip(FIELDS, ["1", "TRANSFER", "100", "C1", "200", "100", "C2", "0", "100", "1", "0"]))
    row.update(changes)
    return row


class FraudProfileTests(unittest.TestCase):
    def setUp(self):
        parent = Path(__file__).resolve().parents[2] / "artifacts/reports/fraud-tests"
        parent.mkdir(parents=True, exist_ok=True)
        self.workdir = parent / uuid.uuid4().hex
        self.workdir.mkdir()
        self.addCleanup(self.cleanup_files)
        self.path = self.workdir / "paysim.csv"

    def cleanup_files(self):
        for path in self.workdir.iterdir():
            path.unlink()
        self.workdir.rmdir()

    def write_csv(self, rows):
        with self.path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def test_invalid_rows_are_reported_and_excluded_from_model_statistics(self):
        self.write_csv([transaction(), transaction(type="PAYMENT", isFraud="0", step="2"),
                        transaction(amount="NaN"), transaction(isFraud="2"),
                        transaction(nameOrig="")])
        profile = profile_paysim(self.path)
        self.assertEqual((profile["rows"], profile["valid_rows"], profile["invalid_rows"]), (5, 2, 3))
        self.assertEqual(profile["label_counts"], {"0": 1, "1": 1})
        self.assertEqual(profile["fraud_rate_valid_rows"], 0.5)
        self.assertEqual(profile["issues"]["invalid:amount"], 1)
        self.assertEqual(profile["missing_by_column"]["nameOrig"], 1)
        self.assertEqual(profile["by_step"], [{"step": 1, "rows": 1, "fraud": 1},
                                             {"step": 2, "rows": 1, "fraud": 0}])
        self.assertEqual(profile["temporal_summary"]["fraud_only_steps"], 1)
        self.assertEqual(profile["temporal_summary"]["last_step_with_nonfraud"], 2)

    def test_sample_is_labelled_and_limit_does_not_claim_full_coverage(self):
        self.write_csv([transaction(), transaction(isFraud="0")])
        self.assertEqual(profile_paysim(self.path, limit=1)["scope"], "first_rows_sample")
        self.assertEqual(profile_paysim(self.path, limit=2)["scope"], "complete_file")
        with self.assertRaises(ValueError):
            profile_paysim(self.path, limit=0)

    def test_lfs_pointer_and_empty_csv_fail_clearly(self):
        self.path.write_text("version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 123\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Git LFS"):
            profile_paysim(self.path)
        self.write_csv([])
        with self.assertRaisesRegex(ValueError, "no contiene registros"):
            profile_paysim(self.path)

    def test_reports_are_serializable_even_without_valid_records(self):
        self.write_csv([transaction(amount="inf")])
        profile = profile_paysim(self.path)
        output, markdown = self.path.with_suffix(".json"), self.path.with_suffix(".md")
        write_reports(profile, output, markdown)
        self.assertIsNone(json.loads(output.read_text(encoding="utf-8"))["fraud_rate_valid_rows"])
        self.assertTrue(markdown.exists())

    def test_features_ignore_labels_ids_and_post_transaction_balances(self):
        base = build_fraud_features(transaction())
        changed = build_fraud_features(transaction(isFraud="0", newbalanceOrig="999", newbalanceDest="999", isFlaggedFraud="1", nameOrig="different", step="50"))
        self.assertEqual(base, changed)
        self.assertEqual(tuple(base), MODEL_FEATURES)

    def test_features_support_zero_balance_and_reject_invalid_input(self):
        result = build_fraud_features(transaction(oldbalanceOrg="0"))
        self.assertEqual(result["amount_to_origin_balance"], 100)
        self.assertEqual(result["exceeds_origin_balance"], 1)
        for value in ("NaN", "inf", "-1", "", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                build_fraud_features(transaction(amount=value))


if __name__ == "__main__":
    unittest.main()
