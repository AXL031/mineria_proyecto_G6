"""Prepara la demo offline con dependencias, huellas, logs y manifiesto verificable."""

import argparse
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankshield.preparation import Preparation, Stage, atomic_json, dependency_order

REPORTS = "artifacts/reports/demo"
BRONZE = "data/bronze/transactions/PS_20174392719_1491204439457_log.csv"
SILVER = "data/silver/transactions/transactions.parquet"
QUALITY = "artifacts/reports/transactions_silver.json"
D1 = "data/gold/analytics/transactions.parquet"
D1_REPORTS = ("artifacts/reports/analytics/dataset.json", "artifacts/reports/analytics/discretization.json")


def stages_for(root=ROOT, scope="current"):
    """Las ampliaciones tienen contrato explícito; su ausencia nunca acredita full."""
    stages = []

    def add(name, script, *, arguments=(), dependencies=(), inputs=(), outputs=(), configs=(), sources=()):
        stages.append(Stage(name, "scripts/" + script, tuple(arguments), tuple(dependencies),
                            tuple(inputs), tuple(outputs), tuple(configs), tuple(sources),
                            {path: 1 for path in outputs if path.endswith(".json")}))

    def md(name, flag="--markdown"):
        return (flag, f"{REPORTS}/{name}.md")

    add("transactions-silver", "build_silver.py", arguments=md("transactions-silver", "--quality-markdown"),
        inputs=(BRONZE,), outputs=(SILVER, QUALITY), configs=("configs/transactions.json",),
        sources=("src/bankshield/transforms/silver_transactions.py", "src/bankshield/ingestion/paysim_profile.py"))
    add("analytics-d1", "build_analytics_transactions.py", arguments=("--config", "configs/analytics.json"),
        dependencies=("transactions-silver",), inputs=(SILVER, QUALITY), outputs=(D1, *D1_REPORTS),
        configs=("configs/analytics.json",), sources=("src/bankshield/transforms/analytical_transactions.py",))
    credit_bronze = "data/bronze/credit/credit_risk_dataset.csv"
    credit_silver = "data/silver/credit/credit.parquet"
    credit_quality = "artifacts/reports/credit/silver_quality.json"
    add("credit-silver", "build_silver_credit.py", arguments=md("credit-silver"), inputs=(credit_bronze,),
        outputs=(credit_silver, credit_quality), sources=("src/bankshield/transforms/silver_credit.py",
                  "src/bankshield/ingestion/credit_profile.py"))
    add("credit-training", "train_credit.py", arguments=md("credit-training"), dependencies=("credit-silver",),
        inputs=(credit_silver, credit_quality, credit_bronze), configs=("configs/credit.json",),
        outputs=("artifacts/models/credit/model.joblib", "artifacts/models/credit/metrics.json"),
        sources=("src/bankshield/models/credit.py", "src/bankshield/features/credit.py"))
    add("forecast-gold", "build_forecast_gold.py", arguments=md("forecast-gold", "--quality-markdown"),
        dependencies=("transactions-silver",), inputs=(SILVER,),
        outputs=("data/gold/forecast/transactions_hourly.parquet", "artifacts/reports/forecast_gold.json"),
        configs=("configs/forecast.json",), sources=("src/bankshield/transforms/temporal_transactions.py",))
    add("forecast-monitoring", "monitor_forecast_shift.py", arguments=md("forecast-monitoring"),
        dependencies=("transactions-silver",), inputs=(SILVER,), outputs=("artifacts/reports/forecast_monitoring.json",),
        configs=("configs/forecast.json",), sources=("src/bankshield/models/monitoring.py",))
    mart = "data/gold/transactions/transactions_mart.parquet"
    add("transactions-gold", "build_gold_transactions.py", arguments=md("transactions-gold", "--quality-markdown"),
        dependencies=("transactions-silver",), inputs=(SILVER,),
        outputs=(mart, "artifacts/reports/transactions_gold.json"), configs=("configs/transactions_gold.json",),
        sources=("src/bankshield/transforms/gold_transactions.py",))
    add("segments-build", "segment_transactions.py", arguments=("--config", f"{REPORTS}/segments-config.json"),
        dependencies=("transactions-gold",), inputs=(mart,), configs=("configs/segments.json", f"{REPORTS}/segments-config.json"),
        outputs=("data/gold/segments/account_segments.parquet", "artifacts/reports/segments.json"),
        sources=("src/bankshield/models/segments.py", "src/bankshield/features/segments.py"))
    complaints_bronze = "data/bronze/complaints/consumer_complaints.csv"
    complaints_silver = "data/silver/complaints/complaints.parquet"
    complaints_quality = "artifacts/reports/complaints/silver_quality.json"
    complaints_model = "artifacts/models/complaints/model.joblib"
    add("complaints-silver", "build_silver_complaints.py", arguments=md("complaints-silver"), inputs=(complaints_bronze,),
        outputs=(complaints_silver, complaints_quality), sources=("src/bankshield/transforms/silver_complaints.py",
                    "src/bankshield/features/text_cleaning.py"))
    add("complaints-training", "train_complaints.py", arguments=md("complaints-training"), dependencies=("complaints-silver",),
        inputs=(complaints_silver, complaints_quality, complaints_bronze), configs=("configs/complaints.json",),
        outputs=(complaints_model, "artifacts/models/complaints/metrics.json"),
        sources=("src/bankshield/models/complaints.py", "src/bankshield/features/text_cleaning.py"))
    add("complaints-examples", "analyze_complaints_errors.py", arguments=md("complaints-examples"),
        dependencies=("complaints-training",), inputs=(complaints_model, complaints_silver, complaints_quality),
        outputs=("artifacts/reports/complaints/error_examples.json",),
        sources=("src/bankshield/models/complaints_review.py", "src/bankshield/models/complaints.py"))
    fraud_profile = "artifacts/reports/fraud/paysim_profile.json"
    fraud_model = "artifacts/models/fraud-silver/model.joblib"
    add("fraud-profile", "profile_fraud.py", arguments=md("fraud-profile"), inputs=(BRONZE,), outputs=(fraud_profile,),
        sources=("src/bankshield/ingestion/paysim_profile.py",))
    add("fraud-training", "train_fraud.py", arguments=("--input-format", "silver", "--input", SILVER,
        "--output", "artifacts/models/fraud-silver", *md("fraud-training")),
        dependencies=("transactions-silver", "fraud-profile"), inputs=(SILVER, QUALITY, fraud_profile, BRONZE),
        configs=("configs/fraud.json",), outputs=(fraud_model, "artifacts/models/fraud-silver/metrics.json"),
        sources=("src/bankshield/models/fraud.py", "src/bankshield/ingestion/fraud_dataset.py", "src/bankshield/features/fraud.py"))
    add("fraud-patterns", "analyze_fraud_patterns.py", arguments=md("fraud-patterns"),
        dependencies=("fraud-training",), inputs=(SILVER, fraud_model, "artifacts/models/fraud-silver/metrics.json"),
        outputs=("artifacts/models/fraud-silver/patterns.json",), sources=("src/bankshield/features/fraud_patterns.py",
                   "src/bankshield/services/fraud.py"))
    add("associations", "mine_associations.py", arguments=("--config", f"{REPORTS}/associations-config.json", *md("associations")),
        dependencies=("analytics-d1",), inputs=(D1, *D1_REPORTS), configs=("configs/associations.json",),
        outputs=("artifacts/models/associations/rules.json",), sources=("src/bankshield/models/associations.py",
                "src/bankshield/features/association_transactions.py"))
    add("regression", "train_regression.py", arguments=("--config", f"{REPORTS}/regression-config.json", *md("regression")),
        dependencies=("analytics-d1",), inputs=(D1, *D1_REPORTS), configs=("configs/regression.json",),
        outputs=("artifacts/models/regression/model.joblib", "artifacts/models/regression/metrics.json",
                 "artifacts/models/regression/predictions.parquet", "artifacts/models/regression/examples.json"),
        sources=("src/bankshield/models/regression.py", "src/bankshield/features/regression.py"))
    add("graph-comparison", "evaluate_graph_alerts.py", arguments=("--limit", "10000",
        "--output", f"{REPORTS}/graph-alert-evaluation.json", "--comparison-output", "artifacts/reports/graph/comparison.json",
        "--comparison-markdown", f"{REPORTS}/graph-comparison.md"), inputs=(BRONZE,),
        configs=("configs/graph.json",), outputs=("artifacts/reports/graph/comparison.json",),
        sources=("src/bankshield/ingestion/graph_dataset.py", "src/bankshield/features/graph.py",
                 "src/bankshield/features/graph_patterns.py"))
    add("model-monitoring", "monitor_model_performance.py", arguments=("--config", f"{REPORTS}/monitoring-config.json"),
        dependencies=("regression",), inputs=("artifacts/models/regression/predictions.parquet",
        "artifacts/models/regression/model.joblib", "artifacts/models/regression/metrics.json", *D1_REPORTS),
        configs=("configs/model_monitoring.json",))
    extensions = {"associations": "CUE-01", "regression": "SEV-01", "graph-comparison": "RHA-01",
                  "model-monitoring": "GER-02 (P2)"}
    result = []
    for stage in stages:
        if stage.name in extensions:
            missing = [path for path in (stage.script, *stage.configs, *stage.sources) if not (root / path).is_file()]
            if stage.name == "graph-comparison" and (root / stage.script).is_file():
                if "--comparison-output" not in (root / stage.script).read_text(encoding="utf-8"):
                    missing.append("CLI --comparison-output")
            if stage.name in ("associations", "regression") and (root / stage.script).is_file():
                if "--markdown" not in (root / stage.script).read_text(encoding="utf-8"):
                    missing.append("CLI --markdown para no sobrescribir documentación versionada")
            reason = None
            if stage.name == "model-monitoring":
                reason = "GER-02 es P2 y usa historial inmutable; ejecutar explícitamente después de regresión, no como salida fija de demo."
            elif missing:
                reason = f"Entrega {extensions[stage.name]} pendiente: {', '.join(missing)}"
            if scope == "current" and reason is None:
                reason = "Fuera del alcance current; seleccionar --scope full para preparar esta ampliación."
            stage = replace(stage, optional=scope == "current" or stage.name == "model-monitoring", unavailable_reason=reason)
        result.append(stage)
    return result


