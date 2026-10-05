"""Construcción de grafo dirigido de transacciones y métricas de red.

Construye un ``nx.DiGraph`` con peso agregado a partir de las aristas
transaccionales.  Los identificadores de cuentas provienen de una
simulación (PaySim) y los resultados deben rotularse como simulados.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Construcción del grafo
# ---------------------------------------------------------------------------

def build_transaction_graph(edges: pd.DataFrame) -> nx.DiGraph:
    """Construye un grafo dirigido con aristas agregadas por par de cuentas.

    Cada arista ``(nameOrig, nameDest)`` almacena atributos agregados:

    - ``weight``: número total de transacciones entre el par.
    - ``total_amount``: suma de montos.
    - ``mean_amount``: monto promedio.
    - ``max_amount``: monto máximo.
    - ``fraud_count``: número de transacciones fraudulentas.
    - ``types``: conjunto de tipos de transacción observados.
    - ``steps``: lista de pasos temporales de las transacciones.

    Parameters
    ----------
    edges : pd.DataFrame
        DataFrame con columnas ``nameOrig``, ``nameDest``, ``amount``,
        ``type``, ``step``, ``isFraud``.

    Returns
    -------
    nx.DiGraph
        Grafo dirigido con atributos de arista agregados.
    """
    required = {"nameOrig", "nameDest", "amount", "type", "step", "isFraud"}
    missing = required - set(edges.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {sorted(missing)}")

    if edges.empty:
        raise ValueError("El DataFrame de aristas está vacío")

    # Agregar por par (origen, destino)
    grouped = edges.groupby(["nameOrig", "nameDest"], observed=True)

    G = nx.DiGraph()

    for (orig, dest), group in grouped:
        G.add_edge(
            orig,
            dest,
            weight=len(group),
            total_amount=float(group["amount"].sum()),
            mean_amount=float(group["amount"].mean()),
            max_amount=float(group["amount"].max()),
            fraud_count=int(group["isFraud"].sum()),
            types=sorted(group["type"].unique().tolist()),
            steps=sorted(group["step"].unique().tolist()),
        )

    # Marcar nodos con su rol predominante
    orig_counts = edges["nameOrig"].value_counts()
    dest_counts = edges["nameDest"].value_counts()
    for node in G.nodes():
        sent = int(orig_counts.get(node, 0))
        received = int(dest_counts.get(node, 0))
        G.nodes[node]["transactions_sent"] = sent
        G.nodes[node]["transactions_received"] = received
        # Prefijo C = cliente, M = comercio (convención PaySim)
        G.nodes[node]["account_type"] = (
            "comercio" if str(node).startswith("M") else "cliente"
        )

    return G


# ---------------------------------------------------------------------------
# Métricas a nivel de nodo
# ---------------------------------------------------------------------------

def compute_node_metrics(G: nx.DiGraph) -> pd.DataFrame:
    """Calcula indicadores de red por cuenta.

    Returns
    -------
    pd.DataFrame
        Una fila por cuenta con métricas de centralidad y actividad.
    """
    if G.number_of_nodes() == 0:
        raise ValueError("El grafo está vacío")

    records: list[dict[str, Any]] = []

    in_deg = dict(G.in_degree(weight="weight"))
    out_deg = dict(G.out_degree(weight="weight"))

    # Centralidad de grado (sin pesos, normalizada)
    in_deg_norm = nx.in_degree_centrality(G)
    out_deg_norm = nx.out_degree_centrality(G)

    # Pagerank con pesos (con fallback manual si scipy no está disponible)
    try:
        pagerank = nx.pagerank(G, weight="weight", max_iter=100)
    except (nx.PowerIterationFailedConvergence, ModuleNotFoundError, ImportError):
        # Fallback a power iteration simple usando solo numpy / dict
        nodes = list(G.nodes())
        n = len(nodes)
        if n == 0:
            pagerank = {}
        else:
            alpha = 0.85
            pagerank = {u: 1.0 / n for u in nodes}
            # out-weights
            out_weights = {u: sum(G[u][v].get("weight", 1) for v in G.successors(u)) for u in nodes}
            for _ in range(100):
                new_pr = {u: (1.0 - alpha) / n for u in nodes}
                dangling_sum = alpha * sum(pagerank[u] for u in nodes if out_weights[u] == 0)
                for u in nodes:
                    new_pr[u] += dangling_sum / n
                    if out_weights[u] > 0:
                        for v in G.successors(u):
                            w = G[u][v].get("weight", 1)
                            new_pr[v] += alpha * pagerank[u] * (w / out_weights[u])
                # Check convergence
                err = sum(abs(new_pr[u] - pagerank[u]) for u in nodes)
                pagerank = new_pr
                if err < 1e-6:
                    break

    for node in G.nodes():
        data = G.nodes[node]
        # Monto total enviado y recibido
        total_sent = sum(
            G[node][succ].get("total_amount", 0) for succ in G.successors(node)
        )
        total_received = sum(
            G[pred][node].get("total_amount", 0) for pred in G.predecessors(node)
        )
        # Cantidad de vecinos distintos
        n_successors = G.out_degree(node)  # sin peso = vecinos distintos
        n_predecessors = G.in_degree(node)

        records.append({
            "account": node,
            "account_type": data.get("account_type", "desconocido"),
            "transactions_sent": data.get("transactions_sent", 0),
            "transactions_received": data.get("transactions_received", 0),
            "weighted_in_degree": in_deg.get(node, 0),
            "weighted_out_degree": out_deg.get(node, 0),
            "in_degree_centrality": in_deg_norm.get(node, 0.0),
            "out_degree_centrality": out_deg_norm.get(node, 0.0),
            "pagerank": pagerank.get(node, 0.0),
            "unique_destinations": n_successors,
            "unique_sources": n_predecessors,
            "total_amount_sent": total_sent,
            "total_amount_received": total_received,
            "net_flow": total_received - total_sent,
        })

    df = pd.DataFrame(records).set_index("account")
    df = df.sort_values("pagerank", ascending=False)
    return df


# ---------------------------------------------------------------------------
# Resumen a nivel de grafo
# ---------------------------------------------------------------------------

def compute_graph_summary(G: nx.DiGraph) -> dict:
    """Calcula estadísticas globales del grafo.

    Incluye densidad, componentes, y distribución de grados.
    """
    if G.number_of_nodes() == 0:
        raise ValueError("El grafo está vacío")

    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()

    # Componentes débilmente conexos
    weak_components = list(nx.weakly_connected_components(G))
    largest_wcc = max(weak_components, key=len)

    # Distribución de grados (sin peso)
    out_degrees = [d for _, d in G.out_degree()]
    in_degrees = [d for _, d in G.in_degree()]

    # Contar nodos por tipo
    type_counts = defaultdict(int)
    for _, data in G.nodes(data=True):
        type_counts[data.get("account_type", "desconocido")] += 1

    # Aristas con fraude
    fraud_edges = sum(
        1 for _, _, d in G.edges(data=True) if d.get("fraud_count", 0) > 0
    )
    total_fraud_txns = sum(
        d.get("fraud_count", 0) for _, _, d in G.edges(data=True)
    )

    return {
        "nodos": n_nodes,
        "aristas_unicas": n_edges,
        "densidad": nx.density(G),
        "componentes_debiles": len(weak_components),
        "nodos_mayor_componente": len(largest_wcc),
        "porcentaje_mayor_componente": len(largest_wcc) / n_nodes,
        "grado_salida_medio": float(np.mean(out_degrees)),
        "grado_salida_maximo": int(np.max(out_degrees)),
        "grado_entrada_medio": float(np.mean(in_degrees)),
        "grado_entrada_maximo": int(np.max(in_degrees)),
        "nodos_por_tipo": dict(type_counts),
        "pares_con_fraude": fraud_edges,
        "transacciones_fraudulentas_total": total_fraud_txns,
        "simulacion": True,
        "nota": "Datos de PaySim; los resultados son simulados.",
    }


# ---------------------------------------------------------------------------
# Extracción de subgrafos
# ---------------------------------------------------------------------------

def extract_subgraph(
    G: nx.DiGraph, account_id: str, depth: int = 1
) -> nx.DiGraph:
    """Extrae el subgrafo ego alrededor de una cuenta.

    Parameters
    ----------
    account_id : str
        Identificador de la cuenta central (e.g. ``C1231006815``).
    depth : int
        Profundidad de la vecindad (1 = vecinos directos).

    Returns
    -------
    nx.DiGraph
        Subgrafo con los mismos atributos de arista y nodo.
    """
    if account_id not in G:
        raise ValueError(f"La cuenta '{account_id}' no existe en el grafo")
    if depth < 1:
        raise ValueError("La profundidad debe ser al menos 1")

    # Recolectar nodos dentro de la profundidad especificada
    nodes = {account_id}
    frontier = {account_id}

    for _ in range(depth):
        next_frontier = set()
        for node in frontier:
            next_frontier.update(G.successors(node))
            next_frontier.update(G.predecessors(node))
        nodes.update(next_frontier)
        frontier = next_frontier

    subgraph = G.subgraph(nodes).copy()
    # Marcar el nodo central
    if account_id in subgraph:
        subgraph.nodes[account_id]["is_center"] = True

    return subgraph
