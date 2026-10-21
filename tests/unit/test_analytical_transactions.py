"""Pruebas de la tabla analítica compartida D1 (TAC-01)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from bankshield.ingestion.paysim_profile import TRANSACTION_TYPES
from bankshield.transforms.analytical_transactions import (
    ANALYTICS_COLUMNS,
    apply_bins,
    assign_partitions,
    build_analytics_transactions,
    build_fixture,
    canonical_sha256,
    fit_bins,
    write_fixture_silver,
)
from bankshield.transforms.silver_transactions import SILVER_SCHEMA, file_sha256

STEPS = (1, 100, 323, 324, 378, 379, 500, 718, 719, 743)
QUANTILES = (1.0 / 3.0, 2.0 / 3.0)


def make_frame(perturb_test=False, flip_labels=False):
    """Fixture de Silver válido que cubre las cuatro particiones."""
    types = sorted(TRANSACTION_TYPES)
    rows = []
    for index, step in enumerate(STEPS):
        for offset in range(4):
            amount = float((index * 10 + offset + 1) * 137)
            if perturb_test and step > 378:
                amount *= 3.0
            old_balance = amount + 5000.0 * (offset + 1)
            label = 1 if (index + offset) % 5 == 0 else 0
            if flip_labels:
                label = 1 - label
            rows.append(
                {
                    "step": step,
                    "type": types[(index + offset) % len(types)],
                    "amount": amount,
                    "nameOrig": f"C{index:02d}{offset}",
                    "oldbalanceOrg": old_balance,
                    "newbalanceOrig": old_balance - amount,
                    "nameDest": f"M{index:02d}{offset}",
                    "oldbalanceDest": 0.0,
                    "newbalanceDest": amount,
                    "isFraud": label,
                    "isFlaggedFraud": 0,
                }
            )
    return pd.DataFrame(rows)


def write_silver(directory: Path, frame: pd.DataFrame, name: str = "silver.parquet") -> Path:
    path = directory / name
    table = pa.Table.from_pandas(frame, schema=SILVER_SCHEMA, preserve_index=False)
    pq.write_table(table, path, compression="snappy")
    return path


def write_quality(path: Path, silver_path: Path, **overrides) -> Path:
    payload = {
        "schema_version": 1,
        "scope": "complete_file",
        "counts": {"bronze_rows": 100, "silver_rows": 100, "rejected_rows": 0},
        "duplicates": {"exact_duplicate_rows": 0, "policy": "kept"},
        "output": {"sha256": file_sha256(silver_path)},
        "quality_checks": {
            "expected_header": True,
            "source_sha256_matches": True,
            "no_rejected_rows": True,
            "no_exact_duplicate_rows": True,
            "steps_are_contiguous": True,
        },
    }
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(payload.get(key), dict):
            payload[key] = {**payload[key], **value}
        else:
            payload[key] = value
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


class BinTests(unittest.TestCase):
    def test_fit_bins_keeps_only_interior_edges(self):
        spec = fit_bins(np.array([1.0, 2.0, 3.0, 100.0]), QUANTILES)

        self.assertEqual(len(spec["interior_edges"]), 2)
        self.assertEqual(spec["labels"], ["b0", "b1", "b2"])
        self.assertTrue(all(1.0 < edge < 100.0 for edge in spec["interior_edges"]))

    def test_constant_values_collapse_to_single_bin(self):
        spec = fit_bins(np.full(10, 7.5), QUANTILES)

        self.assertEqual(spec["interior_edges"], [])
        self.assertEqual(spec["labels"], ["b0"])
        self.assertEqual(spec["train_min"], 7.5)
        self.assertEqual(spec["train_max"], 7.5)

    def test_repeated_quantiles_collapse(self):
        values = np.array([1.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 3.0])
        spec = fit_bins(values, QUANTILES)

        self.assertEqual(spec["interior_edges"], [2.0])
        self.assertEqual(spec["labels"], ["b0", "b1"])

    def test_zero_goes_to_first_bin_and_high_values_to_last(self):
        spec = fit_bins(np.array([0.0, 10.0, 20.0, 30.0]), QUANTILES)
        edges = spec["interior_edges"]
        labels = spec["labels"]

        result = apply_bins(np.array([0.0, edges[0], edges[-1] + 1e9]), edges, labels)

        self.assertEqual(result[0], "b0")
        self.assertEqual(result[1], "b0")
        self.assertEqual(result[2], labels[-1])

    def test_intervals_are_closed_on_the_right(self):
        edges = [10.0, 20.0]
        labels = ["b0", "b1", "b2"]

        result = apply_bins(np.array([9.999, 10.0, 10.001, 20.0, 20.001]), edges, labels)

        self.assertEqual(
            list(result), ["b0", "b0", "b1", "b1", "b2"]
        )

    def test_empty_train_values_are_rejected(self):
        with self.assertRaises(ValueError):
            fit_bins(np.array([], dtype="float64"), QUANTILES)


class PartitionTests(unittest.TestCase):
    def test_boundaries(self):
        steps = np.array([1, 323, 324, 378, 379, 718, 719, 743])
        result = assign_partitions(steps, 323, 378, 718)

        self.assertEqual(
            list(result),
            [
                "train",
                "train",
                "validation",
                "validation",
                "test",
                "test",
                "stress",
                "stress",
            ],
        )


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.frame = make_frame()
        self.silver = write_silver(self.directory, self.frame)
        self.quality = write_quality(self.directory / "quality.json", self.silver)

    def tearDown(self):
        self.temporary.cleanup()

    def build(self, **kwargs):
        output = kwargs.pop("output_path", self.directory / "analytics.parquet")
        silver = kwargs.pop("input_path", self.silver)
        options = {
            "dataset_report_path": self.directory / "dataset.json",
            "discretization_report_path": self.directory / "discretization.json",
            "silver_quality_path": self.quality,
            "chunksize": 3,
            "base_dir": self.directory,
        }
        options.update(kwargs)
        return build_analytics_transactions(silver, output, **options), output

    def test_output_schema_and_partitions(self):
        report, output = self.build()
        result = pd.read_parquet(output)

        self.assertEqual(list(result.columns), list(ANALYTICS_COLUMNS))
        self.assertEqual(len(result), len(self.frame))
        self.assertEqual(sorted(result["partition"].unique()), sorted(report["partitions"]))
        self.assertEqual(report["counts"]["rows_excluded"], 0)
        self.assertTrue(all(report["quality_checks"].values()))

    def test_row_id_is_ordinal_and_contiguous(self):
        report, output = self.build()
        result = pd.read_parquet(output)

        self.assertEqual(result["row_id"].tolist(), list(range(1, len(self.frame) + 1)))
        self.assertEqual(result["row_id"].nunique(), len(self.frame))
        self.assertEqual(report["quality_checks"]["row_ids_contiguous"], True)

    def test_partition_boundaries_in_output(self):
        _, output = self.build()
        result = pd.read_parquet(output)
        grouped = result.groupby("partition")["step"].agg(["min", "max"]).to_dict("index")

        self.assertEqual(grouped["train"], {"min": 1, "max": 323})
        self.assertEqual(grouped["validation"], {"min": 324, "max": 378})
        self.assertEqual(grouped["test"], {"min": 379, "max": 718})
        self.assertEqual(grouped["stress"], {"min": 719, "max": 743})

    def test_changing_test_and_stress_does_not_change_bins(self):
        report, output = self.build()
        perturbed_silver = write_silver(
            self.directory, make_frame(perturb_test=True), "silver_perturbed.parquet"
        )
        quality = write_quality(self.directory / "quality_perturbed.json", perturbed_silver)
        perturbed, perturbed_output = self.build(
            input_path=perturbed_silver,
            silver_quality_path=quality,
            output_path=self.directory / "perturbed.parquet",
        )

        for column in ("amount", "oldbalanceOrg"):
            self.assertEqual(
                report["discretization"]["columns"][column]["interior_edges"],
                perturbed["discretization"]["columns"][column]["interior_edges"],
            )
        train_a = pd.read_parquet(output).query("partition == 'train'").reset_index(drop=True)
        train_b = (
            pd.read_parquet(perturbed_output)
            .query("partition == 'train'")
            .reset_index(drop=True)
        )
        pd.testing.assert_frame_equal(train_a, train_b)

    def test_changing_labels_does_not_change_partitions_or_bins(self):
        report, output = self.build()
        flipped_silver = write_silver(
            self.directory, make_frame(flip_labels=True), "silver_flipped.parquet"
        )
        quality = write_quality(self.directory / "quality_flipped.json", flipped_silver)
        flipped, flipped_output = self.build(
            input_path=flipped_silver,
            silver_quality_path=quality,
            output_path=self.directory / "flipped.parquet",
        )

        self.assertEqual(
            report["discretization"]["sha256"], flipped["discretization"]["sha256"]
        )
        original = pd.read_parquet(output)
        changed = pd.read_parquet(flipped_output)
        pd.testing.assert_series_equal(original["partition"], changed["partition"])
        pd.testing.assert_series_equal(original["amount_bin"], changed["amount_bin"])
        pd.testing.assert_series_equal(
            original["origin_balance_bin"], changed["origin_balance_bin"]
        )
        self.assertFalse(original["isFraud"].equals(changed["isFraud"]))

    def test_chunk_size_does_not_change_results(self):
        _, small = self.build(chunksize=3, output_path=self.directory / "small.parquet")
        _, large = self.build(chunksize=1000, output_path=self.directory / "large.parquet")

        pd.testing.assert_frame_equal(pd.read_parquet(small), pd.read_parquet(large))

    def test_report_links_hashes_and_reports(self):
        report, output = self.build()
        dataset_json = json.loads((self.directory / "dataset.json").read_text(encoding="utf-8"))
        bins_json = json.loads(
            (self.directory / "discretization.json").read_text(encoding="utf-8")
        )

        self.assertEqual(report, dataset_json)
        self.assertEqual(report["source"]["sha256"], file_sha256(self.silver))
        self.assertEqual(report["output"]["sha256"], file_sha256(output))
        self.assertEqual(bins_json["dataset_sha256"], report["output"]["sha256"])
        self.assertEqual(
            bins_json["discretization_sha256"], report["discretization"]["sha256"]
        )
        self.assertEqual(bins_json["source_sha256"], report["source"]["sha256"])
        self.assertEqual(len(report["output"]["schema_sha256"]), 64)
        self.assertEqual(report["config"]["partitions"]["stress"], [719, 743])

    def test_missing_quality_report_is_rejected(self):
        with self.assertRaises(ValueError):
            build_analytics_transactions(
                self.silver,
                self.directory / "no-quality.parquet",
                silver_quality_path=self.directory / "missing.json",
            )

    def test_failed_quality_checks_are_rejected(self):
        quality = write_quality(
            self.directory / "bad_quality.json",
            self.silver,
            quality_checks={"no_rejected_rows": False},
        )
        with self.assertRaises(ValueError):
            self.build(silver_quality_path=quality)

    def test_quality_report_with_other_fingerprint_is_rejected(self):
        quality = write_quality(
            self.directory / "wrong_hash.json",
            self.silver,
            output={"sha256": "0" * 64},
        )
        with self.assertRaises(ValueError):
            self.build(silver_quality_path=quality)

    def test_invalid_step_aborts_without_publishing(self):
        frame = make_frame()
        frame.loc[0, "step"] = 744
        silver = write_silver(self.directory, frame)
        quality = write_quality(self.directory / "q.json", silver)
        output = self.directory / "invalid-step.parquet"

        with self.assertRaises(ValueError):
            self.build(silver_quality_path=quality, output_path=output)

        self.assertFalse(output.exists())

    def test_invalid_row_aborts_without_publishing(self):
        frame = make_frame()
        frame.loc[2, "amount"] = -1.0
        silver = write_silver(self.directory, frame)
        quality = write_quality(self.directory / "q.json", silver)
        output = self.directory / "invalid-amount.parquet"

        with self.assertRaises(ValueError):
            self.build(silver_quality_path=quality, output_path=output)

        self.assertFalse(output.exists())

    def test_unknown_type_is_rejected(self):
        frame = make_frame()
        frame.loc[1, "type"] = "REFUND"
        silver = write_silver(self.directory, frame)
        quality = write_quality(self.directory / "q.json", silver)

        with self.assertRaises(ValueError):
            self.build(silver_quality_path=quality)

    def test_constant_train_amounts_use_single_bin(self):
        frame = make_frame()
        train_mask = frame["step"] <= 323
        frame.loc[train_mask, "amount"] = 1000.0
        silver = write_silver(self.directory, frame)
        quality = write_quality(self.directory / "q.json", silver)
        report, output = self.build(
            silver_quality_path=quality, output_path=self.directory / "constant.parquet"
        )

        spec = report["discretization"]["columns"]["amount"]
        self.assertEqual(spec["interior_edges"], [])
        self.assertEqual(spec["labels"], ["b0"])
        self.assertEqual(
            pd.read_parquet(output)["amount_bin"].unique().tolist(), ["b0"]
        )


class FixtureTests(unittest.TestCase):
    def test_fixture_matches_final_schema(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name)
            report = build_fixture(directory)

            result = pd.read_parquet(directory / "analytics_transactions.parquet")
            self.assertEqual(list(result.columns), list(ANALYTICS_COLUMNS))
            self.assertEqual(report["counts"]["rows_out"], len(result))
            self.assertTrue((directory / "dataset.json").is_file())
            self.assertTrue((directory / "discretization.json").is_file())
            self.assertEqual(
                sorted(result["partition"].unique()),
                ["stress", "test", "train", "validation"],
            )

    def test_fixture_silver_is_contract_valid(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "silver.parquet"
            frame = write_fixture_silver(path)

            stored = pd.read_parquet(path)
            self.assertEqual(pq.ParquetFile(path).schema.names, list(SILVER_SCHEMA.names))
            self.assertEqual(len(stored), len(frame))
            self.assertTrue((stored["amount"] >= 0).all())
            self.assertTrue(stored["type"].isin(TRANSACTION_TYPES).all())

    def test_canonical_hash_is_stable(self):
        payload = {"b": 1, "a": [1, 2]}
        self.assertEqual(canonical_sha256(payload), canonical_sha256({"a": [1, 2], "b": 1}))


if __name__ == "__main__":
    unittest.main()
