"""Comparación justa de alertas de red frente a una referencia por volumen.

Compara, sobre la **misma muestra** y el **mismo universo de cuentas**, el
ranking de indicadores de red con una referencia que solo usa el volumen
transaccional.  Ambos métodos seleccionan exactamente ``k`` cuentas por cada
presupuesto efectivo y se miden con las mismas métricas.

Reglas de diseño (ver ``docs/encargos/rhamses.md``, RHA-01):

- Ningún ranking usa ``fraud_count``, ``isFraud`` ni ``isFlaggedFraud``.  Las
  etiquetas solo se emplean *después* de elegir las cuentas, para medir.
  ``combine_suspicion_indicators`` expone ``fraud_count`` solo con fines
  descriptivos; aquí se toma únicamente ``pattern_count`` y se ignora aquella
  columna.
- La evaluación es exploratoria y retrospectiva sobre la muestra observada: no
  es una predicción temporal ni evidencia sobre la red completa.
- Los datos provienen de una simulación (PaySim).
"""

from __future__ import annotations

import hashlib
import platform
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd

from bankshield.features.graph_patterns import combine_suspicion_indicators

SCHEMA_VERSION = 1
SCOPE = "sample_retrospective"
NETWORK_METHOD = "network_indicators"
REFERENCE_METHOD = "volume_reference"

# Columnas que definen la huella de las filas usadas.
FINGERPRINT_COLUMNS = ("step", "type", "amount", "nameOrig", "nameDest", "isFraud")

# Métricas de razón: (clave, descripción)
RATIO_METRICS = (
    "account_precision",
    "account_recall",
    "covered_transaction_precision",
    "fraud_coverage",
)

# Decimales con que se comparan PageRank y volumen al ordenar.  Evita que
# diferencias de punto flotante del orden de 1e-17 rompan empates reales, que
# deben resolverse por identificador de cuenta.
PAGERANK_SORT_DECIMALS = 12
VOLUME_SORT_DECIMALS = 6

SAMPLING_RULE = (
    "Prefijo del archivo: las primeras N filas en su orden original. No es una "
    "muestra aleatoria ni se afirma que sea representativa del dataset."
)

LIMITATIONS = (
    "Evaluación exploratoria y retrospectiva sobre la misma muestra observada; "
    "no es una predicción temporal ni evidencia sobre la red completa.",
    "La muestra es un prefijo del archivo, no una muestra aleatoria; no se "
    "afirma que sea representativa del dataset.",
    "Los datos provienen de PaySim (simulación); isFraud es una etiqueta del "
    "simulador y los resultados no describen fraude real.",
    "Los rankings no usan etiquetas de fraude; las etiquetas solo se emplean "
    "para medir las cuentas ya seleccionadas. combine_suspicion_indicators "
    "incluye fraud_count con fines descriptivos y no se usa como puntaje.",
    "No se selecciona el k ganador según el fraude observado y no se exige "
    "que el método de red supere a la referencia por volumen.",
    "Los percentiles de los indicadores están fijados en la configuración "
    "antes de evaluar y no se calibran con las etiquetas.",
    "Comunidades y evaluación predictiva temporal de grafos quedan fuera de "
    "esta comparación.",
)

POPULATION_LIMITS = (
    "El universo contiene solo las cuentas que aparecen como origen o destino "
    "en las filas de la muestra; no incluye cuentas sin transacciones en ella.",
    "En PaySim los comercios (prefijo M) solo aparecen como destino.",
)


# ---------------------------------------------------------------------------
# Configuración y presupuestos
# ---------------------------------------------------------------------------

