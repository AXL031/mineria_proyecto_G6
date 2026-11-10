"""Variables de regresión: sin fuga del objetivo y validación de entradas."""

import unittest

import numpy as np
import pandas as pd

from bankshield.features.regression import (
    FEATURE_COLUMNS, build_regression_feature_frame, frame_from_dataset, validate_inputs)


class RegressionFeatureTests(unittest.TestCase):
    def test_columns_never_include_target_or_forbidden_fields(self):
        for forbidden in ("amount", "amount_bin", "isFraud", "row_id", "step", "newbalanceOrig"):
            self.assertFalse(any(forbidden in col for col in FEATURE_COLUMNS))

    def test_changing_amount_and_labels_does_not_change_matrix(self):
        base = pd.DataFrame({"type": ["TRANSFER", "CASH_OUT"], "oldbalanceOrg": [100.0, 0.0], "amount": [5.0, 6.0],
                             "amount_bin": ["b0", "b1"], "isFraud": [0, 1], "step": [1, 2], "row_id": [1, 2]})
        changed = base.assign(amount=[9e6, 1.0], amount_bin=["b2", "b2"], isFraud=[1, 0], step=[700, 5], row_id=[9, 8])
        pd.testing.assert_frame_equal(frame_from_dataset(base), frame_from_dataset(changed))

    def test_engineered_values_and_zero_balance_marker(self):
        frame = build_regression_feature_frame(["PAYMENT", "DEBIT"], [0.0, 99.0])
        self.assertEqual(frame["zero_balance"].tolist(), [1.0, 0.0])
        np.testing.assert_allclose(frame["log_oldbalance"], np.log1p([0.0, 99.0]))

    def test_invalid_inputs_are_rejected(self):
        bad = [(["NOPE"], [1.0]), (["PAYMENT"], [float("nan")]), (["PAYMENT"], [float("inf")]),
               (["PAYMENT"], [-1.0]), (["PAYMENT"], [True])]
        for types, balances in bad:
            with self.subTest(types=types, balances=balances), self.assertRaises(ValueError):
                validate_inputs(types, balances)


if __name__ == "__main__":
    unittest.main()
