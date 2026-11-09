"""Genera KPIs y síntesis comparativa desde reportes reales, sin entrenar modelos."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
from bankshield.analytics_contract import provenance, strict_json, write_json_atomic
from bankshield.transforms.silver_transactions import file_sha256

REPORTS = {
    "transactions": "artifacts/reports/transactions_silver.json",
    "fraud": "artifacts/models/fraud-silver/metrics.json",
    "credit": "artifacts/models/credit/metrics.json",
    "segments": "artifacts/reports/segments.json",
    "forecast": "artifacts/reports/forecast_holt_winters.json",
    "graphs": "artifacts/reports/graph/comparison.json",
    "regression": "artifacts/models/regression/metrics.json",
    "associations": "artifacts/models/associations/rules.json",
}


def fmt(value):
    return "N/D" if value is None else f"{value:,.6f}" if isinstance(value, float) else str(value)


def build(root=ROOT):
    root = Path(root)
    reports = {key: strict_json(root / path) for key, path in REPORTS.items()}
    credit_path = root / "data/bronze/credit/credit_risk_dataset.csv"
    credit = pd.read_csv(credit_path, usecols=["loan_status"])
    complaint_path = root / "data/bronze/complaints/consumer_complaints.csv"
    total_complaints = narratives = 0
    products = Counter()
    for frame in pd.read_csv(complaint_path, usecols=["product", "consumer_complaint_narrative"], dtype=str, chunksize=50_000):
        total_complaints += len(frame)
        narratives += int(frame.consumer_complaint_narrative.fillna("").str.strip().ne("").sum())
        products.update(frame["product"].value_counts().to_dict())
    t, f, seg = reports["transactions"], reports["fraud"], reports["segments"]
    regression, associations = reports["regression"], reports["associations"]
    n_transactions = t["counts"]["silver_rows"]
    n_fraud = sum(row["fraud"] for row in f["partitions"].values())
    metrics = []
    def kpi(key, question, formula, unit, population, value, evidence, owner, category):
        metrics.append({"id": key, "question": question, "formula": formula, "unit": unit,
                        "population_period": population, "observed_value": value, "evidence": evidence,
                        "owner": owner, "category": category,
                        "target": "Sin meta de negocio validada; resultado académico descriptivo."})
    kpi("K01", "¿Qué proporción de operaciones tiene etiqueta fraude?", "100 * fraudes / operaciones",
        "%", "PaySim completo, steps 1–743", 100 * n_fraud / n_transactions,
        REPORTS["fraud"], "Cueva–Taco", "descriptivo")
    kpi("K02", "¿Qué fracción del fraude de prueba recupera el clasificador?", "100 * TP / (TP + FN)",
        "%", "Prueba histórica de fraude 379–743, distinta de test D1", 100 * f["test"]["classifier_selected"]["recall"],
        REPORTS["fraud"], "Cueva", "métrica técnica")
    kpi("K03", "¿Qué proporción de préstamos tiene clase positiva asumida?", "100 * loan_status=1 / registros",
        "%", "Crédito Bronze completo; sin fecha disponible", 100 * float(credit.loan_status.eq(1).mean()),
        str(credit_path.relative_to(root)), "Sevan", "descriptivo; semántica de copia pendiente")
    kpi("K04", "¿Qué proporción de reclamos tiene narrativa publicada?", "100 * narrativas no vacías / reclamos",
        "%", "Copia CFPB completa, 2011–2016", 100 * narratives / total_complaints,
        str(complaint_path.relative_to(root)), "Angel", "cobertura de datos")
    top_product, top_count = products.most_common(1)[0]
    kpi("K05", f"¿Qué concentración tiene el producto con más reclamos ({top_product})?", "100 * reclamos del producto / reclamos",
        "%", "Copia CFPB completa; sin ajuste por cuota de mercado", 100 * top_count / total_complaints,
        str(complaint_path.relative_to(root)), "Angel", "descriptivo")
    kpi("K06", "¿Qué proporción de destinos entra al agrupamiento?", "100 * destinos con >=10 recepciones / destinos únicos",
        "%", "PaySim completo; universo de destinos del Silver", 100 * seg["total_accounts"] / t["accounts"]["unique_destinations"],
        REPORTS["segments"], "Taco", "cobertura de análisis")
    forecast = reports["forecast"]["aggregates"]["transaction_count"]
    kpi("K07", "¿Cuál es el error de cantidad transaccional de la referencia temporal?", "promedio de MAE de cuatro ventanas de 24 steps",
        "transacciones por hora simulada", "Ventanas 623–718; sin stress", forecast["naive"]["mae"],
        REPORTS["forecast"], "Gerardo", "métrica técnica")
    selected = regression["selected_model"]
    kpi("K08", "¿Cuál es el error de estimación del monto?", "sum(abs(prediction-actual)) / n",
        "unidad monetaria no verificada", "Test D1 379–718 completo", regression["evaluation"]["test"][selected]["overall"]["mae"],
        REPORTS["regression"], "Sevan", "métrica técnica")
    coverage = associations["evaluation"]["test"]["fraud_coverage"]
    kpi("K09", "¿Qué fracción del fraude cubre la unión de asociaciones congeladas?", "100 * fraudes cubiertos por al menos una regla / fraudes",
        "%", "Test D1 379–718 completo; reglas elegidas en validation", None if coverage is None else 100 * coverage,
        REPORTS["associations"], "Cueva", "métrica técnica retrospectiva")
    comparison = []
    for name in ("kmeans", "activity_quantiles"):
        comparison.append({"task": "clustering", "candidate": name, "population": f"{seg['total_accounts']} cuentas, k={seg['comparison']['k']}",
                           "metrics": seg["comparison"][name], "decision": "k fijado por silueta KMeans; comparación exploratoria"})
    for target, methods in reports["forecast"]["aggregates"].items():
        for name, values in methods.items():
            comparison.append({"task": f"series/{target}", "candidate": name, "population": "mismas cuatro ventanas de 24 steps",
                               "metrics": values, "decision": "Naive conservado por menor MAE"})
    for item in reports["graphs"]["comparisons"]:
        for name in ("network_indicators", "volume_reference"):
            values = item[name]
            comparison.append({"task": f"grafos/k={item['k']}", "candidate": name,
                               "population": f"prefijo {reports['graphs']['sample']['requested_limit']} filas, universo compartido",
                               "metrics": {key: values[key]["value"] for key in ("account_precision", "fraud_coverage")},
                               "decision": "Comparación retrospectiva a igual k; sin selección por etiquetas"})
    for partition, methods in regression["evaluation"].items():
        for name, values in methods.items():
            comparison.append({"task": f"regresion/{partition}", "candidate": name,
                               "population": str(regression["dataset"]["partitions"][partition]),
                               "metrics": values["overall"], "decision": f"{selected} elegido solo por MAE validation"})
    inputs = {path: file_sha256(root / path).lower() for path in [*REPORTS.values(),
              str(credit_path.relative_to(root)), str(complaint_path.relative_to(root))]}
    return {"schema_version": 1, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "input_sha256": inputs, "kpis": metrics, "comparisons": comparison,
            "associations": {"selected_rules": len(associations["rules"]), "analysis_id": associations["analysis_id"],
                             "evaluation": associations["evaluation"]},
            "limitations": ["Fuentes independientes; no unir clientes entre dominios.",
                            "No se midieron ahorro, rentabilidad ni reducción real de pérdidas.",
                            "No existe una nota o porcentaje de cumplimiento oficial derivado de estas métricas."],
            **provenance([Path(__file__)])}


def render_kpis(report):
    lines = ["# KPIs, indicadores descriptivos y métricas de evaluación", "",
             f"Generado desde los artefactos reales: {report['generated_at_utc']}.", "",
             "No se midieron beneficios económicos reales. Cada indicador tiene población propia; las fuentes no se unen por cliente.",
             "Las metas de negocio no están validadas. Las métricas técnicas no se presentan como ahorro o impacto causal.", ""]
    for item in report["kpis"]:
        lines += [f"## {item['id']} — {item['question']}", "", f"- Encargado: {item['owner']}.",
                  f"- Clase: {item['category']}.", f"- Fórmula: `{item['formula']}`.",
                  f"- Unidad: {item['unit']}.", f"- Población/periodo: {item['population_period']}.",
                  f"- Valor observado: **{fmt(item['observed_value'])}**.", f"- Evidencia: `{item['evidence']}`.",
                  f"- Meta: {item['target']}", ""]
    return "\n".join(lines)


def render_comparison(report):
    lines = ["# Evaluación comparativa por técnica — semana 13", "",
             f"Generación UTC: {report['generated_at_utc']}.", "",
             "Cada comparación se realiza dentro de una tarea. No se comparan MAE, silueta o F1 entre problemas distintos.",
             "", "| Técnica / partición | Candidato | Población | Métricas | Decisión |",
             "| --- | --- | --- | --- | --- |"]
    for row in report["comparisons"]:
        metrics = "; ".join(f"{key}={fmt(value)}" for key, value in row["metrics"].items() if key != "r2_undefined_reason")
        lines.append(f"| {row['task']} | {row['candidate']} | {row['population']} | {metrics} | {row['decision']} |")
    lines += ["", "## Asociaciones de semana 10", "",
              f"Reglas seleccionadas: {report['associations']['selected_rules']}; análisis `{report['associations']['analysis_id']}`.",
              "La búsqueda se hace en train, se filtra en validation y se congelan las reglas para test/stress. No se suman coberturas solapadas.",
              "", "## Límites para la defensa", "",
              "- Clustering: k se eligió con KMeans; no es una evaluación externa de categorías bancarias.",
              "- Series: los errores relativos son elevados; ganar a los candidatos no significa precisión suficiente para operación real.",
              "- Grafos: prefijo no aleatorio y evaluación retrospectiva; no es detección predictiva temporal.",
              "- Regresión: stress se mantiene aparte; la referencia ganadora permanece seleccionada.",
              "- Fuentes/aceptaciones de personas pendientes se registran en cierre-semana13.md.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown-dir", type=Path, default=ROOT / "docs")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/reports/academic/summary.json")
    args = parser.parse_args()
    try:
        report = build()
        write_json_atomic(args.output, report)
        args.markdown_dir.mkdir(parents=True, exist_ok=True)
        (args.markdown_dir / "kpis-negocio.md").write_text(render_kpis(report), encoding="utf-8")
        (args.markdown_dir / "evaluacion-comparativa.md").write_text(render_comparison(report), encoding="utf-8")
        print(f"KPIs: {len(report['kpis'])}; comparaciones: {len(report['comparisons'])}; {args.output}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"No se pudo construir evidencia académica: {exc}\n")


if __name__ == "__main__":
    main()