def comparison_config(graph_config: Mapping[str, Any]) -> dict[str, Any]:
    """Valida y devuelve el bloque ``comparison`` de ``configs/graph.json``."""
    raw = graph_config.get("comparison") if graph_config else None
    if not isinstance(raw, Mapping):
        raise ValueError("Falta el bloque 'comparison' en la configuración de grafos")

    budgets = validate_budgets(raw.get("budgets"))
    default_limit = raw.get("default_sample_limit")
    if isinstance(default_limit, bool) or not isinstance(default_limit, int) or default_limit < 1:
        raise ValueError("default_sample_limit debe ser un entero positivo")

    percentiles: dict[str, float] = {}
    for name in ("fanout_percentile", "fanin_percentile", "flow_percentile"):
        value = raw.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value < 100:
            raise ValueError(f"{name} debe estar entre 0 y 100 (exclusivo)")
        percentiles[name] = float(value)

    return {
        "default_sample_limit": default_limit,
        "budgets": budgets,
        **percentiles,
    }


def validate_budgets(budgets: Sequence[int] | None) -> list[int]:
    """Presupuestos solicitados: enteros positivos, sin repetir, en orden dado."""
    if budgets is None or isinstance(budgets, (str, bytes)) or len(budgets) == 0:
        raise ValueError("Se requiere al menos un presupuesto de cuentas")
    cleaned: list[int] = []
    for budget in budgets:
        if isinstance(budget, bool) or not isinstance(budget, (int, np.integer)) or budget < 1:
            raise ValueError("Cada presupuesto debe ser un entero positivo")
        if int(budget) not in cleaned:
            cleaned.append(int(budget))
    return cleaned


def effective_budgets(
    requested: Sequence[int], universe_size: int
) -> tuple[list[int], dict[int, int]]:
    """Presupuestos efectivos ``min(k, N)`` sin duplicados.

    Returns
    -------
    tuple
        Lista ordenada de presupuestos efectivos distintos y el mapa
        ``solicitado -> efectivo``.  Con universo vacío no hay presupuestos.
    """
    if universe_size < 0:
        raise ValueError("El tamaño del universo no puede ser negativo")
    if universe_size == 0:
        return [], {}
    mapping = {int(k): min(int(k), universe_size) for k in requested}
    return sorted(set(mapping.values())), mapping


# ---------------------------------------------------------------------------
# Huellas de la fuente y de la muestra
# ---------------------------------------------------------------------------

