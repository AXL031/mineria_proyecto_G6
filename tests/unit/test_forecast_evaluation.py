import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from bankshield.evaluation.forecast import (
    BacktestWindow,
    backtest_windows_from_config,
    calculate_forecast_metrics,
    generate_expanding_windows,
    mean_absolute_error,
    root_mean_squared_error,
    split_backtest_window,
    symmetric_mean_absolute_percentage_error,
    validate_backtest_windows,
)


class ForecastWindowTests(unittest.TestCase):
    def test_generates_the_four_configured_expanding_windows(self):
        generated = generate_expanding_windows(
            train_start_step=1,
            first_train_end_step=622,
            horizon=24,
            folds=4,
        )
        root = Path(__file__).resolve().parents[2]
        config = json.loads(
            (root / "configs" / "forecast.json").read_text(encoding="utf-8")
        )
        configured = backtest_windows_from_config(config["evaluation"])

        self.assertEqual(generated, configured)
        self.assertEqual(
            [(window.test_start_step, window.test_end_step) for window in generated],
            [(623, 646), (647, 670), (671, 694), (695, 718)],
        )
        self.assertTrue(all(window.horizon == 24 for window in generated))

    def test_rejects_temporal_leakage_and_invalid_expansion(self):
        with self.assertRaisesRegex(ValueError, "anterior"):
            BacktestWindow("W01", 1, 4, 4, 5)

        first = BacktestWindow("W01", 1, 4, 5, 6)
        invalid_next = BacktestWindow("W02", 1, 5, 6, 7)
        with self.assertRaisesRegex(ValueError, "incorporar"):
            validate_backtest_windows([first, invalid_next], expected_horizon=2)

        outside = BacktestWindow("W01", 1, 4, 5, 8)
        with self.assertRaisesRegex(ValueError, "fuera"):
            validate_backtest_windows(
                [outside],
                expected_horizon=4,
                operational_start_step=1,
                operational_end_step=7,
            )

    def test_splits_complete_series_in_temporal_order(self):
        series = pd.DataFrame(
            {"step": [6, 1, 4, 2, 5, 3, 8, 7], "value": np.arange(8)}
        )
        window = BacktestWindow("W01", 1, 4, 5, 6)

        train, test = split_backtest_window(series, window)

        self.assertEqual(train["step"].tolist(), [1, 2, 3, 4])
        self.assertEqual(test["step"].tolist(), [5, 6])
        self.assertLess(train["step"].max(), test["step"].min())

    def test_rejects_missing_or_duplicated_steps(self):
        window = BacktestWindow("W01", 1, 3, 4, 5)
        missing = pd.DataFrame({"step": [1, 3, 4, 5], "value": [1, 3, 4, 5]})
        duplicated = pd.DataFrame(
            {"step": [1, 2, 2, 3, 4, 5], "value": [1, 2, 2, 3, 4, 5]}
        )

        with self.assertRaisesRegex(ValueError, "Faltan steps"):
            split_backtest_window(missing, window)
        with self.assertRaisesRegex(ValueError, "duplicados"):
            split_backtest_window(duplicated, window)


class ForecastMetricTests(unittest.TestCase):
    def test_calculates_metrics_with_known_values(self):
        actual = [0.0, 10.0]
        predicted = [0.0, 0.0]

        self.assertEqual(mean_absolute_error(actual, predicted), 5.0)
        self.assertAlmostEqual(
            root_mean_squared_error(actual, predicted), math.sqrt(50.0)
        )
        self.assertEqual(
            symmetric_mean_absolute_percentage_error(actual, predicted), 100.0
        )
        metrics = calculate_forecast_metrics(actual, predicted)
        self.assertEqual(metrics["mae"], 5.0)
        self.assertAlmostEqual(metrics["rmse"], math.sqrt(50.0))
        self.assertEqual(metrics["smape"], 100.0)

    def test_zero_over_zero_contributes_zero_to_smape(self):
        metrics = calculate_forecast_metrics([0.0, 0.0], [0.0, 0.0])
        self.assertEqual(metrics, {"mae": 0.0, "rmse": 0.0, "smape": 0.0})

    def test_rejects_invalid_metric_inputs(self):
        invalid_pairs = [
            ([], []),
            ([1.0], [1.0, 2.0]),
            ([1.0, np.nan], [1.0, 2.0]),
            ([[1.0]], [[1.0]]),
        ]
        for actual, predicted in invalid_pairs:
            with self.subTest(actual=actual, predicted=predicted):
                with self.assertRaises(ValueError):
                    calculate_forecast_metrics(actual, predicted)


if __name__ == "__main__":
    unittest.main()
