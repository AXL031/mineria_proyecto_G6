import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from bankshield.ingestion.complaints_profile import FIELDS
from bankshield.transforms.silver_complaints import (
    SILVER_COLUMNS,
    build_silver_complaints,
    read_complaints_csv,
    transform_complaints,
)


def mock_complaint(**changes):
    base = {
        "date_received": "05/12/2015",
        "product": "Credit card",
        "sub_product": "",
        "issue": "Billing disputes",
        "sub_issue": "",
        "consumer_complaint_narrative": "",
        "company_public_response": "",
        "company": "Bank of America",
        "state": "CA",
        "zipcode": "90210",
        "tags": "",
        "consumer_consent_provided": "",
        "submitted_via": "Web",
        "date_sent_to_company": "05/14/2015",
        "company_response_to_consumer": "Closed with explanation",
        "timely_response": "Yes",
        "consumer_disputed?": "No",
        "complaint_id": "1",
    }
    base.update(changes)
    return base


class SilverComplaintsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def bronze(self, rows):
        path = self.root / "complaints.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        return read_complaints_csv(path), path

    def test_types_and_columns(self):
        bronze, _ = self.bronze([mock_complaint(
            complaint_id="7", tags="Older American, Servicemember", **{"consumer_disputed?": "Yes"})])
        silver, rejected, counts = transform_complaints(bronze)
        self.assertEqual(list(silver.columns), list(SILVER_COLUMNS))
        row = silver.iloc[0]
        self.assertEqual(int(row["complaint_id"]), 7)
        self.assertEqual(row["date_received"], pd.Timestamp("2015-05-12"))
        self.assertEqual(int(row["days_to_send"]), 2)
        self.assertFalse(row["sent_before_received"])
        self.assertTrue(row["is_older_american"] and row["is_servicemember"])
        self.assertTrue(row["consumer_disputed"])
        self.assertTrue(row["timely_response"])
        self.assertTrue(pd.isna(row["sub_product"]))
        self.assertEqual(len(rejected), 0)
        self.assertEqual(counts["silver_rows"], 1)

    def test_rejections_have_traceable_reasons(self):
        bronze, _ = self.bronze([
            mock_complaint(complaint_id="1"),
            mock_complaint(complaint_id=""),
            mock_complaint(complaint_id="abc"),
            mock_complaint(complaint_id="4", date_received="13/45/2015"),
            mock_complaint(complaint_id="5", date_received=""),
            mock_complaint(complaint_id="6", product=""),
        ])
        silver, rejected, counts = transform_complaints(bronze)
        self.assertEqual(len(silver), 1)
        self.assertEqual(counts["rejected_rows"], 5)
        self.assertEqual(counts["reject_reasons"], {
            "missing:complaint_id": 1, "invalid:complaint_id": 1, "invalid:date_received": 1,
            "missing:date_received": 1, "missing:product": 1})

    def test_duplicate_ids_keep_first(self):
        bronze, _ = self.bronze([
            mock_complaint(complaint_id="9", product="Mortgage"),
            mock_complaint(complaint_id="9", product="Credit card"),
        ])
        silver, _, counts = transform_complaints(bronze)
        self.assertEqual(len(silver), 1)
        self.assertEqual(silver.iloc[0]["product"], "Mortgage")
        self.assertEqual(counts["duplicate_ids_removed"], 1)
        self.assertEqual(counts["bronze_rows"], counts["silver_rows"] + counts["duplicate_ids_removed"])

    def test_anomalies_are_flagged_not_rejected(self):
        bronze, _ = self.bronze([
            mock_complaint(complaint_id="1", date_sent_to_company="05/10/2015", zipcode="123XX"),
            mock_complaint(complaint_id="2", zipcode="[9999"),
            mock_complaint(complaint_id="3", zipcode=""),
        ])
        silver, rejected, counts = transform_complaints(bronze)
        self.assertEqual(len(silver), 3)
        self.assertEqual(len(rejected), 0)
        self.assertEqual(counts["sent_before_received"], 1)
        self.assertEqual(silver["sent_before_received"].tolist(), [True, False, False])
        self.assertEqual(silver["zipcode_format_valid"].tolist(), [True, False, False])
        self.assertEqual(counts["zipcode_format_invalid"], 1)

    def test_text_columns(self):
        text = "  XXXX took {$50.00} on XX/XX/XXXX.\nPlease help  "
        bronze, _ = self.bronze([
            mock_complaint(complaint_id="1", consumer_complaint_narrative=text),
            mock_complaint(complaint_id="2", consumer_complaint_narrative=text),
            mock_complaint(complaint_id="3", consumer_complaint_narrative="Unique complaint"),
            mock_complaint(complaint_id="4"),
        ])
        silver, _, counts = transform_complaints(bronze)
        first = silver.iloc[0]
        self.assertEqual(first["narrative"], text.strip())
        self.assertEqual(first["narrative_clean"], "<censurado> took <monto> on <fecha>. please help")
        self.assertEqual(int(first["redaction_count"]), 3)
        self.assertEqual(int(first["clean_word_count"]), 7)
        self.assertEqual(silver["narrative_is_repeated"].tolist(), [True, True, False, False])
        self.assertEqual(silver["has_narrative"].tolist(), [True, True, True, False])
        self.assertTrue(pd.isna(silver.iloc[3]["narrative_clean"]))
        self.assertEqual(counts["silver_narratives"], 3)

    def test_does_not_modify_input(self):
        bronze, _ = self.bronze([mock_complaint(complaint_id="1")])
        before = bronze.copy()
        transform_complaints(bronze)
        pd.testing.assert_frame_equal(bronze, before)

    def test_missing_header_is_rejected(self):
        path = self.root / "bad.csv"
        path.write_text("complaint_id,product\n1,Mortgage\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            read_complaints_csv(path)

    def test_build_writes_parquet_and_report(self):
        _, source = self.bronze([
            mock_complaint(complaint_id="1", consumer_complaint_narrative="XXXX did it"),
            mock_complaint(complaint_id="2"),
            mock_complaint(complaint_id="3", product=""),
        ])
        output = self.root / "silver" / "complaints.parquet"
        quality = self.root / "reports" / "quality.json"
        markdown = self.root / "reports" / "quality.md"
        report = build_silver_complaints(source, output, quality, markdown)
        self.assertTrue(output.exists() and quality.exists() and markdown.exists())
        self.assertEqual(len(pd.read_parquet(output)), 2)
        saved = json.loads(quality.read_text(encoding="utf-8"))
        self.assertEqual(saved["counts"]["rejected_rows"], 1)
        self.assertTrue(all(saved["quality_checks"].values()))
        self.assertEqual(len(saved["source"]["sha256"]), 64)
        self.assertEqual(len(report["output"]["sha256"]), 64)
        self.assertIn("Calidad Silver de reclamos", markdown.read_text(encoding="utf-8"))

    def test_failed_check_raises(self):
        _, source = self.bronze([mock_complaint(complaint_id="1")])
        from bankshield.transforms import silver_complaints as module

        original = module.quality_checks
        module.quality_checks = lambda silver, counts: {**original(silver, counts), "row_accounting": False}
        self.addCleanup(setattr, module, "quality_checks", original)
        with self.assertRaises(ValueError):
            build_silver_complaints(source, self.root / "o.parquet", self.root / "q.json")


if __name__ == "__main__":
    unittest.main()
