import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import pandas as pd

from bankshield.features.segments import BEHAVIOR_COLUMNS, build_account_features
from bankshield.models.segments import (
    CLUSTER_COLUMNS,
    baseline_segments,
    prepare_matrix,
    profile_segments,
    segment_accounts,
)


def sample_transactions():
    rows = []
    groups = {0: (10.0, 10), 1: (1_000.0, 4), 2: (100_000.0, 1)}
    for group, (amount, n_senders) in groups.items():
        for i in range(20):
            account = f"D{group}_{i}"
            for j in range(10):
                sender = f"S{group}_{i}_{j % n_senders}"
                rows.append(
                    {
                        "nameDest": account,
                        "nameOrig": sender,
                        "type": "CASH_IN" if group == 0 else ("TRANSFER" if group == 1 else "CASH_OUT"),
                        "amount": amount,
                        "step": (i * 10 + j) % 24,
                        "isFraud": 1 if group == 2 and j < 2 else 0,
                    }
                )
    rows.append(
        {
            "nameDest": "RARE",
            "nameOrig": "S0",
            "type": "TRANSFER",
            "amount": 5.0,
            "step": 1,
            "isFraud": 0,
        }
    )
    return pd.DataFrame(rows)


class AccountFeatureTests(unittest.TestCase):
    def test_filters_and_aggregates_destinations(self):
        features = build_account_features(sample_transactions(), min_transactions=10)

        self.assertEqual(features.columns.tolist(), ["account", *BEHAVIOR_COLUMNS])
        self.assertEqual(len(features), 60)
        self.assertNotIn("RARE", set(features["account"]))
        self.assertTrue((features["n_received"] == 10).all())

    def test_behavior_metrics(self):
        features = build_account_features(sample_transactions(), min_transactions=10)
        row = features.loc[features["account"] == "D0_0"].iloc[0]

        self.assertEqual(row["distinct_senders"], 10)
        self.assertAlmostEqual(row["sender_concentration"], 0.0)
        self.assertEqual(row["n_sent"], 0)
        self.assertAlmostEqual(row["net_flow"], 100.0)

        large = features.loc[features["account"] == "D2_0"].iloc[0]
        self.assertEqual(large["distinct_senders"], 1)
        self.assertAlmostEqual(large["fraud_rate_received"], 0.2)

    def test_rejects_invalid_input(self):
        with self.assertRaisesRegex(ValueError, "Faltan columnas"):
            build_account_features(pd.DataFrame({"nameDest": ["A"]}))
        with self.assertRaisesRegex(ValueError, "vacío"):
            build_account_features(
                pd.DataFrame(
                    columns=[
                        "nameDest", "nameOrig", "type", "amount", "step", "isFraud"
                    ]
                )
            )
        bad_amount = pd.DataFrame(
            {
                "nameDest": ["A"],
                "nameOrig": ["B"],
                "type": "TRANSFER",
                "amount": [-1.0],
                "step": [1],
                "isFraud": [0],
            }
        )
        with self.assertRaisesRegex(ValueError, "no negativo"):
            build_account_features(bad_amount)


class SegmentationModelTests(unittest.TestCase):
    def setUp(self):
        self.features = build_account_features(sample_transactions(), min_transactions=10)

    def test_prepare_matrix_is_finite(self):
        matrix = prepare_matrix(self.features)
        self.assertEqual(matrix.shape, (len(self.features), len(CLUSTER_COLUMNS)))
        self.assertTrue(np.isfinite(matrix).all())

    def test_baseline_segments_partition(self):
        labels = baseline_segments(self.features, 3)
        self.assertEqual(len(labels), len(self.features))
        self.assertEqual(sorted(set(labels.tolist())), [0, 1, 2])

    def test_segment_accounts_reports_metrics_and_profiles(self):
        result = segment_accounts(self.features, k_range=range(2, 6), seed=7)

        self.assertEqual(len(result["labels"]), len(self.features))
        self.assertIn(result["chosen_k"], [2, 3, 4, 5])
        self.assertEqual(
            int(result["profiles"]["size"].sum()), len(self.features)
        )
        self.assertEqual(
            set(result["silhouette_by_k"]), {2, 3, 4, 5}
        )
        self.assertEqual(len(result["stability_ari"]), 3)

    def test_profiles_match_labels(self):
        labels = np.array([0, 1] * (len(self.features) // 2))
        profiles = profile_segments(self.features, labels)
        self.assertEqual(int(profiles["size"].sum()), len(self.features))
        self.assertEqual(profiles["segment"].tolist(), [0, 1])


if __name__ == "__main__":
    unittest.main()
