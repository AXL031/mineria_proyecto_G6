import csv
import json
import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from bankshield.ingestion.complaints_profile import (
    FIELDS,
    extract_year,
    profile_complaints,
    write_reports,
)


def mock_complaint(**changes):
    base = {
        "date_received": "05/12/2015",
        "product": "Credit card",
        "sub_product": "General-purpose credit card",
        "issue": "Billing disputes",
        "sub_issue": "Excessive fee",
        "consumer_complaint_narrative": "I was charged an unknown fee of $50 by XXXX on my card.",
        "company_public_response": "Company has responded to the consumer",
        "company": "Bank of America",
        "state": "CA",
        "zipcode": "90210",
        "tags": "",
        "consumer_consent_provided": "Consent provided",
        "submitted_via": "Web",
        "date_sent_to_company": "05/14/2015",
        "company_response_to_consumer": "Closed with explanation",
        "timely_response": "Yes",
        "consumer_disputed?": "No",
        "complaint_id": "1001",
    }
    base.update(changes)
    return base


class ComplaintsProfileTests(unittest.TestCase):
    def setUp(self):
        parent = Path(__file__).resolve().parents[2] / "artifacts/reports/complaints-tests"
        parent.mkdir(parents=True, exist_ok=True)
        self.workdir = parent / uuid.uuid4().hex
        self.workdir.mkdir()
        self.addCleanup(self.cleanup_files)
        self.path = self.workdir / "complaints.csv"

    def cleanup_files(self):
        if self.workdir.exists():
            for path in self.workdir.iterdir():
                path.unlink()
            self.workdir.rmdir()

    def write_csv(self, rows):
        with self.path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def test_extract_year(self):
        self.assertEqual(extract_year("08/30/2013"), "2013")
        self.assertEqual(extract_year("2015-05-12"), "2015")
        self.assertEqual(extract_year(""), "desconocido")
        self.assertEqual(extract_year("invalid-date"), "otro")

    def test_profile_basic_and_narratives(self):
        row1 = mock_complaint(complaint_id="1", consumer_complaint_narrative="Complaint text with XXXX redaction.")
        row2 = mock_complaint(complaint_id="2", consumer_complaint_narrative="")  # Sin narrativa
        row3 = mock_complaint(complaint_id="3", product="Mortgage", consumer_complaint_narrative="Short message.")
        self.write_csv([row1, row2, row3])

        profile = profile_complaints(self.path)
        self.assertEqual(profile["rows"], 3)
        self.assertEqual(profile["valid_rows"], 3)
        self.assertEqual(profile["invalid_rows"], 0)

        nm = profile["narrative_metrics"]
        self.assertEqual(nm["count"], 2)
        self.assertAlmostEqual(nm["coverage_rate"], 2 / 3, places=4)
        self.assertEqual(nm["narratives_with_redaction"], 1)
        self.assertEqual(nm["redaction_rate"], 0.5)

        self.assertIn("Credit card", profile["by_product"])
        self.assertEqual(profile["by_product"]["Credit card"]["rows"], 2)
        self.assertEqual(profile["by_product"]["Credit card"]["narratives"], 1)
        self.assertEqual(profile["by_product"]["Mortgage"]["rows"], 1)

    def test_invalid_and_missing_rows(self):
        row_valid = mock_complaint(complaint_id="10")
        row_invalid_id = mock_complaint(complaint_id="abc")
        row_missing_prod = mock_complaint(complaint_id="11", product="")
        self.write_csv([row_valid, row_invalid_id, row_missing_prod])

        profile = profile_complaints(self.path)
        self.assertEqual(profile["rows"], 3)
        self.assertEqual(profile["valid_rows"], 1)
        self.assertEqual(profile["invalid_rows"], 2)
        self.assertEqual(profile["issues"]["invalid:complaint_id"], 1)
        self.assertEqual(profile["issues"]["missing:product"], 1)

    def test_duplicate_complaint_ids(self):
        row1 = mock_complaint(complaint_id="99")
        row2 = mock_complaint(complaint_id="99")
        self.write_csv([row1, row2])

        profile = profile_complaints(self.path)
        self.assertEqual(profile["duplicate_complaint_ids"], 1)

    def test_sampling_and_limits(self):
        self.write_csv([mock_complaint(complaint_id="1"), mock_complaint(complaint_id="2")])
        profile = profile_complaints(self.path, limit=1)
        self.assertEqual(profile["rows"], 1)
        self.assertEqual(profile["scope"], "first_rows_sample")

        with self.assertRaises(ValueError):
            profile_complaints(self.path, limit=0)

    def test_write_reports(self):
        self.write_csv([mock_complaint(complaint_id="1")])
        profile = profile_complaints(self.path)
        json_out = self.workdir / "report.json"
        md_out = self.workdir / "report.md"

        write_reports(profile, json_out, md_out)
        self.assertTrue(json_out.exists())
        self.assertTrue(md_out.exists())

        loaded = json.loads(json_out.read_text(encoding="utf-8"))
        self.assertEqual(loaded["rows"], 1)
        self.assertIn("Perfil de Reclamos", md_out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
