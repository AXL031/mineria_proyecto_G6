"""Puntos de entrada de la API para el módulo de Grafos de Transacciones.

Expone endpoints para consulta de cuentas, subgrafos locales y ranking
de entidades según indicadores de red. Todos los resultados indican
explícitamente que provienen de simulación.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
import networkx as nx

from bankshield.features.graph import (
    build_transaction_graph,
    compute_graph_summary,
)
from bankshield.features.graph_patterns import (
    combine_suspicion_indicators,
    detect_circular_transactions,
    detect_high_fanin,
    detect_high_fanout,
    detect_high_value_edges,
)
from bankshield.ingestion.graph_dataset import read_transaction_edges, summarize_edges
from bankshield.services.graph import (
    query_account,
    query_subgraph,
    query_top_accounts,
)

router = APIRouter(prefix="/graphs", tags=["Grafos de Transacciones"])

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data/bronze/transactions/PS_20174392719_1491204439457_log.csv"
CONFIG_PATH = ROOT / "configs/graph.json"

# Estado en memoria para reutilización eficiente
_GRAPH_CACHE: dict[str, Any] = {
    "graph": None,
    "summary": None,
    "edges_summary": None,
}


def _get_or_load_graph(sample_limit: int = 100_000) -> nx.DiGraph:
    """Carga o retorna el grafo en memoria acotada."""
    if _GRAPH_CACHE["graph"] is not None:
        return _GRAPH_CACHE["graph"]

    if not DATA_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail="No se encontró el dataset de transacciones en Bronze",
        )

    edges = read_transaction_edges(DATA_PATH, limit=sample_limit)
    G = build_transaction_graph(edges)
    _GRAPH_CACHE["graph"] = G
    _GRAPH_CACHE["summary"] = compute_graph_summary(G)
    _GRAPH_CACHE["edges_summary"] = summarize_edges(edges)
    return G


@router.get("/summary")
def get_graph_summary(limit: int = Query(default=100_000, ge=1000, le=500_000)):
    """Obtiene el resumen global de la topología de la red transaccional."""
    _get_or_load_graph(limit)
    return {
        "status": "success",
        "simulation_data": True,
        "graph_summary": _GRAPH_CACHE["summary"],
        "edges_summary": _GRAPH_CACHE["edges_summary"],
    }


@router.get("/account/{account_id}")
def get_account_detail(account_id: str):
    """Consulta detallada de una cuenta (conexiones entrantes, salientes y flujos)."""
    G = _get_or_load_graph()
    try:
        data = query_account(G, account_id)
        return {"status": "success", "data": data}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/subgraph/{account_id}")
def get_account_subgraph(
    account_id: str,
    depth: int = Query(default=1, ge=1, le=2),
):
    """Extrae el subgrafo ego alrededor de una cuenta para visualización interactiva."""
    G = _get_or_load_graph()
    try:
        subgraph_data = query_subgraph(G, account_id, depth=depth)
        return {"status": "success", "data": subgraph_data}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/top")
def get_top_accounts(
    metric: str = Query(default="pagerank"),
    top_n: int = Query(default=20, ge=1, le=100),
):
    """Ranking de cuentas con mayor valor en métricas de centralidad y flujo."""
    G = _get_or_load_graph()
    try:
        ranked = query_top_accounts(G, metric=metric, top_n=top_n)
        return {
            "status": "success",
            "simulation_data": True,
            "metric": metric,
            "top_n": top_n,
            "results": ranked,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/patterns/suspicious")
def get_suspicious_patterns(
    fanout_pct: float = Query(default=95.0, ge=50.0, le=99.9),
    fanin_pct: float = Query(default=95.0, ge=50.0, le=99.9),
):
    """Detecta cuentas que activan múltiples patrones de sospecha en la red."""
    G = _get_or_load_graph()
    from bankshield.features.graph import compute_node_metrics
    node_metrics = compute_node_metrics(G)
    suspicious_df = combine_suspicion_indicators(
        G, node_metrics, fanout_percentile=fanout_pct, fanin_percentile=fanin_pct
    )
    results = suspicious_df.head(50).to_dict(orient="records")
    return {
        "status": "success",
        "simulation_data": True,
        "total_detected": len(suspicious_df),
        "results": results,
    }
