"""Entrenamiento, selección con validation, métricas y artefactos de regresión sobre D1 sintético."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from bankshield.features.regression import build_regression_feature_frame
from bankshield.models.regression import (
    Accumulator, MedianByType, RegressionConfig, choose_model, select_train_sample, summarize, train_regression)

TYPES = ["PAYMENT", "TRANSFER", "CASH_OUT", "DEBIT", "CASH_IN"]


def synthetic_d1(root, drop_type=None):
    """D1 mínimo con las columnas del contrato; drop_type deja ese tipo fuera de train."""
    rng = np.random.default_rng(0)
    steps = np.repeat(np.arange(1, 744), 8)
    kinds = rng.choice(TYPES, size=steps.size)
    if drop_type:
        kinds[(steps <= 323) & (kinds == drop_type)] = "PAYMENT"
    balance = np.where(rng.random(steps.size) < 0.2, 0.0, rng.lognormal(8, 1.5, steps.size))
    amount = np.exp(rng.normal(7, 1, steps.size)) * (1 + (kinds == "TRANSFER"))
    partition = np.select([steps <= 323, steps <= 378, steps <= 718], ["train", "validation", "test"], "stress")
    frame = pd.DataFrame({"row_id": np.arange(1, steps.size + 1), "step": steps, "type": kinds, "amount": amount,
                          "oldbalanceOrg": balance, "isFraud": (steps > 718).astype("int8"),
                          "partition": partition, "amount_bin": "b0", "origin_balance_bin": "b0"})
    path = Path(root) / "d1.parquet"
    frame.to_parquet(path, index=False)
    sha = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    report = Path(root) / "dataset.json"
    report.write_text(json.dumps({"source": {"sha256": "A" * 64}, "output": {"sha256": sha}}), encoding="utf-8")
    return path, report, frame


class RegressionTrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        cls.root = Path(cls.work.name)
        cls.path, cls.report, cls.frame = synthetic_d1(cls.root)
        cls.config = RegressionConfig(max_train_rows=1500)
        cls.out = cls.root / "model"
        cls.result = train_regression(cls.config, cls.path, cls.report, cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def test_sample_is_deterministic_and_train_only(self):
        parts = self.frame["partition"].to_numpy()
        a, info = select_train_sample(parts, self.config)
        b, _ = select_train_sample(parts, self.config)
        np.testing.assert_array_equal(a, b)
        self.assertTrue((parts[a] == "train").all())
        self.assertEqual(info["rows_used"], 1500)
        self.assertEqual(self.result["train_sample"]["rows_used"], 1500)
        self.assertEqual(self.result["train_sample"]["rows_available"], int((parts == "train").sum()))
        self.assertEqual(len(select_train_sample(parts, RegressionConfig(max_train_rows=None))[0]),
                         int((parts == "train").sum()))

    def test_reference_matches_manual_medians_with_global_fallback(self):
        features = build_regression_feature_frame(["PAYMENT", "PAYMENT", "TRANSFER"], [1.0, 2.0, 3.0])
        ref = MedianByType.fit(features, [10.0, 20.0, 100.0])
        probe = build_regression_feature_frame(["PAYMENT", "TRANSFER", "DEBIT"], [1.0, 1.0, 1.0])
        np.testing.assert_allclose(ref.predict(probe), [15.0, 100.0, 20.0])

    def test_metrics_match_manual_calculation(self):
        acc = Accumulator()
        acc.add(("p",), np.array([10.0, 20.0, 30.0]), np.array([12.0, 18.0, 33.0]))
        got = summarize(acc.total(lambda k: True))
        error = np.array([2.0, -2.0, 3.0])
        self.assertEqual(got["n"], 3)
        self.assertAlmostEqual(got["mae"], np.abs(error).mean())
        self.assertAlmostEqual(got["rmse"], np.sqrt((error ** 2).mean()))
        self.assertAlmostEqual(got["mean_bias"], error.mean())
        self.assertAlmostEqual(got["r2"], 1 - (error ** 2).sum() / 200.0)

    def test_r2_is_null_with_reason_when_variance_is_zero(self):
        acc = Accumulator()
        acc.add(("p",), np.array([5.0, 5.0]), np.array([4.0, 6.0]))
        got = summarize(acc.total(lambda k: True))
        self.assertIsNone(got["r2"])
        self.assertTrue(got["r2_unavailable_reason"])

    def test_selection_uses_validation_not_test_and_breaks_ties_by_simplicity(self):
        def entry(val, test):
            return {"validation": {"overall": {"mae": val}}, "test": {"overall": {"mae": test}}}
        metrics = {"reference": entry(10.0, 1.0), "ridge_alpha_1": entry(9.0, 99.0),
                   "hist_gradient_boosting": entry(8.0, 500.0)}
        self.assertEqual(choose_model(metrics, self.config), "hist_gradient_boosting")
        tie = {"reference": entry(5.0, 9.0), "ridge_alpha_1": entry(5.0 - 1e-12, 1.0)}
        self.assertEqual(choose_model(tie, self.config), "reference")
        validation = {n: v["validation"]["mae"] for n, v in self.result["comparison"].items()}
        self.assertEqual(validation[self.result["selected_model"]], min(validation.values()))

    def test_partitions_are_disjoint_and_exports_cover_all_evaluated_rows(self):
        predictions = pq.read_table(self.out / "predictions.parquet").to_pandas()
        expected = self.frame[self.frame["partition"] != "train"]
        self.assertEqual(len(predictions), len(expected))
        self.assertTrue(predictions["row_id"].is_unique)
        self.assertEqual(set(predictions["partition"]), {"validation", "test", "stress"})
        self.assertTrue(np.isfinite(predictions[["actual", "prediction"]]).all().all())
        self.assertTrue((predictions["prediction"] >= 0).all() and (predictions["actual"] >= 0).all())
        self.assertEqual(set(predictions["model_id"]), {self.result["model_id"]})
        self.assertEqual(set(predictions["source_sha256"]), {"a" * 64})

    def test_artifacts_share_model_identity_and_examples_are_deterministic(self):
        model_sha = hashlib.sha256((self.out / "model.joblib").read_bytes()).hexdigest()
        metrics = json.loads((self.out / "metrics.json").read_text(encoding="utf-8"))
        examples = json.loads((self.out / "examples.json").read_text(encoding="utf-8"))
        self.assertEqual(metrics["model_sha256"], model_sha)
        self.assertEqual(examples["model_id"], model_sha)
        self.assertLessEqual(len(examples["rows"]), 200)
        again = train_regression(self.config, self.path, self.report, self.root / "again")
        repeated = json.loads((self.root / "again/examples.json").read_text(encoding="utf-8"))
        self.assertEqual([r["row_id"] for r in repeated["rows"]], [r["row_id"] for r in examples["rows"]])
        self.assertEqual(again["selected_model"], self.result["selected_model"])

    def test_type_without_train_rows_still_evaluates_with_global_median(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, report, _ = synthetic_d1(tmp, drop_type="DEBIT")
            result = train_regression(RegressionConfig(max_train_rows=None), path, report, Path(tmp) / "m")
            self.assertGreater(result["metrics"]["reference"]["test"]["by_type"]["DEBIT"]["n"], 0)

    def test_mismatched_dataset_hash_is_rejected(self):
        bad = self.root / "bad.json"
        bad.write_text(json.dumps({"source": {"sha256": "a" * 64}, "output": {"sha256": "b" * 64}}), encoding="utf-8")
        with self.assertRaises(ValueError):
            train_regression(self.config, self.path, bad, self.root / "x")


if __name__ == "__main__":
    unittest.main()
