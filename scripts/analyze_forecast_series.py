"""Genera estadísticas y gráficos exploratorios de la serie Gold temporal."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankshield.features.temporal import analyze_temporal_series


def resolve(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analiza y grafica la serie Gold temporal."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "forecast.json",
        help="Configuración. Valor predeterminado: configs/forecast.json",
    )
    args = parser.parse_args()

    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Error al leer la configuración: {exc}\n")

    try:
        report = analyze_temporal_series(
            input_path=resolve(ROOT, config["output"]),
            analysis_json=resolve(ROOT, config["analysis_json"]),
            analysis_markdown=resolve(ROOT, config["analysis_markdown"]),
            plots_dir=resolve(ROOT, config["plots_dir"]),
            seasonal_period=int(config.get("seasonal_period", 24)),
            base_dir=ROOT,
        )
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")

    coverage = report["coverage"]
    correlations = report["autocorrelation"]
    print(
        f"Serie: {coverage['steps']} steps | "
        f"Periodo operativo: {coverage['operational_steps']} | "
        f"Tramo final: {coverage['tail_steps']}"
    )
    print(
        "Autocorrelación a 24 steps — "
        f"cantidad: {correlations['24']['transaction_count']:.4f} | "
        f"monto: {correlations['24']['total_amount']:.4f}"
    )
    print(f"Reporte: {resolve(ROOT, config['analysis_markdown'])}")
    print(f"Gráficos: {resolve(ROOT, config['plots_dir'])}")


if __name__ == "__main__":
    main()
