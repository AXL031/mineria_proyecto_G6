"""Detección de patrones sospechosos en la red de transacciones.

Cada detector devuelve un DataFrame con las cuentas afectadas, el patrón
detectado y un puntaje relativo.  Los umbrales iniciales son exploratorios
y deben calibrarse según la distribución observada.

Los datos provienen de una simulación (PaySim); cualquier resultado debe
rotularse como simulado y no implica fraude real.
"""

from __future__ import annotations

from typing import Any

import networkx as nx
import numpy as np
import pandas as pd


def detect_high_fanout(
    G: nx.DiGraph,
    threshold_percentile: float = 95,
) -> pd.DataFrame:
    """Cuentas que envían a un número inusual de destinos distintos.

    Un alto fan-out puede indicar distribución de fondos a múltiples
    cuentas (abanico), un patrón asociado a lavado de dinero en la
    literatura.

    Parameters
    ----------
    G : nx.DiGraph
        Grafo de transacciones con atributos de arista.
    threshold_percentile : float
        Percentil para definir "inusual" (por defecto 95).

    Returns
    -------
    pd.DataFrame
        Cuentas con fan-out superior al umbral.
    """
    out_degrees = {node: G.out_degree(node) for node in G.nodes()}
    if not out_degrees:
        return pd.DataFrame()

    values = list(out_degrees.values())
    threshold = float(np.percentile(values, threshold_percentile))

    records = []
    for node, degree in out_degrees.items():
        if degree > threshold:
            total_sent = sum(
                G[node][succ].get("total_amount", 0)
                for succ in G.successors(node)
            )
            fraud_sent = sum(
                G[node][succ].get("fraud_count", 0)
                for succ in G.successors(node)
            )
            records.append({
                "account": node,
                "pattern": "high_fanout",
                "out_degree": degree,
                "threshold": threshold,
                "total_amount_sent": total_sent,
                "fraud_count": fraud_sent,
                "account_type": G.nodes[node].get("account_type", "desconocido"),
            })

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.sort_values("out_degree", ascending=False)
    return df


def detect_high_fanin(
    G: nx.DiGraph,
    threshold_percentile: float = 95,
) -> pd.DataFrame:
    """Cuentas que reciben de un número inusual de orígenes distintos.

    Un alto fan-in puede indicar concentración de fondos (embudo),
    el paso inverso del patrón de abanico.

    Parameters
    ----------
    G : nx.DiGraph
        Grafo de transacciones.
    threshold_percentile : float
        Percentil para definir "inusual".

    Returns
    -------
    pd.DataFrame
        Cuentas con fan-in superior al umbral.
    """
    in_degrees = {node: G.in_degree(node) for node in G.nodes()}
    if not in_degrees:
        return pd.DataFrame()

    values = list(in_degrees.values())
    threshold = float(np.percentile(values, threshold_percentile))

    records = []
    for node, degree in in_degrees.items():
        if degree > threshold:
            total_received = sum(
                G[pred][node].get("total_amount", 0)
                for pred in G.predecessors(node)
            )
            fraud_received = sum(
                G[pred][node].get("fraud_count", 0)
                for pred in G.predecessors(node)
            )
            records.append({
                "account": node,
                "pattern": "high_fanin",
                "in_degree": degree,
                "threshold": threshold,
                "total_amount_received": total_received,
                "fraud_count": fraud_received,
                "account_type": G.nodes[node].get("account_type", "desconocido"),
            })

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.sort_values("in_degree", ascending=False)
    return df