def file_sha256(path: Path, block_size: int = 1 << 20) -> str:
    """SHA-256 de un archivo leído en bloques."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest()


def edges_fingerprint(edges: pd.DataFrame) -> str:
    """SHA-256 de las filas usadas, en su orden y con columnas fijas."""
    missing = set(FINGERPRINT_COLUMNS) - set(edges.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {sorted(missing)}")
    payload = edges.loc[:, list(FINGERPRINT_COLUMNS)].to_csv(
        index=False, lineterminator="\n"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Universo y rankings
# ---------------------------------------------------------------------------

def build_universe(edges: pd.DataFrame) -> list[str]:
    """Todas las cuentas origen y destino de la muestra, sin filtrar por fraude."""
    if edges.empty:
        return []
    accounts = set(edges["nameOrig"].astype(str)) | set(edges["nameDest"].astype(str))
    return sorted(accounts)


def _check_universe(universe: list[str], G: nx.DiGraph, node_metrics: pd.DataFrame) -> None:
    if set(universe) != set(map(str, G.nodes())):
        raise ValueError("El grafo no contiene exactamente las cuentas de la muestra")
    if not set(universe) <= set(map(str, node_metrics.index)):
        raise ValueError("Las métricas de nodo no cubren todo el universo")


def rank_network(
    universe: list[str],
    G: nx.DiGraph,
    node_metrics: pd.DataFrame,
    *,
    fanout_percentile: float,
    fanin_percentile: float,
    flow_percentile: float,
) -> pd.DataFrame:
    """Ranking del método de red sobre todo el universo.

    Orden: ``pattern_count`` descendente, PageRank descendente y
    ``account_id`` ascendente.  Las cuentas sin indicador activo tienen cero y
    permanecen en el universo.  No se usa ninguna etiqueta de fraude.
    """
    if not universe:
        return pd.DataFrame(columns=["account", "pattern_count", "pagerank", "rank"])
    _check_universe(universe, G, node_metrics)

    indicators = combine_suspicion_indicators(
        G, node_metrics, fanout_percentile, fanin_percentile, flow_percentile
    )
    counts: dict[str, int] = {}
    if not indicators.empty:
        # Solo se toma el conteo de indicadores; fraud_count se descarta.
        counts = {
            str(row.account): int(row.pattern_count)
            for row in indicators.loc[:, ["account", "pattern_count"]].itertuples()
        }

    frame = pd.DataFrame({"account": universe})
    frame["pattern_count"] = frame["account"].map(counts).fillna(0).astype(int)
    frame["pagerank"] = [float(node_metrics.at[a, "pagerank"]) for a in universe]
    frame["_pagerank_key"] = frame["pagerank"].round(PAGERANK_SORT_DECIMALS)
    frame = frame.sort_values(
        ["pattern_count", "_pagerank_key", "account"],
        ascending=[False, False, True],
        kind="mergesort",
    ).drop(columns="_pagerank_key")
    frame = frame.reset_index(drop=True)
    frame["rank"] = np.arange(1, len(frame) + 1)
    return frame


def rank_volume(
    universe: list[str], G: nx.DiGraph, node_metrics: pd.DataFrame
) -> pd.DataFrame:
    """Referencia por volumen sobre los mismos nodos y aristas.

    Orden: ``total_amount_sent + total_amount_received`` descendente y
    ``account_id`` ascendente.  No usa etiquetas.
    """
    if not universe:
        return pd.DataFrame(columns=["account", "total_volume", "rank"])
    _check_universe(universe, G, node_metrics)

    frame = pd.DataFrame({"account": universe})
    frame["total_volume"] = [
        float(node_metrics.at[a, "total_amount_sent"])
        + float(node_metrics.at[a, "total_amount_received"])
        for a in universe
    ]
    frame["_volume_key"] = frame["total_volume"].round(VOLUME_SORT_DECIMALS)
    frame = frame.sort_values(
        ["_volume_key", "account"], ascending=[False, True], kind="mergesort"
    ).drop(columns="_volume_key")
    frame = frame.reset_index(drop=True)
    frame["rank"] = np.arange(1, len(frame) + 1)
    return frame


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------

def _ratio(numerator: int, denominator: int, null_reason: str) -> dict[str, Any]:
    """Razón auditable: conserva numerador y denominador; null con motivo."""
    if denominator == 0:
        return {
            "value": None,
            "numerator": int(numerator),
            "denominator": 0,
            "null_reason": null_reason,
        }
    return {
        "value": float(numerator) / float(denominator),
        "numerator": int(numerator),
        "denominator": int(denominator),
        "null_reason": None,
    }


def positive_accounts(edges: pd.DataFrame) -> set[str]:
    """Cuentas que aparecen como origen o destino de al menos un fraude etiquetado."""
    fraud = edges[edges["isFraud"] == 1]
    return set(fraud["nameOrig"].astype(str)) | set(fraud["nameDest"].astype(str))


def evaluate_selection(
    edges: pd.DataFrame, selected: Sequence[str], positives: set[str]
) -> dict[str, Any]:
    """Mide una selección de cuentas contra las etiquetas de la muestra.

    Una transacción queda cubierta si su origen **o** su destino pertenece a la
    selección y se cuenta una sola vez aunque ambos extremos estén
    seleccionados.
    """
    chosen = set(map(str, selected))
    if len(chosen) != len(selected):
        raise ValueError("La selección contiene cuentas repetidas")

    total_fraud = int((edges["isFraud"] == 1).sum())
    covered_mask = edges["nameOrig"].astype(str).isin(chosen) | edges["nameDest"].astype(
        str
    ).isin(chosen)
    covered = int(covered_mask.sum())
    covered_fraud = int((covered_mask & (edges["isFraud"] == 1)).sum())
    positive_selected = len(chosen & positives)

    return {
        "selected_accounts": len(chosen),
        "positive_accounts_selected": positive_selected,
        "covered_transactions": covered,
        "covered_fraud_transactions": covered_fraud,
        "account_precision": _ratio(
            positive_selected, len(chosen), "no hay cuentas seleccionadas"
        ),
        "account_recall": _ratio(
            positive_selected, len(positives), "la muestra no tiene cuentas positivas"
        ),
        "covered_transaction_precision": _ratio(
            covered_fraud, covered, "ninguna transacción queda cubierta"
        ),
        "fraud_coverage": _ratio(
            covered_fraud, total_fraud, "la muestra no tiene transacciones fraudulentas"
        ),
    }


def _difference(network: Mapping[str, Any], reference: Mapping[str, Any]) -> dict[str, Any]:
    """Diferencia red - referencia a igual k; null si alguna métrica es null."""
    result: dict[str, Any] = {}
    for name in RATIO_METRICS:
        a, b = network[name]["value"], reference[name]["value"]
        result[name] = None if a is None or b is None else a - b
    return result


# ---------------------------------------------------------------------------
# Reporte
# ---------------------------------------------------------------------------

def _library_versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "networkx": nx.__version__,
    }


def _analysis_id(
    source_sha256: str, requested_limit: int | None, fingerprint: str, config: Mapping[str, Any]
) -> str:
    material = "|".join(
        [
            source_sha256,
            str(requested_limit),
            fingerprint,
            repr(sorted(config.items())),
            str(SCHEMA_VERSION),
        ]
    )
    return "graph-comparison-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def build_comparison_report(
    edges: pd.DataFrame,
    G: nx.DiGraph | None,
    node_metrics: pd.DataFrame | None,
    *,
    config: Mapping[str, Any],
    source: Mapping[str, Any],
    requested_limit: int | None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Construye el reporte de comparación red vs referencia por volumen.

    Parameters
    ----------
    edges : pd.DataFrame
        Única muestra leída con ``read_transaction_edges``.
    G, node_metrics
        Grafo y métricas construidos con esa misma muestra.  Pueden ser
        ``None`` solo si la muestra está vacía.
    config : Mapping
        Resultado de :func:`comparison_config`.
    source : Mapping
        ``path``, ``sha256`` y ``size_bytes`` de la fuente.
    requested_limit : int or None
        Límite de filas solicitado (consta en el reporte, no solo las filas
        efectivas).
    """
    required = set(FINGERPRINT_COLUMNS)
    if not required <= set(edges.columns):
        raise ValueError(f"Faltan columnas requeridas: {sorted(required - set(edges.columns))}")
    if requested_limit is not None and requested_limit < 1:
        raise ValueError("El límite solicitado debe ser un entero positivo")

    requested = validate_budgets(config["budgets"])
    universe = build_universe(edges)
    n_universe = len(universe)
    effective, mapping = effective_budgets(requested, n_universe)

    if n_universe:
        if G is None or node_metrics is None:
            raise ValueError("Se requieren el grafo y sus métricas")
        network = rank_network(
            universe,
            G,
            node_metrics,
            fanout_percentile=config["fanout_percentile"],
            fanin_percentile=config["fanin_percentile"],
            flow_percentile=config["flow_percentile"],
        )
        reference = rank_volume(universe, G, node_metrics)
    else:
        network = rank_network([], nx.DiGraph(), pd.DataFrame(), fanout_percentile=0,
                               fanin_percentile=0, flow_percentile=0)
        reference = rank_volume([], nx.DiGraph(), pd.DataFrame())

    positives = positive_accounts(edges) if n_universe else set()
    fingerprint = edges_fingerprint(edges)
    max_k = max(effective) if effective else 0

    selections: dict[str, dict[str, list[str]]] = {NETWORK_METHOD: {}, REFERENCE_METHOD: {}}
    comparisons: list[dict[str, Any]] = []
    for k in effective:
        net_sel = network["account"].head(k).tolist()
        ref_sel = reference["account"].head(k).tolist()
        if len(set(net_sel)) != k or len(set(ref_sel)) != k:
            raise ValueError("Ambos métodos deben devolver exactamente k cuentas distintas")
        selections[NETWORK_METHOD][str(k)] = net_sel
        selections[REFERENCE_METHOD][str(k)] = ref_sel

        net_metrics = evaluate_selection(edges, net_sel, positives)
        ref_metrics = evaluate_selection(edges, ref_sel, positives)
        comparisons.append(
            {
                "k": k,
                "requested_budgets": sorted(r for r, e in mapping.items() if e == k),
                NETWORK_METHOD: net_metrics,
                REFERENCE_METHOD: ref_metrics,
                "difference": _difference(net_metrics, ref_metrics),
            }
        )

    total_fraud = int((edges["isFraud"] == 1).sum())
    account_types = {"cliente": 0, "comercio": 0}
    for account in universe:
        account_types["comercio" if account.startswith("M") else "cliente"] += 1

    steps = edges["step"] if n_universe else pd.Series(dtype="int64")
    source_sha = str(source.get("sha256", ""))

    report = {
        "schema_version": SCHEMA_VERSION,
        "analysis_id": _analysis_id(source_sha, requested_limit, fingerprint, config),
        "simulation_data": True,
        "scope": SCOPE,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "path": str(source.get("path", "")),
            "sha256": source_sha,
            "size_bytes": source.get("size_bytes"),
        },
        "sample": {
            "requested_limit": requested_limit,
            "rows_read": int(len(edges)),
            "min_step": int(steps.min()) if len(steps) else None,
            "max_step": int(steps.max()) if len(steps) else None,
            "sampling_rule": SAMPLING_RULE,
            "rows_fingerprint_sha256": fingerprint,
            "fraud_transactions": total_fraud,
            "fraud_rate": (total_fraud / len(edges)) if len(edges) else None,
        },
        "configuration": {
            "budgets_requested": requested,
            "default_sample_limit": config["default_sample_limit"],
            "fanout_percentile": config["fanout_percentile"],
            "fanin_percentile": config["fanin_percentile"],
            "flow_percentile": config["flow_percentile"],
            "network_ranking": "pattern_count desc, pagerank desc, account_id asc",
            "reference_ranking": "total_amount_sent + total_amount_received desc, account_id asc",
        },
        "universe": {
            "size": n_universe,
            "account_types": account_types,
            "positive_accounts": len(positives),
            "population_limits": list(POPULATION_LIMITS),
        },
        "budgets": {
            "requested": requested,
            "effective": effective,
            "requested_to_effective": {str(k): v for k, v in mapping.items()},
        },
        "rankings": {
            NETWORK_METHOD: {
                "selected_by_budget": selections[NETWORK_METHOD],
                "top_scores": network.head(max_k)[["rank", "account", "pattern_count", "pagerank"]]
                .to_dict(orient="records"),
            },
            REFERENCE_METHOD: {
                "selected_by_budget": selections[REFERENCE_METHOD],
                "top_scores": reference.head(max_k)[["rank", "account", "total_volume"]]
                .to_dict(orient="records"),
            },
        },
        "comparisons": comparisons,
        "limitations": list(LIMITATIONS),
        "versions": {**_library_versions(), "schema_version": SCHEMA_VERSION},
    }
    return report


