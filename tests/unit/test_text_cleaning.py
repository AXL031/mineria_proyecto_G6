import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from bankshield.features.text_cleaning import RESIDUAL_REDACTION, clean_narrative, count_redactions


class TextCleaningTests(unittest.TestCase):
    def test_masks_each_redaction_family(self):
        text = "XXXX charged {$27.00} on XX/XX/XXXX and again XXXX/XXXX/2015."
        self.assertEqual(
            clean_narrative(text),
            "<censurado> charged <monto> on <fecha> and again <fecha>.",
        )
        self.assertEqual(count_redactions(text), 4)

    def test_amounts_with_thousands_and_ranges(self):
        text = "Paid {$1,250.50} between XX/XX/XXXX-XX/XX/XXXX"
        self.assertEqual(clean_narrative(text), "paid <monto> between <fecha>-<fecha>")

    def test_uncensored_date_is_kept(self):
        self.assertEqual(clean_narrative("Called on 05/12/2015"), "called on 05/12/2015")
        self.assertEqual(count_redactions("Called on 05/12/2015"), 0)

    def test_redaction_glued_to_punctuation_or_letters(self):
        self.assertEqual(clean_narrative("From XXXX, XXXX."), "from <censurado>, <censurado>.")
        self.assertEqual(clean_narrative("XXXX/month"), "<censurado>/month")
        self.assertEqual(clean_narrative("XXXXXXXXXXXX"), "<censurado>")

    def test_lowercase_x_runs_typed_by_consumers_are_masked(self):
        self.assertEqual(clean_narrative("account # is xxxxxxxxxxx, ok"), "account # is <censurado>, ok")
        self.assertEqual(count_redactions("card xxxx and XXXX"), 2)

    def test_words_containing_x_are_not_masked(self):
        self.assertEqual(clean_narrative("MAXX Express xxl"), "maxx express xxl")
        self.assertIsNone(RESIDUAL_REDACTION.search(clean_narrative("MAXX Express xxl")))

    def test_whitespace_and_case_are_normalized(self):
        self.assertEqual(clean_narrative("  Line one \n\nLINE   two\t\n"), "line one line two")

    def test_none_and_empty(self):
        self.assertEqual(clean_narrative(None), "")
        self.assertEqual(clean_narrative(""), "")
        self.assertEqual(count_redactions(None), 0)

    def test_no_residual_redaction_after_cleaning(self):
        text = "XXXX XXXXXXXX XX/XX/XXXX XXXX/XXXX/99 {$5.00} XXXXI"
        self.assertIsNone(RESIDUAL_REDACTION.search(clean_narrative(text)))


if __name__ == "__main__":
    unittest.main()