def detect_circular_transactions(
    G: nx.DiGraph,
    max_length: int = 4,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Busca ciclos cortos en el grafo que podrían indicar circularidad.

    La presencia de un ciclo no implica fraude; muchas relaciones
    comerciales legítimas son bidireccionales.  Este detector identifica
    candidatos para revisión manual.

    Parameters
    ----------
    G : nx.DiGraph
        Grafo de transacciones.
    max_length : int
        Longitud máxima del ciclo a buscar (por defecto 4).
    limit : int
        Máximo número de ciclos a reportar.

    Returns
    -------
    list[dict]
        Lista de ciclos encontrados con sus atributos.
    """
    if max_length < 2:
        raise ValueError("La longitud mínima de ciclo es 2")

    cycles = []
    seen = set()

    try:
        for cycle in nx.simple_cycles(G, length_bound=max_length):
            if len(cycles) >= limit:
                break

            # Normalizar para evitar duplicados rotacionales
            key = tuple(sorted(cycle))
            if key in seen:
                continue
            seen.add(key)

            # Calcular monto total del ciclo
            total_amount = 0.0
            fraud_in_cycle = 0
            for i in range(len(cycle)):
                u = cycle[i]
                v = cycle[(i + 1) % len(cycle)]
                if G.has_edge(u, v):
                    edge = G[u][v]
                    total_amount += edge.get("total_amount", 0)
                    fraud_in_cycle += edge.get("fraud_count", 0)

            cycles.append({
                "cycle": cycle,
                "length": len(cycle),
                "total_amount": total_amount,
                "fraud_count": fraud_in_cycle,
            })
    except Exception:
        # simple_cycles puede ser costoso; capturar errores de memoria
        pass

    return sorted(cycles, key=lambda c: c["total_amount"], reverse=True)


def detect_high_value_edges(
    G: nx.DiGraph,
    threshold_percentile: float = 99,
) -> pd.DataFrame:
    """Pares de cuentas con montos totales excepcionalmente altos.

    Parameters
    ----------
    G : nx.DiGraph
        Grafo de transacciones.
    threshold_percentile : float
        Percentil del monto total para considerar un par como "alto valor".

    Returns
    -------
    pd.DataFrame
        Pares de cuentas con monto total superior al umbral.
    """
    edge_data = []
    for u, v, data in G.edges(data=True):
        edge_data.append({
            "origin": u,
            "destination": v,
            "total_amount": data.get("total_amount", 0),
            "transaction_count": data.get("weight", 0),
            "fraud_count": data.get("fraud_count", 0),
            "types": data.get("types", []),
        })

    if not edge_data:
        return pd.DataFrame()

    df = pd.DataFrame(edge_data)
    threshold = float(np.percentile(df["total_amount"], threshold_percentile))
    high_value = df[df["total_amount"] > threshold].copy()
    high_value["threshold"] = threshold
    high_value["pattern"] = "high_value_edge"

    return high_value.sort_values("total_amount", ascending=False)


def detect_net_flow_anomalies(
    node_metrics: pd.DataFrame,
    threshold_percentile: float = 95,
) -> pd.DataFrame:
    """Cuentas con flujo neto (recibido - enviado) anormalmente alto o bajo.

    Un flujo neto extremo puede indicar cuentas acumuladoras o
    distribuidoras.

    Parameters
    ----------
    node_metrics : pd.DataFrame
        DataFrame de métricas por nodo (de ``compute_node_metrics``).
    threshold_percentile : float
        Percentil para ambos extremos.

    Returns
    -------
    pd.DataFrame
        Cuentas con flujo neto anómalo.
    """
    if "net_flow" not in node_metrics.columns:
        raise ValueError("Se requiere la columna 'net_flow' en las métricas")

    flow = node_metrics["net_flow"]
    upper = float(np.percentile(flow, threshold_percentile))
    lower = float(np.percentile(flow, 100 - threshold_percentile))

    anomalies = node_metrics[
        (flow > upper) | (flow < lower)
    ].copy()
    anomalies["pattern"] = "net_flow_anomaly"
    anomalies["upper_threshold"] = upper
    anomalies["lower_threshold"] = lower

    return anomalies.sort_values("net_flow", key=abs, ascending=False)


def combine_suspicion_indicators(
    G: nx.DiGraph,
    node_metrics: pd.DataFrame,
    fanout_percentile: float = 95,
    fanin_percentile: float = 95,
    flow_percentile: float = 95,
) -> pd.DataFrame:
    """Combina múltiples indicadores en un resumen de sospecha por cuenta.

    Asigna un puntaje simple basado en cuántos patrones dispara cada
    cuenta.  Este puntaje es exploratorio y no constituye una evaluación
    de riesgo real.

    Returns
    -------
    pd.DataFrame
        Una fila por cuenta sospechosa con los indicadores activos.
    """
    fanout = detect_high_fanout(G, fanout_percentile)
    fanin = detect_high_fanin(G, fanin_percentile)
    flow_anomalies = detect_net_flow_anomalies(node_metrics, flow_percentile)

    # Recolectar indicadores por cuenta
    indicators: dict[str, dict] = {}

    for _, row in fanout.iterrows():
        acc = row["account"]
        indicators.setdefault(acc, {"patterns": [], "fraud_count": 0})
        indicators[acc]["patterns"].append("high_fanout")
        indicators[acc]["fraud_count"] += row.get("fraud_count", 0)

    for _, row in fanin.iterrows():
        acc = row["account"]
        indicators.setdefault(acc, {"patterns": [], "fraud_count": 0})
        indicators[acc]["patterns"].append("high_fanin")
        indicators[acc]["fraud_count"] += row.get("fraud_count", 0)

    for acc, row in flow_anomalies.iterrows():
        indicators.setdefault(acc, {"patterns": [], "fraud_count": 0})
        indicators[acc]["patterns"].append("net_flow_anomaly")

    if not indicators:
        return pd.DataFrame()

    records = []
    for account, info in indicators.items():
        node_data = G.nodes.get(account, {})
        records.append({
            "account": account,
            "account_type": node_data.get("account_type", "desconocido"),
            "patterns": info["patterns"],
            "pattern_count": len(info["patterns"]),
            "fraud_count": info["fraud_count"],
            "pagerank": float(node_metrics.loc[account, "pagerank"])
            if account in node_metrics.index
            else 0.0,
        })

    df = pd.DataFrame(records)
    df = df.sort_values("pattern_count", ascending=False)
    return df
