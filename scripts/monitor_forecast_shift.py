"""Compara el tramo final de PaySim con una ventana operativa reciente."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankshield.models.monitoring import run_historical_monitoring


def resolve(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Monitorea cambios históricos entre dos ventanas de PaySim."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "forecast.json",
    )
    parser.add_argument("--input", type=Path, help="Parquet Silver transaccional")
    parser.add_argument("--output", type=Path, help="Reporte JSON")
    parser.add_argument("--markdown", type=Path, help="Resumen Markdown")
    args = parser.parse_args()

    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        monitoring = config["monitoring"]
        report = run_historical_monitoring(
            resolve(ROOT, args.input or config["input"]),
            resolve(ROOT, args.output or monitoring["report_json"]),
            resolve(ROOT, args.markdown or monitoring["results_markdown"]),
            monitoring,
            base_dir=ROOT,
        )
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Error: {exc}\n")

    print(f"Experimento: {report['experiment_id']}")
    print(f"Estado: {report['status']} | Alertas: {report['alert_count']}")
    for name, value in report["changes"].items():
        displayed = "no definido" if value is None else f"{value:.4f}"
        print(f"{name}: {displayed} | alerta={report['alerts'][name]}")


if __name__ == "__main__":
    main()
