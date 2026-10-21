"""Reconstruye artefactos faltantes para demo sin sobrescribir reportes versionados."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "artifacts/reports/demo"


def step(name, script, arguments, outputs, force=False):
    if not force and all((ROOT / output).is_file() for output in outputs):
        print(f"Disponible: {name}", flush=True)
        return
    print(f"Preparando: {name}. Log: artifacts/reports/demo/{name}.log", flush=True)
    with (REPORTS / f"{name}.log").open("w", encoding="utf-8") as log:
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / script), *arguments],
                                cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"Falló {name}; revisar {REPORTS / (name + '.log')}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Reconstruir incluso artefactos existentes")
    args = parser.parse_args()
    REPORTS.mkdir(parents=True, exist_ok=True)
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[variable] = "2"
    def run(name, script, arguments, outputs):
        step(name, script, arguments, outputs, args.force)
    run("transactions-silver", "build_silver.py", ["--quality-markdown", str(REPORTS / "transactions-silver.md")],
        ["data/silver/transactions/transactions.parquet", "artifacts/reports/transactions_silver.json"])
    run("credit-silver", "build_silver_credit.py", ["--markdown", str(REPORTS / "credit-silver.md")],
        ["data/silver/credit/credit.parquet", "artifacts/reports/credit/silver_quality.json"])
    run("credit-training", "train_credit.py", ["--markdown", str(REPORTS / "credit-training.md")],
        ["artifacts/models/credit/model.joblib"])
    run("forecast-gold", "build_forecast_gold.py", ["--quality-markdown", str(REPORTS / "forecast-gold.md")],
        ["data/gold/forecast/transactions_hourly.parquet"])
    run("forecast-monitoring", "monitor_forecast_shift.py", ["--markdown", str(REPORTS / "forecast-monitoring.md")],
        ["artifacts/reports/forecast_monitoring.json"])
    run("transactions-gold", "build_gold_transactions.py", ["--quality-markdown", str(REPORTS / "transactions-gold.md")],
        ["data/gold/transactions/transactions_mart.parquet"])
    config = json.loads((ROOT / "configs/segments.json").read_text(encoding="utf-8"))
    config["report_markdown"] = str(REPORTS / "segments.md")
    config_path = REPORTS / "segments-config.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    run("segments-build", "segment_transactions.py", ["--config", str(config_path)],
        ["data/gold/segments/account_segments.parquet", "artifacts/reports/segments.json"])
    run("complaints-silver", "build_silver_complaints.py", ["--markdown", str(REPORTS / "complaints-silver.md")],
        ["data/silver/complaints/complaints.parquet", "artifacts/reports/complaints/silver_quality.json"])
    run("complaints-training", "train_complaints.py", ["--markdown", str(REPORTS / "complaints-training.md")],
        ["artifacts/models/complaints/model.joblib"])
    run("complaints-examples", "analyze_complaints_errors.py", ["--markdown", str(REPORTS / "complaints-examples.md")],
        ["artifacts/reports/complaints/error_examples.json"])
    if not (ROOT / "artifacts/models/fraud-silver/model.joblib").is_file():
        run("fraud-training", "train_fraud.py", ["--input-format", "silver", "--input", "data/silver/transactions/transactions.parquet",
             "--output", "artifacts/models/fraud-silver", "--markdown", str(REPORTS / "fraud-training.md")],
            ["artifacts/models/fraud-silver/model.joblib"])
    run("fraud-patterns", "analyze_fraud_patterns.py", ["--markdown", str(REPORTS / "fraud-patterns.md")],
        ["artifacts/models/fraud-silver/patterns.json"])
    print("Artefactos disponibles. Inicia scripts/start_demo.ps1 y verifica el recorrido.")


if __name__ == "__main__":
    main()
