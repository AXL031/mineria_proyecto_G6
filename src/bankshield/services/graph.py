"""Servicio de consulta de grafos de transacciones.

Proporciona una interfaz de consulta sobre el grafo construido,
diseñada para ser consumida por endpoints de la API.

Los resultados provienen de datos simulados (PaySim) y deben
presentarse como tales en cualquier interfaz.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx
import pandas as pd

from bankshield.evaluation.graph import SCHEMA_VERSION as COMPARISON_SCHEMA_VERSION
from bankshield.features.graph import (
    compute_node_metrics,
    extract_subgraph,
)


def query_account(G: nx.DiGraph, account_id: str) -> dict[str, Any]:
    """Consulta completa de una cuenta: conexiones, métricas e indicadores.

    Parameters
    ----------
    G : nx.DiGraph
        Grafo de transacciones construido.
    account_id : str
        Identificador de la cuenta a consultar.

    Returns
    -------
    dict
        Información completa de la cuenta con el esquema documentado
        en ``docs/grafos/contrato-variables.md``.
    """
    if account_id not in G:
        raise ValueError(f"La cuenta '{account_id}' no existe en el grafo")

    node_data = G.nodes[account_id]

    # Conexiones salientes
    outgoing = []
    for succ in G.successors(account_id):
        edge = G[account_id][succ]
        outgoing.append({
            "destination": succ,
            "transaction_count": edge.get("weight", 0),
            "total_amount": edge.get("total_amount", 0),
            "mean_amount": edge.get("mean_amount", 0),
            "fraud_count": edge.get("fraud_count", 0),
            "types": edge.get("types", []),
        })

    # Conexiones entrantes
    incoming = []
    for pred in G.predecessors(account_id):
        edge = G[pred][account_id]
        incoming.append({
            "origin": pred,
            "transaction_count": edge.get("weight", 0),
            "total_amount": edge.get("total_amount", 0),
            "mean_amount": edge.get("mean_amount", 0),
            "fraud_count": edge.get("fraud_count", 0),
            "types": edge.get("types", []),
        })

    total_sent = sum(c["total_amount"] for c in outgoing)
    total_received = sum(c["total_amount"] for c in incoming)

    return {
        "account": account_id,
        "account_type": node_data.get("account_type", "desconocido"),
        "transactions_sent": node_data.get("transactions_sent", 0),
        "transactions_received": node_data.get("transactions_received", 0),
        "unique_destinations": len(outgoing),
        "unique_sources": len(incoming),
        "total_amount_sent": total_sent,
        "total_amount_received": total_received,
        "net_flow": total_received - total_sent,
        "outgoing_connections": sorted(
            outgoing, key=lambda c: c["total_amount"], reverse=True
        ),
        "incoming_connections": sorted(
            incoming, key=lambda c: c["total_amount"], reverse=True
        ),
        "simulation_data": True,
    }


def query_subgraph(
    G: nx.DiGraph, account_id: str, depth: int = 1
) -> dict[str, Any]:
    """Consulta de subgrafo alrededor de una cuenta para visualización.

    Devuelve nodos y aristas en un formato compatible con librerías
    de visualización (e.g. D3, vis.js, Streamlit).

    Parameters
    ----------
    G : nx.DiGraph
        Grafo completo de transacciones.
    account_id : str
        Cuenta central del subgrafo.
    depth : int
        Profundidad de la vecindad (1 = vecinos directos).

    Returns
    -------
    dict
        Nodos y aristas del subgrafo con sus atributos.
    """
    sub = extract_subgraph(G, account_id, depth)

    nodes = []
    for node, data in sub.nodes(data=True):
        nodes.append({
            "id": node,
            "account_type": data.get("account_type", "desconocido"),
            "is_center": data.get("is_center", False),
            "transactions_sent": data.get("transactions_sent", 0),
            "transactions_received": data.get("transactions_received", 0),
        })

    edges = []
    for u, v, data in sub.edges(data=True):
        edges.append({
            "source": u,
            "target": v,
            "weight": data.get("weight", 0),
            "total_amount": data.get("total_amount", 0),
            "fraud_count": data.get("fraud_count", 0),
            "types": data.get("types", []),
        })

    return {
        "center_account": account_id,
        "depth": depth,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
        "simulation_data": True,
    }


def query_top_accounts(
    G: nx.DiGraph,
    metric: str = "pagerank",
    top_n: int = 20,
) -> list[dict[str, Any]]:
    """Devuelve las cuentas con mayor valor en una métrica de red.

    Parameters
    ----------
    G : nx.DiGraph
        Grafo de transacciones.
    metric : str
        Nombre de la métrica para ordenar (columna del DataFrame
        producido por ``compute_node_metrics``).
    top_n : int
        Número de cuentas a devolver.

    Returns
    -------
    list[dict]
        Lista de cuentas con sus métricas, ordenadas de mayor a menor.
    """
    valid_metrics = {
        "pagerank", "weighted_in_degree", "weighted_out_degree",
        "in_degree_centrality", "out_degree_centrality",
        "unique_destinations", "unique_sources",
        "total_amount_sent", "total_amount_received", "net_flow",
    }
    if metric not in valid_metrics:
        raise ValueError(
            f"Métrica '{metric}' no válida. Opciones: {sorted(valid_metrics)}"
        )

    node_df = compute_node_metrics(G)
    top = node_df.nlargest(top_n, metric)

    results = []
    for account, row in top.iterrows():
        results.append({
            "account": account,
            "account_type": row["account_type"],
            metric: float(row[metric]),
            "transactions_sent": int(row["transactions_sent"]),
            "transactions_received": int(row["transactions_received"]),
        })

    return results


# ---------------------------------------------------------------------------
# Comparación de alertas de red (reporte preparado)
# ---------------------------------------------------------------------------

COMPARISON_REQUIRED_KEYS = (
    "schema_version", "analysis_id", "scope", "sample", "universe",
    "comparisons", "limitations",
)


class ComparisonReportError(Exception):
    """El reporte de comparación no puede servirse para la consulta pedida.

    ``code`` distingue el motivo: ``report_missing``, ``report_invalid``,
    ``incompatible_version`` o ``sample_mismatch``.
    """

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def load_comparison_report(path: Path) -> dict[str, Any]:
    """Carga el reporte preparado sin construir ni recalcular el grafo."""
    path = Path(path)
    if not path.is_file():
        raise ComparisonReportError(
            "report_missing",
            "No existe el reporte de comparación de grafos. Genérelo con "
            "scripts/evaluate_graph_alerts.py --comparison-output.",
        )
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ComparisonReportError(
            "report_invalid", f"No se pudo leer el reporte de comparación: {exc}"
        ) from exc
    if not isinstance(report, dict):
        raise ComparisonReportError("report_invalid", "El reporte de comparación es inválido.")
    return report


def comparison_response(report: dict[str, Any], limit: int) -> dict[str, Any]:
    """Respuesta de la API para la muestra pedida, sin servir otro universo.

    El ``limit`` debe coincidir con el tamaño de muestra *solicitado* que consta
    en el reporte, no solo con las filas efectivamente leídas.
    """
    version = report.get("schema_version")
    if version != COMPARISON_SCHEMA_VERSION:
        raise ComparisonReportError(
            "incompatible_version",
            f"El reporte tiene la versión de esquema {version!r}; se esperaba "
            f"{COMPARISON_SCHEMA_VERSION}. Regenere la comparación.",
        )
    missing = [key for key in COMPARISON_REQUIRED_KEYS if key not in report]
    if missing:
        raise ComparisonReportError(
            "report_invalid", f"Al reporte le faltan campos: {missing}. Regenere la comparación."
        )
    sample = report["sample"]
    requested = sample.get("requested_limit") if isinstance(sample, dict) else None
    if requested != limit:
        raise ComparisonReportError(
            "sample_mismatch",
            f"El reporte corresponde a una muestra solicitada de {requested!r} filas, "
            f"no de {limit:,}. Regenere la comparación para esa muestra.",
        )
    return {
        "status": "success",
        "schema_version": report["schema_version"],
        "analysis_id": report["analysis_id"],
        "simulation_data": True,
        "scope": report["scope"],
        "sample": sample,
        "universe_size": report["universe"].get("size"),
        "comparisons": report["comparisons"],
        "limitations": report["limitations"],
    }