# ---------------------------------------------------------------------------
# Salidas
# ---------------------------------------------------------------------------

def _pct(metric: Mapping[str, Any]) -> str:
    if metric["value"] is None:
        return f"n/d ({metric['null_reason']})"
    return f"{metric['value']:.4%} ({metric['numerator']:,}/{metric['denominator']:,})"


def _diff(value: float | None) -> str:
    return "n/d" if value is None else f"{value * 100:+.2f} pp"


def render_comparison_markdown(report: Mapping[str, Any]) -> str:
    """Markdown generado desde el mismo contenido del reporte JSON."""
    sample = report["sample"]
    universe = report["universe"]
    cfg = report["configuration"]
    limit = sample["requested_limit"]
    lines = [
        "# Comparación de alertas de red frente a una referencia por volumen",
        "",
        "Documento generado por `scripts/evaluate_graph_alerts.py` desde "
        "`artifacts/reports/graph/comparison.json`; no transcribir cifras a mano. "
        "Datos de PaySim (simulación). Evaluación exploratoria y retrospectiva "
        "sobre la misma muestra observada.",
        "",
        f"- Análisis: `{report['analysis_id']}` (esquema {report['schema_version']}).",
        f"- Fuente SHA-256: `{report['source']['sha256']}`.",
        f"- Límite solicitado: {limit if limit is not None else 'archivo completo'}"
        f"; filas leídas: {sample['rows_read']:,}"
        f"; steps {sample['min_step']}–{sample['max_step']}.",
        f"- Regla de muestreo: {sample['sampling_rule']}",
        f"- Huella de las filas usadas: `{sample['rows_fingerprint_sha256']}`.",
        f"- Transacciones fraudulentas etiquetadas: {sample['fraud_transactions']:,}.",
        f"- Universo: {universe['size']:,} cuentas "
        f"({universe['account_types']['cliente']:,} clientes, "
        f"{universe['account_types']['comercio']:,} comercios); "
        f"{universe['positive_accounts']:,} cuentas positivas.",
        f"- Presupuestos solicitados: {report['budgets']['requested']}; "
        f"efectivos: {report['budgets']['effective']}.",
        f"- Percentiles fijados: fan-out {cfg['fanout_percentile']}, "
        f"fan-in {cfg['fanin_percentile']}, flujo neto {cfg['flow_percentile']}.",
        "",
        "## Métodos",
        "",
        f"- **Red:** {cfg['network_ranking']}.",
        f"- **Referencia por volumen:** {cfg['reference_ranking']}.",
        "- Ambos usan el mismo universo, los mismos nodos y aristas, y ninguna "
        "etiqueta de fraude para ordenar.",
        "",
    ]
    if not report["comparisons"]:
        lines += ["## Resultados", "", "Sin presupuestos efectivos: la muestra no tiene cuentas.", ""]
    for comp in report["comparisons"]:
        net, ref, diff = comp[NETWORK_METHOD], comp[REFERENCE_METHOD], comp["difference"]
        lines += [
            f"## k = {comp['k']} (solicitado: {comp['requested_budgets']})",
            "",
            "| Métrica | Nivel | Red | Referencia por volumen | Diferencia (red − referencia) |",
            "| --- | --- | --- | --- | --- |",
            f"| Cuentas seleccionadas | cuenta | {net['selected_accounts']:,} | "
            f"{ref['selected_accounts']:,} | – |",
            f"| Cuentas positivas seleccionadas | cuenta | {net['positive_accounts_selected']:,} | "
            f"{ref['positive_accounts_selected']:,} | – |",
            f"| Precisión de cuentas | cuenta | {_pct(net['account_precision'])} | "
            f"{_pct(ref['account_precision'])} | {_diff(diff['account_precision'])} |",
            f"| Recall de cuentas positivas | cuenta | {_pct(net['account_recall'])} | "
            f"{_pct(ref['account_recall'])} | {_diff(diff['account_recall'])} |",
            f"| Transacciones cubiertas | transacción | {net['covered_transactions']:,} | "
            f"{ref['covered_transactions']:,} | – |",
            f"| Transacciones fraudulentas cubiertas | transacción | "
            f"{net['covered_fraud_transactions']:,} | {ref['covered_fraud_transactions']:,} | – |",
            f"| Precisión de transacciones cubiertas | transacción | "
            f"{_pct(net['covered_transaction_precision'])} | "
            f"{_pct(ref['covered_transaction_precision'])} | "
            f"{_diff(diff['covered_transaction_precision'])} |",
            f"| Cobertura de fraude | transacción | {_pct(net['fraud_coverage'])} | "
            f"{_pct(ref['fraud_coverage'])} | {_diff(diff['fraud_coverage'])} |",
            "",
        ]
    lines += ["## Limitaciones", ""] + [f"- {text}" for text in report["limitations"]]
    lines += ["", "## Versiones", ""] + [
        f"- {name}: {value}" for name, value in report["versions"].items()
    ]
    return "\n".join(lines) + "\n"
