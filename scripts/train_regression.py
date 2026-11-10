"""Entrena y evalúa la regresión del monto transaccional (SEV-01) sobre D1."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankshield.models.regression import RegressionConfig, train_regression


def main():
    parser = argparse.ArgumentParser(description="Entrenamiento de la regresión del monto")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/regression.json")
    args = parser.parse_args()
    try:
        raw = json.loads(args.config.read_text(encoding="utf-8"))
        resolve = lambda key: ROOT / raw[key]
        report = train_regression(RegressionConfig.from_mapping(raw), resolve("input"),
                                  resolve("dataset_report"), resolve("output"))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(f"Modelo seleccionado: {report['selected_model']} ({report['model_id']})")
    for name, parts in report["comparison"].items():
        v, t = parts["validation"], parts["test"]
        print(f"  {name:24s} validation MAE {v['mae']:.2f} | test MAE {t['mae']:.2f} RMSE {t['rmse']:.2f} "
              f"R2 {t['r2'] if t['r2'] is None else round(t['r2'], 4)}")
    print(f"Tiempo: {report['run']['seconds']} s (CPU {report['run']['cpu_seconds']} s); "
          f"predicciones: {report['predictions_rows']} filas")


if __name__ == "__main__":
    main()
