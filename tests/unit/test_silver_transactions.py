import csv
import hashlib
import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pyarrow.parquet as pq

from bankshield.ingestion.paysim_profile import FIELDS
from bankshield.transforms.silver_transactions import build_silver


def transaction(**changes):
    row = dict(zip(FIELDS, ["1", "TRANSFER", "100", "C1", "200", "100", "C2", "0", "100", "1", "0"]))
    row.update(changes)
    return row


class SilverTransactionsTests(unittest.TestCase):
    def setUp(self):
        parent = Path(__file__).resolve().parents[2] / "artifacts/reports/silver-tests"
        parent.mkdir(parents=True, exist_ok=True)
        self.workdir = parent / uuid.uuid4().hex
        self.workdir.mkdir()
        self.addCleanup(shutil.rmtree, self.workdir, True)
        self.input = self.workdir / "paysim.csv"
        self.output = self.workdir / "silver.parquet"
        self.quality_json = self.workdir / "quality.json"
        self.quality_markdown = self.workdir / "quality.md"

    def write_csv(self, rows):
        with self.input.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def build(self, **kwargs):
        return build_silver(
            self.input,
            self.output,
            quality_json=self.quality_json,
            quality_markdown=self.quality_markdown,
            **kwargs,
        )

    def test_valid_rows_are_written_with_declared_types(self):
        self.write_csv([transaction(), transaction(step="2", isFraud="0", type="PAYMENT")])
        report = self.build()
        self.assertEqual(report["counts"]["bronze_rows"], 2)
        self.assertEqual(report["counts"]["silver_rows"], 2)
        self.assertEqual(report["counts"]["rejected_rows"], 0)
        self.assertEqual(report["scope"], "complete_file")

        table = pq.read_table(self.output)
        self.assertEqual(table.column_names, list(FIELDS))
        schema = table.schema
        self.assertEqual(str(schema.field("step").type), "int64")
        self.assertEqual(str(schema.field("isFraud").type), "int8")
        self.assertEqual(str(schema.field("amount").type), "double")
        self.assertEqual(str(schema.field("type").type), "string")
        self.assertEqual(table.num_rows, 2)

        self.assertEqual(report["accounts"]["unique_origins"], 1)
        self.assertEqual(report["accounts"]["unique_destinations"], 1)
        self.assertEqual(report["accounts"]["unique_accounts"], 2)
        self.assertTrue(report["quality_checks"]["no_rejected_rows"])
        self.assertTrue(report["quality_checks"]["steps_are_contiguous"])
        self.assertIsNone(report["quality_checks"]["source_sha256_matches"])

    def test_reports_are_written_and_serializable(self):
        self.write_csv([transaction()])
        self.build()
        stored = json.loads(self.quality_json.read_text(encoding="utf-8"))
        self.assertEqual(stored["counts"]["silver_rows"], 1)
        markdown = self.quality_markdown.read_text(encoding="utf-8")
        self.assertIn("# Reporte de calidad", markdown)
        self.assertIn("| Filas en Silver | 1 |", markdown)

    def test_invalid_rows_are_rejected_and_registered_by_cause(self):
        self.write_csv([
            transaction(),
            transaction(type="BOGUS"),
            transaction(amount="-5"),
            transaction(isFraud="2"),
            transaction(nameOrig=""),
            transaction(step="1.5"),
        ])
        report = self.build()
        self.assertEqual(report["counts"]["bronze_rows"], 6)
        self.assertEqual(report["counts"]["silver_rows"], 1)
        self.assertEqual(report["counts"]["rejected_rows"], 5)
        issues = report["counts"]["rejected_by_issue"]
        self.assertEqual(issues["invalid:type"], 1)
        self.assertEqual(issues["negative:amount"], 1)
        self.assertEqual(issues["invalid:isFraud"], 1)
        self.assertEqual(issues["missing:nameOrig"], 1)
        self.assertEqual(issues["invalid:step"], 1)
        self.assertFalse(report["quality_checks"]["no_rejected_rows"])
        self.assertEqual(pq.read_table(self.output).num_rows, 1)

    def test_duplicates_are_reported_and_kept(self):
        self.write_csv([transaction(), transaction(), transaction(step="9")])
        report = self.build()
        self.assertEqual(report["counts"]["silver_rows"], 3)
        self.assertEqual(report["duplicates"]["exact_duplicate_rows"], 1)
        self.assertEqual(report["duplicates"]["policy"], "kept")
        self.assertFalse(report["quality_checks"]["no_exact_duplicate_rows"])
        self.assertEqual(pq.read_table(self.output).num_rows, 3)

    def test_lfs_pointer_and_unexpected_header_fail(self):
        self.input.write_text(
            "version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 123\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "Git LFS"):
            self.build()
        unexpected = ",".join(list(FIELDS) + ["extra"])
        self.input.write_text(unexpected + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Cabecera PaySim inesperada"):
            self.build()
        self.assertFalse(self.output.exists())

    def test_expected_sha256_is_verified(self):
        self.write_csv([transaction()])
        digest = hashlib.sha256(self.input.read_bytes()).hexdigest().upper()
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.build(expected_sha256="0" * 64)
        report = self.build(expected_sha256=digest)
        self.assertTrue(report["quality_checks"]["source_sha256_matches"])
        self.assertEqual(report["source"]["sha256"], digest)

    def test_limit_labels_the_report_as_a_sample(self):
        self.write_csv([transaction(), transaction(step="2"), transaction(step="3")])
        report = self.build(limit=1)
        self.assertEqual(report["scope"], "first_rows_sample")
        self.assertEqual(report["counts"]["bronze_rows"], 1)
        self.assertEqual(report["counts"]["silver_rows"], 1)
        self.assertEqual(report["row_limit"], 1)
        with self.assertRaises(ValueError):
            self.build(limit=0)

    def test_all_invalid_input_fails_without_leaving_output(self):
        self.write_csv([transaction(amount="NaN")])
        with self.assertRaisesRegex(ValueError, "sin registros válidos"):
            self.build()
        self.assertFalse(self.output.exists())
        self.assertFalse(self.output.with_suffix(".parquet.tmp").exists())


if __name__ == "__main__":
    unittest.main()
