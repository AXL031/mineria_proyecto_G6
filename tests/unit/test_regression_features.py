import unittest
import numpy as np
import pandas as pd

from bankshield.features.regression import FEATURES, build_regression_features


class RegressionFeatureTests(unittest.TestCase):
    def test_target_bins_labels_ids_and_future_balances_do_not_change_features(self):
        frame = pd.DataFrame({"type": ["TRANSFER", "PAYMENT"], "oldbalanceOrg": [0., 20.],
                              "amount": [100., 200.], "amount_bin": ["b0", "b1"], "isFraud": [1, 0]})
        changed = frame.assign(amount=9999, amount_bin="b2", isFraud=0, row_id=999,
                               step=743, newbalanceOrig=123)
        pd.testing.assert_frame_equal(build_regression_features(frame), build_regression_features(changed))
        self.assertEqual(tuple(build_regression_features(frame).columns), FEATURES)
        self.assertEqual(build_regression_features(frame).zero_origin_balance.tolist(), [1, 0])

    def test_invalid_inputs(self):
        for balance in (-1, float("nan"), float("inf"), True):
            with self.subTest(balance=balance), self.assertRaises(ValueError):
                build_regression_features([{"type": "TRANSFER", "oldbalanceOrg": balance}])
        with self.assertRaises(ValueError):
            build_regression_features([{"type": "UNKNOWN", "oldbalanceOrg": 0.}])
