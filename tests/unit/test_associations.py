import copy
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from analytics_fixtures import dataset_fixture, association_config
from bankshield.analytics_contract import AnalyticalDataset, strict_json, write_json_atomic
from bankshield.features.association_transactions import item_masks
from bankshield.models.associations import count_candidates, join_candidates, metrics, mine, report_identity


class MemoryDataset:
    def __init__(self, frame):
        self.frame = frame

    def batches(self, partition=None):
        frame = self.frame if partition is None else self.frame.loc[self.frame.partition.eq(partition)]
        yield frame

    def identity(self):
        return {"fixture": True}


def small_frame():
    return pd.DataFrame({"type": ["TRANSFER", "TRANSFER", "PAYMENT", "PAYMENT"] * 4,
                         "amount": [10., 10., 5., 5.] * 4, "oldbalanceOrg": [10., 20., 0., 0.] * 4,
                         "amount_bin": ["b1", "b1", "b0", "b0"] * 4,
                         "origin_balance_bin": ["b1", "b1", "b0", "b0"] * 4,
                         "isFraud": [1, 0, 0, 0] * 4,
                         "partition": [part for part in ("train", "validation", "test", "stress") for _ in range(4)]})


class AssociationTests(unittest.TestCase):
    def test_manual_support_confidence_lift_and_coverage(self):
        dataset = MemoryDataset(small_frame())
        counted = count_candidates(dataset, [("type=TRANSFER",)], "train")[("type=TRANSFER",)]
        self.assertEqual((counted["n"], counted["joint_count"], counted["antecedent_count"]), (4, 1, 2))
        self.assertEqual(counted["support"], .25)
        self.assertEqual(counted["antecedent_support"], .5)
        self.assertEqual(counted["confidence"], .5)
        self.assertEqual(counted["lift"], 2)
        self.assertEqual(counted["fraud_coverage"], 1)

    def test_no_matches_and_no_positives_are_null(self):
        m = metrics(4, 0, 0, 0)
        self.assertIsNone(m["confidence"])
        self.assertIsNone(m["lift"])
        self.assertIsNone(m["fraud_coverage"])
        self.assertIsNone(metrics(0, 0, 0, 0)["support"])

    def test_items_are_independent_of_labels_and_post_transaction_fields(self):
        frame = small_frame()
        changed = frame.assign(isFraud=1 - frame.isFraud, isFlaggedFraud=1, newbalanceOrig=999999)
        for key, mask in item_masks(frame).items():
            np.testing.assert_array_equal(mask, item_masks(changed)[key])
        self.assertFalse(any("isFraud" in key for key in item_masks(frame)))

    def test_apriori_rejects_two_values_of_one_attribute_and_prunes_subsets(self):
        self.assertEqual(join_candidates([("type=PAYMENT",), ("type=TRANSFER",)], 2), [])
        self.assertEqual(join_candidates([("a=1", "b=1"), ("a=1", "c=1")], 3), [])

    def test_test_and_stress_do_not_change_selection(self):
        frame = small_frame()
        first = mine(MemoryDataset(frame), association_config())
        changed = frame.copy()
        changed.loc[changed.partition.isin(["test", "stress"]), "isFraud"] = 1
        second = mine(MemoryDataset(changed), association_config())
        self.assertEqual([r["id"] for r in first["rules"]], [r["id"] for r in second["rules"]])
        self.assertEqual(first["search"], second["search"])
        self.assertNotEqual(first["evaluation"]["test"], second["evaluation"]["test"])

    def test_union_does_not_sum_overlapping_rules(self):
        report = mine(MemoryDataset(small_frame()), association_config())
        self.assertGreater(len(report["rules"]), 1)
        self.assertEqual(report["evaluation"]["test"]["joint_count"], 1)
        self.assertEqual(report["evaluation"]["test"]["fraud_coverage"], 1)

    def test_empty_selection_is_valid_without_relaxing_thresholds(self):
        config = {**association_config(), "min_antecedent_count": 999}
        report = mine(MemoryDataset(small_frame()), config)
        self.assertEqual(report["rules"], [])
        self.assertEqual(report["config"]["min_antecedent_count"], 999)

    def test_candidate_limit_fails_instead_of_truncating(self):
        with self.assertRaisesRegex(ValueError, "max_candidates"):
            mine(MemoryDataset(small_frame()), {**association_config(), "max_candidates": 1})

    def test_real_contract_fixture_and_chunk_independence(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset = dataset_fixture(Path(tmp))
            first = mine(dataset, association_config())
            dataset.chunksize = 17
            second = mine(dataset, association_config())
            self.assertEqual(first["analysis_id"], second["analysis_id"])

    def test_d1_rejects_altered_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset_fixture(Path(tmp))
            path = Path(tmp) / "dataset.json"
            metadata = strict_json(path)
            metadata["output"]["sha256"] = "0" * 64
            write_json_atomic(path, metadata)
            with self.assertRaisesRegex(ValueError, "huella"):
                AnalyticalDataset(Path(tmp) / "analytics_transactions.parquet", path, Path(tmp) / "discretization.json")
