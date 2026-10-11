"""Evalúa los modelos Naive del módulo de pronósticos."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankshield.evaluation.forecast import run_forecast_baseline_evaluation


def resolve(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evalúa Naive y Naive estacional mediante backtesting."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "forecast.json",
        help="Configuración. Valor predeterminado: configs/forecast.json",
    )
    parser.add_argument("--input", type=Path, help="Parquet Gold temporal")
    parser.add_argument("--output", type=Path, help="Reporte JSON de métricas")
    args = parser.parse_args()

    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        evaluation_config = config["evaluation"]
        input_path = resolve(ROOT, args.input or config["output"])
        output_path = resolve(
            ROOT,
            args.output or evaluation_config["report_json"],
        )
        report = run_forecast_baseline_evaluation(
            input_path,
            output_path,
            evaluation_config,
            base_dir=ROOT,
        )
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Error: {exc}\n")

    print(f"Experimento: {report['experiment_id']}")
    print(
        f"Ventanas: {len(report['windows'])} | "
        f"Horizonte: {report['protocol']['horizon']} steps"
    )
    for target, models in report["aggregates"].items():
        summary = " | ".join(
            f"{model}: MAE={metrics['mae']:.4f}"
            for model, metrics in models.items()
        )
        print(f"{target} — {summary}")
    print(f"Reporte JSON: {output_path}")


if __name__ == "__main__":
    main()
