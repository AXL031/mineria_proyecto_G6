import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from analytics_fixtures import dataset_fixture, regression_config
from bankshield.analytics_contract import strict_json, write_json_atomic
from bankshield.features.regression import build_regression_features
from bankshield.models.regression import MetricAccumulator, MedianByType, sample_train, select_model, train
from bankshield.services.regression import RegressionScorer


class RegressionTrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.tmp.name)
        cls.dataset = dataset_fixture(cls.directory / "data")
        cls.output = cls.directory / "model"
        cls.report = train(cls.dataset, regression_config(), cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_reservoir_is_deterministic_chunk_independent_and_only_train(self):
        first, info = sample_train(self.dataset, 10, 42)
        self.dataset.chunksize = 11
        second, other = sample_train(self.dataset, 10, 42)
        pd.testing.assert_frame_equal(first, second)
        self.assertEqual(info, other)
        all_train = pd.concat(list(self.dataset.batches("train")))
        self.assertTrue(first.row_id.isin(all_train.row_id).all())

    def test_reference_medians_and_unobserved_valid_type(self):
        X = pd.DataFrame({"type": ["TRANSFER", "TRANSFER", "PAYMENT"]})
        model = MedianByType().fit(X, [10, 30, 90])
        np.testing.assert_array_equal(model.predict(pd.DataFrame({"type": ["TRANSFER", "CASH_IN"]})), [20, 30])

    def test_metrics_match_manual_calculation_and_null_r2(self):
        accumulator = MetricAccumulator()
        accumulator.add([1, 2], [2, 2])
        accumulator.add([3], [2])
        result = accumulator.result()
        self.assertAlmostEqual(result["mae"], 2 / 3)
        self.assertAlmostEqual(result["rmse"], np.sqrt(2 / 3))
        self.assertEqual(result["r2"], 0)
        self.assertEqual(result["mean_bias"], 0)
        constant = MetricAccumulator()
        constant.add([2, 2], [1, 1])
        self.assertIsNone(constant.result()["r2"])
        self.assertEqual(constant.result()["r2_undefined_reason"], "constant_target")

    def test_selection_only_uses_validation_and_prefers_reference_on_ties(self):
        values = {name: {"overall": {"mae": value}} for name, value in (
            ("median_by_type", 10), ("ridge_alpha_1", 10), ("ridge_alpha_10", 11), ("hist_gradient_boosting", 12))}
        self.assertEqual(select_model(values), "median_by_type")
        values["hist_gradient_boosting"]["overall"]["mae"] = 9
        self.assertEqual(select_model(values), "hist_gradient_boosting")

    def test_loaded_pipeline_reproduces_exported_predictions(self):
        import pyarrow.parquet as pq
        scorer = RegressionScorer(self.output / "model.joblib")
        exported = pq.read_table(self.output / "predictions.parquet").to_pandas()
        self.assertEqual(len(exported), sum(self.dataset.report["partitions"][p]["rows"] for p in ("validation", "test", "stress")))
        self.assertFalse(exported.row_id.duplicated().any())
        self.assertNotIn("train", set(exported.partition))
        inputs = pd.concat(list(self.dataset.batches())).set_index("row_id").loc[exported.row_id]
        predicted = [row["prediction"] for row in scorer.score(inputs)]
        np.testing.assert_allclose(predicted, exported.prediction)

    def test_transformer_learns_only_sampled_train(self):
        # StandardScaler de Ridge conserva exactamente la media del train muestreado.
        from bankshield.models.regression import candidates
        sampled, _ = sample_train(self.dataset, 10, 42)
        features = build_regression_features(sampled)
        model = candidates()["ridge_alpha_1"].fit(features, sampled.amount)
        scaler = model.regressor_.named_steps["features"].named_transformers_["numeric"]
        np.testing.assert_allclose(scaler.mean_, features.iloc[:, 1:].mean().to_numpy())

    def test_metrics_tampering_and_examples_identity_are_rejected(self):
        path = self.output / "metrics.json"
        try:
            altered = copy.deepcopy(self.report)
            altered["evaluation"]["test"]["median_by_type"]["overall"]["mae"] += 1
            write_json_atomic(path, altered)
            with self.assertRaisesRegex(ValueError, "Métricas distintas"):
                RegressionScorer(self.output / "model.joblib")
        finally:
            write_json_atomic(path, self.report)
        scorer = RegressionScorer(self.output / "model.joblib")
        examples_path = self.output / "examples.json"
        original = examples_path.read_bytes()
        try:
            examples = strict_json(examples_path)
            examples["model_id"] = "0" * 64
            write_json_atomic(examples_path, examples)
            with self.assertRaisesRegex(ValueError, "Ejemplos incompatibles"):
                scorer.examples()
        finally:
            examples_path.write_bytes(original)
