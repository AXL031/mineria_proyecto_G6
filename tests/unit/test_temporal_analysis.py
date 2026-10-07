import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pandas as pd

from bankshield.features.temporal import (
    analyze_temporal_series,
    final_fraud_only_start,
    prepare_temporal_series,
    summarize_temporal_series,
)


def gold_sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "step": [1, 2, 3, 4, 5, 6],
            "transaction_count": [10, 12, 11, 9, 2, 1],
            "total_amount": [100.0, 120.0, 110.0, 90.0, 40.0, 30.0],
            "average_amount": [10.0, 10.0, 10.0, 10.0, 20.0, 30.0],
            "fraud_count": [0, 0, 1, 0, 2, 1],
            "fraud_rate": [0.0, 0.0, 1 / 11, 0.0, 1.0, 1.0],
        }
    )


class TemporalAnalysisTests(unittest.TestCase):
    def test_prepares_cycle_and_rolling_features(self):
        series = prepare_temporal_series(gold_sample(), seasonal_period=3)
        self.assertEqual(series["simulated_hour"].tolist(), [0, 1, 2, 0, 1, 2])
        self.assertEqual(series.loc[0, "transaction_count_ma24"], 10.0)
        self.assertEqual(series.loc[2, "transaction_count_ma24"], 11.0)

    def test_detects_final_fraud_only_segment(self):
        series = prepare_temporal_series(gold_sample(), seasonal_period=3)
        self.assertEqual(final_fraud_only_start(series), 5)
        report = summarize_temporal_series(series, seasonal_period=3)
        self.assertEqual(report["coverage"]["operational_steps"], 4)
        self.assertEqual(report["coverage"]["tail_steps"], 2)

    def test_generates_reports_and_plots(self):
        root = Path(__file__).resolve().parents[2]
        parent = root / "artifacts" / "reports" / "forecast-analysis-tests"
        parent.mkdir(parents=True, exist_ok=True)
        workdir = parent / uuid.uuid4().hex
        workdir.mkdir()
        self.addCleanup(shutil.rmtree, workdir, True)

        input_path = workdir / "gold.parquet"
        analysis_json = workdir / "analysis.json"
        analysis_markdown = workdir / "analysis.md"
        plots_dir = workdir / "plots"
        gold_sample().to_parquet(input_path, index=False)

        report = analyze_temporal_series(
            input_path,
            analysis_json,
            analysis_markdown,
            plots_dir,
            seasonal_period=3,
            base_dir=root,
        )

        self.assertEqual(report["coverage"]["final_fraud_only_start"], 5)
        self.assertTrue(analysis_json.exists())
        self.assertTrue(analysis_markdown.exists())
        self.assertEqual(len(list(plots_dir.glob("*.png"))), 3)
        stored = json.loads(analysis_json.read_text(encoding="utf-8"))
        self.assertEqual(stored["seasonal_period"], 3)


if __name__ == "__main__":
    unittest.main()
