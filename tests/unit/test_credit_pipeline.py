"""Silver, contrato de variables, partición, calibración y entrenamiento de crédito con datos sintéticos."""

import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from bankshield.features.credit import RAW_COLUMNS, build_credit_feature_frame, feature_columns, invalid_reasons
from bankshield.models.credit import (CreditConfig, apply_calibrator, expected_calibration_error,
                                      fit_calibrator, split_silver, train_credit)
from bankshield.services.credit import CreditScorer
from bankshield.transforms.silver_credit import build_silver_credit, transform_credit


def synthetic_bronze(rows=600, seed=0):
    rng = np.random.default_rng(seed)
    age = rng.integers(21, 60, rows)
    income = rng.integers(20000, 120000, rows)
    amount = rng.integers(1000, 30000, rows)
    ratio = (amount / income).round(2)
    grade = rng.choice(list("ABCDEFG"), rows)
    default_file = rng.choice(["N", "Y"], rows)
    risk = 0.15 + 1.5 * ratio + 0.2 * (default_file == "Y")
    status = (rng.random(rows) < np.clip(risk, 0.02, 0.95)).astype(int)
    frame = pd.DataFrame({
        "person_age": age, "person_income": income,
        "person_home_ownership": rng.choice(["RENT", "OWN", "MORTGAGE", "OTHER"], rows),
        "person_emp_length": rng.integers(0, 7, rows).astype(float),
        "loan_intent": rng.choice(["PERSONAL", "EDUCATION", "MEDICAL", "VENTURE",
                                   "HOMEIMPROVEMENT", "DEBTCONSOLIDATION"], rows),
        "loan_grade": grade, "loan_amnt": amount,
        "loan_int_rate": rng.uniform(5, 22, rows).round(2), "loan_status": status,
        "loan_percent_income": ratio, "cb_person_default_on_file": default_file,
        "cb_person_cred_hist_length": rng.integers(2, 9, rows)})
    frame.loc[3, "person_emp_length"] = np.nan
    frame.loc[5, "loan_int_rate"] = np.nan
    return frame[list(RAW_COLUMNS)]


class CreditSilverTests(unittest.TestCase):
    def test_rejects_impossible_values_removes_duplicates_and_recomputes_ratio(self):
        bronze = synthetic_bronze(50)
        bronze.loc[1, "person_age"] = 144
        bronze.loc[2, "person_emp_length"] = 123.0
        bronze.loc[4, "loan_intent"] = "UNKNOWN"
        bronze = pd.concat([bronze, bronze.iloc[[10]]], ignore_index=True)
        silver, rejected, counts = transform_credit(bronze)
        self.assertEqual(counts["rejected_rows"], 3)
        self.assertEqual(counts["exact_duplicates_removed"], 1)
        self.assertEqual(counts["bronze_rows"], counts["silver_rows"] + 4)
        self.assertEqual(set(rejected["reject_reason"]),
                         {"age_out_of_range", "emp_length_impossible", "loan_intent_unknown_category"})
        np.testing.assert_allclose(silver["loan_percent_income"], silver["loan_amnt"] / silver["person_income"])
        self.assertTrue(silver["emp_length_missing"].any() and silver["int_rate_missing"].any())
        self.assertTrue(silver["row_id"].is_unique)

    def test_invalid_reasons_flags_missing_values_in_required_fields(self):
        bronze = synthetic_bronze(10)
        bronze.loc[0, "person_age"] = np.nan
        self.assertEqual(invalid_reasons(bronze).iloc[0], "age_out_of_range")
        self.assertTrue((invalid_reasons(bronze).iloc[1:] == "").all())

    def test_feature_frame_excludes_label_and_pricing_for_application_set(self):
        frame = build_credit_feature_frame(synthetic_bronze(20))
        self.assertEqual(list(frame.columns), feature_columns("application"))
        self.assertNotIn("loan_status", frame.columns)
        self.assertNotIn("loan_int_rate", frame.columns)
        self.assertIn("loan_grade", build_credit_feature_frame(synthetic_bronze(20), "with_pricing").columns)
        with self.assertRaises(ValueError):
            build_credit_feature_frame(synthetic_bronze(5).assign(person_home_ownership="BOAT"))
        with self.assertRaises(ValueError):
            build_credit_feature_frame(synthetic_bronze(5).drop(columns="loan_intent"))


class CreditTrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        root = Path(cls.work.name)
        cls.csv = root / "credit.csv"
        synthetic_bronze().to_csv(cls.csv, index=False)
        cls.silver, cls.quality = root / "credit.parquet", root / "quality.json"
        build_silver_credit(cls.csv, cls.silver, cls.quality)
        cls.config = CreditConfig(max_iter=30)
        cls.output = root / "model"
        cls.report = train_credit(cls.silver, cls.quality, cls.config, cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def test_split_is_disjoint_complete_stratified_and_deterministic(self):
        silver = pd.read_parquet(self.silver)
        parts = split_silver(silver, self.config)
        ids = [set(p["row_id"]) for p in parts.values()]
        self.assertEqual(len(ids[0] | ids[1] | ids[2]), len(silver))
        self.assertFalse(ids[0] & ids[1] or ids[0] & ids[2] or ids[1] & ids[2])
        for part in parts.values():
            self.assertAlmostEqual(part["loan_status"].mean(), silver["loan_status"].mean(), delta=0.02)
        again = split_silver(silver, self.config)
        self.assertTrue(parts["test"]["row_id"].equals(again["test"]["row_id"]))

    def test_report_has_baselines_calibration_and_frozen_threshold(self):
        test = self.report["test"]
        self.assertEqual(set(test), {"prior:application", "logistic:application",
                                     "hist_gradient_boosting:application",
                                     "hist_gradient_boosting:with_pricing",
                                     "hist_gradient_boosting:application:calibrated"})
        self.assertGreater(test["hist_gradient_boosting:application"]["roc_auc"], 0.55)
        self.assertEqual(test["prior:application"]["roc_auc"], 0.5)
        self.assertEqual(test["hist_gradient_boosting:application:calibrated"]["threshold"],
                         self.report["threshold_selection"]["threshold"])
        self.assertEqual(self.report["main_model"]["feature_set"], "application")
        json.dumps(self.report, allow_nan=False)

    def test_training_rejects_modified_or_failed_silver(self):
        quality = json.loads(self.quality.read_text(encoding="utf-8"))
        bad = Path(self.work.name) / "bad.json"
        bad.write_text(json.dumps({**quality, "quality_checks": {"row_ids_unique": False}}), encoding="utf-8")
        with self.assertRaises(ValueError):
            train_credit(self.silver, bad, self.config, Path(self.work.name) / "x")
        changed = Path(self.work.name) / "changed.json"
        changed.write_text(json.dumps({**quality, "output": {**quality["output"], "sha256": "0" * 64}}),
                           encoding="utf-8")
        with self.assertRaises(ValueError):
            train_credit(self.silver, changed, self.config, Path(self.work.name) / "x")

    def test_scorer_probability_explanation_and_reference(self):
        scorer = CreditScorer(self.output / "model.joblib")
        record = {"person_age": 30, "person_income": 40000.0, "person_home_ownership": "RENT",
                  "person_emp_length": None, "loan_intent": "MEDICAL", "loan_amnt": 30000.0,
                  "cb_person_default_on_file": "Y", "cb_person_cred_hist_length": 4}
        result = scorer.score([record])[0]
        self.assertTrue(0 <= result["default_probability"] <= 1)
        self.assertEqual(result["high_risk"], result["default_probability"] >= scorer.threshold)
        explanation = scorer.explain(record)
        self.assertLessEqual(len(explanation["factors"]), 5)
        self.assertFalse(explanation["causal"])
        effects = [abs(f["effect"]) for f in explanation["factors"]]
        self.assertEqual(effects, sorted(effects, reverse=True))
        safer = scorer.score([{**record, "loan_amnt": 1000.0, "cb_person_default_on_file": "N"}])[0]
        self.assertLess(safer["default_probability"], result["default_probability"])
        self.assertEqual(scorer.score([]), [])


class CalibrationTests(unittest.TestCase):
    def test_platt_reduces_error_for_overconfident_scores(self):
        rng = np.random.default_rng(1)
        true_p = rng.uniform(0.05, 0.6, 4000)
        labels = (rng.random(4000) < true_p).astype(int)
        overconfident = np.clip(true_p ** 3, 0.001, 0.999)
        calibrator = fit_calibrator(labels[:2000], overconfident[:2000])
        before = expected_calibration_error(labels[2000:], overconfident[2000:])
        after = expected_calibration_error(labels[2000:], apply_calibrator(calibrator, overconfident[2000:]))
        self.assertLess(after, before)


if __name__ == "__main__":
    unittest.main()
