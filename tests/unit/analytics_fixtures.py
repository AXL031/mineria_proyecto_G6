"""Fixtures explícitos de D1; no contienen ni descargan datos originales."""

import json
from pathlib import Path

from bankshield.analytics_contract import AnalyticalDataset
from bankshield.transforms.analytical_transactions import build_fixture


def dataset_fixture(directory, chunksize=7):
    directory = Path(directory)
    build_fixture(directory)
    return AnalyticalDataset(directory / "analytics_transactions.parquet", directory / "dataset.json",
                             directory / "discretization.json", chunksize=chunksize)


def regression_config():
    return {"max_train_rows": 12, "seed": 42, "examples_limit": 10}


def association_config():
    return {"min_support": .01, "min_antecedent_count": 1, "min_confidence": .01,
            "min_lift": 0, "max_rules": 50, "max_antecedent_items": 3, "max_candidates": 1000}
