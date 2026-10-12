"""Comprueba las asociaciones sin etiquetas en antecedentes y casos sin soporte."""

import unittest

import numpy as np
import pandas as pd

from bankshield.features.fraud_patterns import RULES, rule_masks, summarize_rules


class FraudPatternTests(unittest.TestCase):
    def test_rules_depend_only_on_pre_transaction_information(self):
        frame = pd.DataFrame([
            {"type": "TRANSFER", "amount": 10, "oldbalanceOrg": 10, "isFraud": 1},
            {"type": "CASH_OUT", "amount": 20, "oldbalanceOrg": 10, "isFraud": 0},
            {"type": "PAYMENT", "amount": 0, "oldbalanceOrg": 0, "isFraud": 0},
        ])
        masks = rule_masks(frame)
        changed = frame.assign(isFraud=0, isFlaggedFraud=1, newbalanceOrig=999)
        for key in RULES:
            np.testing.assert_array_equal(masks[key], rule_masks(changed)[key])
        self.assertEqual(masks["positive_amount_equals_balance"].tolist(), [True, False, False])
        self.assertEqual(masks["amount_exceeds_balance"].tolist(), [False, True, False])

    def test_support_confidence_lift_and_absence_are_distinct(self):
        counts = {key: [0, 0] for key in RULES}
        counts["transfer"] = [20, 5]
        report = summarize_rules(100, 10, counts)
        first = report["rules"][0]
        self.assertEqual(first["support"], 0.2)
        self.assertEqual(first["confidence"], 0.25)
        self.assertEqual(first["lift"], 2.5)
        self.assertEqual(first["fraud_coverage"], 0.5)
        self.assertIsNone(report["rules"][1]["confidence"])
        self.assertIsNone(report["rules"][1]["lift"])


if __name__ == "__main__":
    unittest.main()
