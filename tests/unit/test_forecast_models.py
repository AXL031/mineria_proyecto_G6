import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from bankshield.models.forecast import naive_forecast, seasonal_naive_forecast


class ForecastBaselineTests(unittest.TestCase):
    def test_naive_repeats_the_last_observation(self):
        prediction = naive_forecast([10.0, 12.0, 9.0], horizon=4)

        np.testing.assert_array_equal(prediction, [9.0, 9.0, 9.0, 9.0])

    def test_seasonal_naive_uses_the_value_observed_24_steps_before(self):
        history = np.arange(1.0, 49.0)

        prediction = seasonal_naive_forecast(
            history,
            horizon=24,
            seasonal_period=24,
        )

        np.testing.assert_array_equal(prediction, np.arange(25.0, 49.0))

    def test_seasonal_naive_repeats_the_last_cycle_for_longer_horizons(self):
        prediction = seasonal_naive_forecast(
            [10.0, 20.0, 30.0, 40.0],
            horizon=5,
            seasonal_period=2,
        )

        np.testing.assert_array_equal(prediction, [30.0, 40.0, 30.0, 40.0, 30.0])

    def test_models_do_not_modify_the_history(self):
        history = np.array([1.0, 2.0, 3.0, 4.0])
        original = history.copy()

        naive_forecast(history, horizon=2)
        seasonal_naive_forecast(history, horizon=2, seasonal_period=2)

        np.testing.assert_array_equal(history, original)

    def test_rejects_invalid_history_and_parameters(self):
        invalid_calls = [
            lambda: naive_forecast([], horizon=1),
            lambda: naive_forecast([1.0, np.nan], horizon=1),
            lambda: naive_forecast([1.0], horizon=0),
            lambda: seasonal_naive_forecast([1.0], horizon=1, seasonal_period=2),
            lambda: seasonal_naive_forecast([1.0], horizon=1, seasonal_period=0),
        ]

        for call in invalid_calls:
            with self.subTest(call=call):
                with self.assertRaises(ValueError):
                    call()


if __name__ == "__main__":
    unittest.main()
