"""Entrena, compara y exporta la regresión de monto sobre D1 completo."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankshield.analytics_contract import AnalyticalDataset, resolve, strict_json
from bankshield.models.regression import train, render_markdown


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/regression.json")
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    try:
        config = strict_json(resolve(args.config))
        dataset = AnalyticalDataset(*(resolve(config[key]) for key in (
            "input", "dataset_report", "discretization_report")), chunksize=config["chunksize"])
        report = train(dataset, config, resolve(config["output"]))
        markdown = resolve(args.markdown or config["markdown"])
        markdown.parent.mkdir(parents=True, exist_ok=True)
        markdown.write_text(render_markdown(report), encoding="utf-8")
        print(f"Modelo: {report['selected_model']}; SHA-256: {report['model_id']}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"No se pudo completar regresión: {exc}\n")


if __name__ == "__main__":
    main()