def write_demo_configs(root):
    # Solo copias locales; nunca cambiar reportes Markdown versionados.
    for name in ("segments", "associations", "regression", "model_monitoring"):
        source = root / f"configs/{name}.json"
        if source.is_file():
            config = json.loads(source.read_text(encoding="utf-8"))
            for key in ("report_markdown", "results_markdown", "markdown"):
                if key in config or (name == "segments" and key == "report_markdown"):
                    config[key] = f"{REPORTS}/{name}.md"
            atomic_json(root / REPORTS / f"{name.replace('model_', '')}-config.json", config)


def git_context(root):
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True)
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True)
        return {"commit": commit.stdout.strip() if commit.returncode == 0 else None,
                "tree_dirty": bool(dirty.stdout.strip()) if dirty.returncode == 0 else None}
    except OSError:
        return {"commit": None, "tree_dirty": None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Reconstruir TODA etapa seleccionada y sus dependencias, incluido fraude")
    parser.add_argument("--scope", choices=("current", "full"), default="current",
                        help="current: seis módulos + D1; full: exige también entregas CUE-01/SEV-01/RHA-01")
    parser.add_argument("--stage", action="append", help="Preparar solo esta etapa y sus dependencias; repetible")
    parser.add_argument("--plan", action="store_true", help="Mostrar orden y entregas pendientes, sin generar datos ni entrenar")
    args = parser.parse_args()
    if args.stage and set(args.stage).intersection({"associations", "regression", "graph-comparison"}):
        args.scope = "full"
    stages = stages_for(scope=args.scope)
    selected = args.stage or [stage.name for stage in stages]
    try:
        if args.plan:
            for stage in dependency_order(stages, selected):
                print(f"{stage.name} <- {', '.join(stage.dependencies) or 'Bronze'}" +
                      (f" | {stage.unavailable_reason}" if stage.unavailable_reason else ""))
            return
        write_demo_configs(ROOT)
        engine = Preparation(ROOT, context={"scope": args.scope, "limited_selection": bool(args.stage),
                                            **git_context(ROOT)})
        engine.run(stages, selected, force=args.force)
        print(f"Preparación scope={args.scope} terminada; manifiesto: {engine.manifest_path}")
        if args.scope == "current":
            print("Las ampliaciones pendientes no quedan acreditadas. Usar --scope full cuando sus dueños las entreguen.")
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"Error de preparación: {exc}\n")


if __name__ == "__main__":
    main()
