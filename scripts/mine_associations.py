"""Descubre y evalúa asociaciones desde D1, exclusivamente offline."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankshield.analytics_contract import AnalyticalDataset, resolve, strict_json, write_json_atomic
from bankshield.models.associations import mine, render_markdown


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/associations.json")
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    try:
        config = strict_json(resolve(args.config))
        dataset = AnalyticalDataset(*(resolve(config[key]) for key in (
            "input", "dataset_report", "discretization_report")), chunksize=config["chunksize"])
        report = mine(dataset, config)
        write_json_atomic(resolve(config["output"]), report)
        markdown = resolve(args.markdown or config["markdown"])
        markdown.parent.mkdir(parents=True, exist_ok=True)
        markdown.write_text(render_markdown(report), encoding="utf-8")
        print(f"Reglas: {len(report['rules'])}; candidatos: {report['search']['total_candidates']}; análisis: {report['analysis_id']}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"No se pudo completar asociaciones: {exc}\n")


if __name__ == "__main__":
    main()
