"""Evaluación de alertas de grafos contra etiquetas de fraude.

Mide la asociación entre los patrones de sospecha detectados por
el módulo de grafos y la etiqueta real `isFraud` del dataset PaySim.

Los patrones detectados son exploratorios y no constituyen un modelo
predictivo.  Esta evaluación documenta su utilidad como señales
complementarias.

Uso desde la raíz del proyecto:

    python scripts/evaluate_graph_alerts.py
    python scripts/evaluate_graph_alerts.py --limit 100000
    python scripts/evaluate_graph_alerts.py --markdown artifacts/reports/graph/evaluacion-alertas.md
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd

from bankshield.ingestion.graph_dataset import read_transaction_edges, summarize_edges
from bankshield.features.graph import (
    build_transaction_graph,
    compute_node_metrics,
    compute_graph_summary,
)
from bankshield.features.graph_patterns import (
    combine_suspicion_indicators,
    detect_high_fanout,
    detect_high_fanin,
    detect_high_value_edges,
    detect_net_flow_anomalies,
)


def _load_config() -> dict:
    config_path = ROOT / "configs" / "graph.json"
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))
    return {}


def _evaluate_pattern_vs_fraud(
    edges: pd.DataFrame,
    G,
    node_metrics: pd.DataFrame,
    pattern_name: str,
    flagged_accounts: set[str],
) -> dict:
    """Evalúa un conjunto de cuentas marcadas por un patrón contra isFraud.

    Calcula cuántas transacciones fraudulentas involucran cuentas
    detectadas por el patrón (como origen o destino).

    Returns
    -------
    dict
        Métricas de asociación entre el patrón y la etiqueta de fraude.
    """
    if not flagged_accounts:
        return {
            "pattern": pattern_name,
            "flagged_accounts": 0,
            "flagged_with_fraud": 0,
            "fraud_txns_involving_flagged": 0,
            "total_fraud_txns": int(edges["isFraud"].sum()),
            "coverage_fraud": 0.0,
            "precision_at_account": 0.0,
            "precision_at_txn": 0.0,
            "note": "Ninguna cuenta superó el umbral.",
        }

    total_fraud = int(edges["isFraud"].sum())
    fraud_edges = edges[edges["isFraud"] == 1]

    # Transacciones fraudulentas donde al menos una cuenta está flagged
    fraud_involving_flagged = fraud_edges[
        fraud_edges["nameOrig"].isin(flagged_accounts)
        | fraud_edges["nameDest"].isin(flagged_accounts)
    ]
    n_fraud_involving = len(fraud_involving_flagged)

    # Transacciones totales que involucran cuentas flagged
    all_involving_flagged = edges[
        edges["nameOrig"].isin(flagged_accounts)
        | edges["nameDest"].isin(flagged_accounts)
    ]
    n_total_involving = len(all_involving_flagged)

    # Cuentas flagged que tienen al menos una transacción fraudulenta
    fraud_origins = set(fraud_edges["nameOrig"].unique())
    fraud_dests = set(fraud_edges["nameDest"].unique())
    fraud_accounts = fraud_origins | fraud_dests
    flagged_with_fraud = flagged_accounts & fraud_accounts

    coverage = n_fraud_involving / total_fraud if total_fraud > 0 else 0.0
    precision_txn = (
        n_fraud_involving / n_total_involving if n_total_involving > 0 else 0.0
    )
    precision_account = (
        len(flagged_with_fraud) / len(flagged_accounts)
        if flagged_accounts
        else 0.0
    )

    return {
        "pattern": pattern_name,
        "flagged_accounts": len(flagged_accounts),
        "flagged_with_fraud": len(flagged_with_fraud),
        "precision_at_account": round(precision_account, 6),
        "fraud_txns_involving_flagged": n_fraud_involving,
        "total_txns_involving_flagged": n_total_involving,
        "precision_at_txn": round(precision_txn, 6),
        "total_fraud_txns": total_fraud,
        "coverage_fraud": round(coverage, 6),
        "note": (
            "Cobertura = fraudes que involucran al menos una cuenta "
            "flagged / total fraudes.  Precisión a nivel de cuenta = "
            "cuentas flagged con al menos un fraude / total flagged."
        ),
    }


def _evaluate_combined(
    edges: pd.DataFrame,
    suspicious_df: pd.DataFrame,
) -> dict:
    """Evalúa las cuentas que combinan múltiples indicadores."""
    if suspicious_df.empty:
        return {
            "multi_pattern_accounts": 0,
            "min_patterns": 0,
            "note": "Sin cuentas con múltiples indicadores.",
        }

    total_fraud = int(edges["isFraud"].sum())
    fraud_edges = edges[edges["isFraud"] == 1]
    fraud_accounts = set(fraud_edges["nameOrig"].unique()) | set(
        fraud_edges["nameDest"].unique()
    )

    results = []
    for min_patterns in range(1, int(suspicious_df["pattern_count"].max()) + 1):
        subset = suspicious_df[suspicious_df["pattern_count"] >= min_patterns]
        flagged = set(subset["account"])
        flagged_fraud = flagged & fraud_accounts

        fraud_involving = fraud_edges[
            fraud_edges["nameOrig"].isin(flagged)
            | fraud_edges["nameDest"].isin(flagged)
        ]

        all_involving = edges[
            edges["nameOrig"].isin(flagged)
            | edges["nameDest"].isin(flagged)
        ]

        results.append({
            "min_patterns": min_patterns,
            "flagged_accounts": len(flagged),
            "flagged_with_fraud": len(flagged_fraud),
            "precision_account": round(
                len(flagged_fraud) / len(flagged) if flagged else 0.0, 6
            ),
            "fraud_txns_covered": len(fraud_involving),
            "coverage_fraud": round(
                len(fraud_involving) / total_fraud if total_fraud > 0 else 0.0,
                6,
            ),
            "precision_txn": round(
                len(fraud_involving) / len(all_involving)
                if len(all_involving) > 0
                else 0.0,
                6,
            ),
        })

    return {
        "total_fraud_txns": total_fraud,
        "by_min_patterns": results,
    }


def _example_cases(
    edges: pd.DataFrame,
    suspicious_df: pd.DataFrame,
    G,
    n: int = 5,
) -> list[dict]:
    """Extrae ejemplos de cuentas con alertas y su realidad de fraude.

    Devuelve tanto cuentas con alertas que SÍ tienen fraude asociado
    (verdaderos positivos) como cuentas con alertas sin fraude
    (falsos positivos), para documentar la calidad de las señales.
    """
    if suspicious_df.empty:
        return []

    fraud_edges = edges[edges["isFraud"] == 1]
    fraud_accounts = set(fraud_edges["nameOrig"].unique()) | set(
        fraud_edges["nameDest"].unique()
    )

    cases = []
    # Verdaderos positivos (alerta + fraude real)
    tp_accounts = [
        acc for acc in suspicious_df["account"]
        if acc in fraud_accounts
    ]
    for acc in tp_accounts[:n]:
        row = suspicious_df[suspicious_df["account"] == acc].iloc[0]
        fraud_as_orig = int(
            fraud_edges[fraud_edges["nameOrig"] == acc]["isFraud"].sum()
        )
        fraud_as_dest = int(
            fraud_edges[fraud_edges["nameDest"] == acc]["isFraud"].sum()
        )
        cases.append({
            "account": acc,
            "account_type": row["account_type"],
            "patterns": row["patterns"],
            "pattern_count": int(row["pattern_count"]),
            "fraud_as_origin": fraud_as_orig,
            "fraud_as_destination": fraud_as_dest,
            "category": "verdadero_positivo",
        })

    # Falsos positivos (alerta sin fraude real)
    fp_accounts = [
        acc for acc in suspicious_df["account"]
        if acc not in fraud_accounts
    ]
    for acc in fp_accounts[:n]:
        row = suspicious_df[suspicious_df["account"] == acc].iloc[0]
        cases.append({
            "account": acc,
            "account_type": row["account_type"],
            "patterns": row["patterns"],
            "pattern_count": int(row["pattern_count"]),
            "fraud_as_origin": 0,
            "fraud_as_destination": 0,
            "category": "falso_positivo",
        })

    return cases


def _write_markdown(report: dict, path: Path) -> None:
    """Genera informe Markdown de la evaluación de alertas."""
    lines = [
        "# Evaluación de alertas de grafos contra etiquetas de fraude",
        "",
        "Informe generado por `scripts/evaluate_graph_alerts.py`.  Los datos",
        "provienen de PaySim (simulación); los resultados son exploratorios.",
        "",
        f"- Aristas analizadas: {report['edge_summary']['total_aristas']:,}.",
        f"- Transacciones fraudulentas: {report['edge_summary']['aristas_fraudulentas']:,}"
        f" ({report['edge_summary']['tasa_fraude']:.4%}).",
        "",
        "## Evaluación por patrón individual",
        "",
        "| Patrón | Cuentas marcadas | Con fraude | Precisión (cuenta) | "
        "Fraudes cubiertos | Cobertura |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    for p in report["pattern_evaluations"]:
        lines.append(
            f"| {p['pattern']} | {p['flagged_accounts']:,} | "
            f"{p.get('flagged_with_fraud', 0):,} | "
            f"{p.get('precision_at_account', 0):.4%} | "
            f"{p.get('fraud_txns_involving_flagged', 0):,} | "
            f"{p.get('coverage_fraud', 0):.4%} |"
        )

    lines += [
        "",
        "## Evaluación combinada (múltiples indicadores)",
        "",
        "| Mín. patrones | Cuentas | Con fraude | Precisión (cuenta) | "
        "Fraudes cubiertos | Cobertura | Precisión (txn) |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    combined = report["combined_evaluation"]
    for row in combined.get("by_min_patterns", []):
        lines.append(
            f"| {row['min_patterns']} | {row['flagged_accounts']:,} | "
            f"{row['flagged_with_fraud']:,} | "
            f"{row['precision_account']:.4%} | "
            f"{row['fraud_txns_covered']:,} | "
            f"{row['coverage_fraud']:.4%} | "
            f"{row['precision_txn']:.4%} |"
        )

    # Ejemplos
    if report.get("example_cases"):
        lines += [
            "",
            "## Ejemplos de casos",
            "",
            "### Verdaderos positivos (alerta + fraude real)",
            "",
        ]
        tp_cases = [c for c in report["example_cases"] if c["category"] == "verdadero_positivo"]
        fp_cases = [c for c in report["example_cases"] if c["category"] == "falso_positivo"]

        if tp_cases:
            lines += [
                "| Cuenta | Tipo | Patrones | Fraudes (origen) | Fraudes (destino) |",
                "| --- | --- | --- | ---: | ---: |",
            ]
            for c in tp_cases:
                patterns = ", ".join(c["patterns"]) if isinstance(c["patterns"], list) else str(c["patterns"])
                lines.append(
                    f"| `{c['account']}` | {c['account_type']} | "
                    f"{patterns} | {c['fraud_as_origin']} | "
                    f"{c['fraud_as_destination']} |"
                )
        else:
            lines.append("No se encontraron verdaderos positivos en esta muestra.")

        lines += [
            "",
            "### Falsos positivos (alerta sin fraude real)",
            "",
        ]
        if fp_cases:
            lines += [
                "| Cuenta | Tipo | Patrones | Nº patrones |",
                "| --- | --- | --- | ---: |",
            ]
            for c in fp_cases:
                patterns = ", ".join(c["patterns"]) if isinstance(c["patterns"], list) else str(c["patterns"])
                lines.append(
                    f"| `{c['account']}` | {c['account_type']} | "
                    f"{patterns} | {c['pattern_count']} |"
                )
        else:
            lines.append("No se encontraron falsos positivos en esta muestra.")

    lines += [
        "",
        "## Interpretación y limitaciones",
        "",
        "- **Cobertura** mide qué fracción de las transacciones fraudulentas",
        "  involucran al menos una cuenta detectada por el patrón.",
        "- **Precisión a nivel de cuenta** mide qué fracción de las cuentas",
        "  detectadas tiene al menos una transacción fraudulenta.",
        "- Los patrones son exploratorios y basados en percentiles estáticos.",
        "  Un patrón con alta cobertura pero baja precisión genera muchas",
        "  alertas falsas.",
        "- Los umbrales requieren calibración con datos reales y revisión",
        "  de expertos de dominio.",
        "- La evaluación no mide predicción: no hay separación temporal",
        "  ni partición de prueba.  Es una asociación cruzada, no una",
        "  estimación de desempeño predictivo.",
        "- `isFraud` es una etiqueta del simulador; en producción real,",
        "  las etiquetas de fraude pueden estar incompletas o sesgadas.",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluar alertas de grafos contra etiquetas de fraude"
    )
    parser.add_argument(
        "--input", type=Path,
        default=ROOT / "data/bronze/transactions/PS_20174392719_1491204439457_log.csv",
    )
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "artifacts/reports/graph/alert_evaluation.json",
    )
    parser.add_argument(
        "--markdown", type=Path,
        help="Ruta opcional para el informe Markdown",
    )
    parser.add_argument(
        "--limit", type=int,
        help="Máximo de filas a leer",
    )
    args = parser.parse_args()

    config = _load_config()
    limit = args.limit or config.get("sample_limit")

    # 1. Ingesta
    print("=" * 60)
    print("PASO 1: Lectura de aristas transaccionales")
    print("=" * 60)
    edges = read_transaction_edges(args.input, limit=limit)
    edge_summary = summarize_edges(edges)
    print(f"Aristas leídas: {len(edges):,}")
    print(f"Transacciones fraudulentas: {edge_summary['aristas_fraudulentas']:,} "
          f"({edge_summary['tasa_fraude']:.4%})")

    # 2. Construcción del grafo
    print("\n" + "=" * 60)
    print("PASO 2: Construcción del grafo y métricas")
    print("=" * 60)
    G = build_transaction_graph(edges)
    node_metrics = compute_node_metrics(G)
    print(f"Nodos: {G.number_of_nodes():,}")

    # 3. Evaluar cada patrón individualmente
    print("\n" + "=" * 60)
    print("PASO 3: Evaluación de cada patrón vs isFraud")
    print("=" * 60)
    fanout_pct = config.get("fanout_percentile", 95)
    fanin_pct = config.get("fanin_percentile", 95)
    flow_pct = config.get("flow_percentile", 95)

    fanout_df = detect_high_fanout(G, fanout_pct)
    fanin_df = detect_high_fanin(G, fanin_pct)
    flow_df = detect_net_flow_anomalies(node_metrics, flow_pct)
    high_value_df = detect_high_value_edges(G, config.get("high_value_percentile", 99))

    pattern_evaluations = []

    # Fan-out
    fanout_accounts = set(fanout_df["account"]) if not fanout_df.empty else set()
    eval_fanout = _evaluate_pattern_vs_fraud(edges, G, node_metrics, "high_fanout", fanout_accounts)
    pattern_evaluations.append(eval_fanout)
    print(f"  high_fanout: {eval_fanout['flagged_accounts']} cuentas, "
          f"cobertura {eval_fanout['coverage_fraud']:.4%}")

    # Fan-in
    fanin_accounts = set(fanin_df["account"]) if not fanin_df.empty else set()
    eval_fanin = _evaluate_pattern_vs_fraud(edges, G, node_metrics, "high_fanin", fanin_accounts)
    pattern_evaluations.append(eval_fanin)
    print(f"  high_fanin: {eval_fanin['flagged_accounts']} cuentas, "
          f"cobertura {eval_fanin['coverage_fraud']:.4%}")

    # Net flow anomaly
    flow_accounts = set(flow_df.index) if not flow_df.empty else set()
    eval_flow = _evaluate_pattern_vs_fraud(edges, G, node_metrics, "net_flow_anomaly", flow_accounts)
    pattern_evaluations.append(eval_flow)
    print(f"  net_flow_anomaly: {eval_flow['flagged_accounts']} cuentas, "
          f"cobertura {eval_flow['coverage_fraud']:.4%}")

    # High value edges (evaluación diferente: a nivel de arista)
    if not high_value_df.empty:
        hv_origins = set(high_value_df["origin"])
        hv_dests = set(high_value_df["destination"])
        hv_accounts = hv_origins | hv_dests
    else:
        hv_accounts = set()
    eval_hv = _evaluate_pattern_vs_fraud(edges, G, node_metrics, "high_value_edge", hv_accounts)
    pattern_evaluations.append(eval_hv)
    print(f"  high_value_edge: {eval_hv['flagged_accounts']} cuentas, "
          f"cobertura {eval_hv['coverage_fraud']:.4%}")

    # 4. Evaluación combinada
    print("\n" + "=" * 60)
    print("PASO 4: Evaluación combinada")
    print("=" * 60)
    suspicious = combine_suspicion_indicators(
        G, node_metrics, fanout_pct, fanin_pct, flow_pct
    )
    combined_eval = _evaluate_combined(edges, suspicious)
    for row in combined_eval.get("by_min_patterns", []):
        print(f"  >={row['min_patterns']} patrones: {row['flagged_accounts']} cuentas, "
              f"precisión {row['precision_account']:.4%}, "
              f"cobertura {row['coverage_fraud']:.4%}")

    # 5. Ejemplos de casos
    print("\n" + "=" * 60)
    print("PASO 5: Ejemplos de casos")
    print("=" * 60)
    cases = _example_cases(edges, suspicious, G, n=5)
    tp = [c for c in cases if c["category"] == "verdadero_positivo"]
    fp = [c for c in cases if c["category"] == "falso_positivo"]
    print(f"  Verdaderos positivos encontrados: {len(tp)}")
    print(f"  Falsos positivos encontrados: {len(fp)}")

    # 6. Reportes
    print("\n" + "=" * 60)
    print("PASO 6: Generación de reportes")
    print("=" * 60)

    report = {
        "schema_version": 1,
        "scope": "muestra" if limit else "archivo_completo",
        "row_limit": limit,
        "edge_summary": edge_summary,
        "pattern_evaluations": pattern_evaluations,
        "combined_evaluation": combined_eval,
        "example_cases": cases,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    print(f"JSON: {args.output}")

    if args.markdown:
        _write_markdown(report, args.markdown)
        print(f"Markdown: {args.markdown}")

    print("\n[OK] Evaluación de alertas completada.")


if __name__ == "__main__":
    main()
