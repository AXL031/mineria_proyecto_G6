"""CLI para perfilado y análisis de la red de transacciones.

Ejecuta el pipeline completo: ingesta → grafo → métricas → patrones
y genera reportes en JSON y Markdown.

Uso desde la raíz del proyecto:

    python scripts/profile_graph.py
    python scripts/profile_graph.py --limit 100000
    python scripts/profile_graph.py --markdown docs/grafos/perfil-red.md
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankshield.ingestion.graph_dataset import read_transaction_edges, summarize_edges
from bankshield.features.graph import (
    build_transaction_graph,
    compute_node_metrics,
    compute_graph_summary,
)
from bankshield.features.graph_patterns import (
    combine_suspicion_indicators,
    detect_circular_transactions,
    detect_high_fanout,
    detect_high_fanin,
    detect_high_value_edges,
)
from bankshield.services.graph import query_account, query_top_accounts


def _load_config() -> dict:
    """Carga configuración desde configs/graph.json."""
    config_path = ROOT / "configs" / "graph.json"
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))
    return {}


def _write_json_report(data: dict, path: Path) -> None:
    """Guarda reporte JSON con formato legible."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )


def _write_markdown_report(
    edge_summary: dict,
    graph_summary: dict,
    top_pagerank: list,
    top_fanout: list,
    suspicious: list,
    cycles: list,
    scope: str,
    path: Path,
) -> None:
    """Genera informe Markdown del análisis de red."""
    lines = [
        "# Perfil de red de transacciones — módulo de grafos",
        "",
        "Informe generado por `scripts/profile_graph.py`.  Los datos provienen",
        "de una simulación (PaySim); los resultados son simulados.",
        "",
        f"- Alcance: `{scope}`.",
        f"- Aristas leídas: {edge_summary['total_aristas']:,}.",
        f"- Cuentas origen únicas: {edge_summary['cuentas_origen_unicas']:,}.",
        f"- Cuentas destino únicas: {edge_summary['cuentas_destino_unicas']:,}.",
        f"- Cuentas totales únicas: {edge_summary['cuentas_totales_unicas']:,}.",
        f"- Monto total: {edge_summary['monto_total']:,.2f}.",
        f"- Aristas fraudulentas: {edge_summary['aristas_fraudulentas']:,} "
        f"({edge_summary['tasa_fraude']:.4%}).",
        "",
        "## Transacciones por tipo",
        "",
        "| Tipo | Transacciones | Monto total | Monto medio | Fraudes |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for tipo, stats in edge_summary["por_tipo"].items():
        lines.append(
            f"| {tipo} | {stats['transacciones']:,} | "
            f"{stats['monto_total']:,.2f} | {stats['monto_medio']:,.2f} | "
            f"{stats['fraudes']:,} |"
        )

    lines += [
        "",
        "## Resumen del grafo",
        "",
        f"- Nodos: {graph_summary['nodos']:,}.",
        f"- Aristas únicas (pares): {graph_summary['aristas_unicas']:,}.",
        f"- Densidad: {graph_summary['densidad']:.6f}.",
        f"- Componentes débilmente conexos: {graph_summary['componentes_debiles']:,}.",
        f"- Mayor componente: {graph_summary['nodos_mayor_componente']:,} nodos "
        f"({graph_summary['porcentaje_mayor_componente']:.2%}).",
        f"- Grado de salida medio: {graph_summary['grado_salida_medio']:.2f}; "
        f"máximo: {graph_summary['grado_salida_maximo']}.",
        f"- Grado de entrada medio: {graph_summary['grado_entrada_medio']:.2f}; "
        f"máximo: {graph_summary['grado_entrada_maximo']}.",
        f"- Pares con al menos una transacción fraudulenta: "
        f"{graph_summary['pares_con_fraude']:,}.",
    ]

    # Nodos por tipo
    lines += ["", "### Nodos por tipo de cuenta", ""]
    for tipo, count in graph_summary["nodos_por_tipo"].items():
        lines.append(f"- {tipo}: {count:,}.")

    # Top PageRank
    lines += [
        "",
        "## Cuentas con mayor PageRank",
        "",
        "| Cuenta | Tipo | PageRank | Tx enviadas | Tx recibidas |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for acc in top_pagerank[:10]:
        lines.append(
            f"| `{acc['account']}` | {acc['account_type']} | "
            f"{acc['pagerank']:.6f} | {acc['transactions_sent']:,} | "
            f"{acc['transactions_received']:,} |"
        )

    # Top fan-out
    if not top_fanout.empty:
        lines += [
            "",
            "## Cuentas con mayor fan-out (abanico de destinos)",
            "",
            "| Cuenta | Tipo | Destinos | Monto enviado | Fraudes |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
        for _, row in top_fanout.head(10).iterrows():
            lines.append(
                f"| `{row['account']}` | {row['account_type']} | "
                f"{row['out_degree']} | {row['total_amount_sent']:,.2f} | "
                f"{row['fraud_count']} |"
            )

    # Ciclos
    if cycles:
        lines += [
            "",
            "## Ciclos detectados (transacciones circulares)",
            "",
            f"Se encontraron {len(cycles)} ciclos cortos.  "
            "La presencia de ciclos no implica fraude; muchas relaciones "
            "comerciales legítimas son bidireccionales.",
            "",
            "| Longitud | Monto total | Fraudes | Cuentas |",
            "| ---: | ---: | ---: | --- |",
        ]
        for cycle in cycles[:10]:
            accounts = " → ".join(f"`{a}`" for a in cycle["cycle"])
            lines.append(
                f"| {cycle['length']} | {cycle['total_amount']:,.2f} | "
                f"{cycle['fraud_count']} | {accounts} |"
            )

    # Cuentas sospechosas
    if not suspicious.empty:
        lines += [
            "",
            "## Cuentas con múltiples indicadores de sospecha",
            "",
            "| Cuenta | Tipo | Patrones | Nº patrones | Fraudes | PageRank |",
            "| --- | --- | --- | ---: | ---: | ---: |",
        ]
        for _, row in suspicious.head(10).iterrows():
            patterns = ", ".join(row["patterns"])
            lines.append(
                f"| `{row['account']}` | {row['account_type']} | "
                f"{patterns} | {row['pattern_count']} | "
                f"{row['fraud_count']} | {row['pagerank']:.6f} |"
            )

    lines += [
        "",
        "## Limitaciones",
        "",
        "- Los datos provienen de PaySim, una simulación.  Los patrones "
        "detectados reflejan la estructura del simulador, no operaciones "
        "bancarias reales.",
        "- `step` no corresponde a fechas calendario; no se puede hacer "
        "análisis temporal con fechas.",
        "- Los umbrales de detección son percentiles exploratorios; "
        "requieren calibración con datos reales.",
        "- La búsqueda de ciclos está limitada en longitud y cantidad "
        "por razones de cómputo.",
        "- El grafo agrega todas las transacciones del mismo par "
        "en una sola arista; se pierde el detalle temporal.",
        "- Este perfil no mide: comunidades, componentes fuertemente conexos "
        "de gran escala, ni evolución temporal de la red.",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Perfilar red de transacciones sin modificar Bronze"
    )
    parser.add_argument(
        "--input", type=Path,
        default=ROOT / "data/bronze/transactions/PS_20174392719_1491204439457_log.csv",
    )
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "artifacts/reports/graph/network_profile.json",
    )
    parser.add_argument(
        "--markdown", type=Path,
        help="Ruta opcional para el informe Markdown",
    )
    parser.add_argument(
        "--limit", type=int,
        help="Máximo de filas a leer; sin este argumento se usa el límite "
             "de la configuración",
    )
    args = parser.parse_args()

    config = _load_config()
    limit = args.limit or config.get("sample_limit")
    chunksize = config.get("chunksize", 200_000)

    # 1. Ingesta
    print("=" * 60)
    print("PASO 1: Lectura de aristas transaccionales")
    print("=" * 60)
    edges = read_transaction_edges(args.input, limit=limit, chunksize=chunksize)
    edge_summary = summarize_edges(edges)
    scope = "muestra" if limit else "archivo_completo"
    print(f"Aristas leídas: {len(edges):,}")

    # 2. Construcción del grafo
    print("\n" + "=" * 60)
    print("PASO 2: Construcción del grafo dirigido")
    print("=" * 60)
    G = build_transaction_graph(edges)
    graph_summary = compute_graph_summary(G)
    print(f"Nodos: {graph_summary['nodos']:,}")
    print(f"Aristas únicas: {graph_summary['aristas_unicas']:,}")
    print(f"Componentes débiles: {graph_summary['componentes_debiles']:,}")

    # 3. Métricas de nodo
    print("\n" + "=" * 60)
    print("PASO 3: Cálculo de métricas de red por cuenta")
    print("=" * 60)
    node_metrics = compute_node_metrics(G)
    top_pagerank = query_top_accounts(G, metric="pagerank", top_n=20)
    print(f"Métricas calculadas para {len(node_metrics)} cuentas")

    # 4. Detección de patrones
    print("\n" + "=" * 60)
    print("PASO 4: Detección de patrones sospechosos")
    print("=" * 60)
    fanout_pct = config.get("fanout_percentile", 95)
    fanin_pct = config.get("fanin_percentile", 95)
    flow_pct = config.get("flow_percentile", 95)
    hv_pct = config.get("high_value_percentile", 99)
    max_cycle = config.get("max_cycle_length", 4)
    max_cycles = config.get("max_cycles_reported", 50)

    top_fanout = detect_high_fanout(G, fanout_pct)
    top_fanin = detect_high_fanin(G, fanin_pct)
    high_value = detect_high_value_edges(G, hv_pct)
    print(f"Cuentas con alto fan-out: {len(top_fanout)}")
    print(f"Cuentas con alto fan-in: {len(top_fanin)}")
    print(f"Pares de alto valor: {len(high_value)}")

    print("Buscando ciclos cortos (puede tardar)...")
    cycles = detect_circular_transactions(G, max_length=max_cycle, limit=max_cycles)
    print(f"Ciclos encontrados: {len(cycles)}")

    suspicious = combine_suspicion_indicators(
        G, node_metrics, fanout_pct, fanin_pct, flow_pct
    )
    print(f"Cuentas con múltiples indicadores: {len(suspicious)}")

    # 5. Ejemplo de consulta
    print("\n" + "=" * 60)
    print("PASO 5: Ejemplo de consulta de cuenta")
    print("=" * 60)
    if top_pagerank:
        example_account = top_pagerank[0]["account"]
        example_query = query_account(G, example_account)
        print(f"Cuenta ejemplo: {example_account}")
        print(f"  Tipo: {example_query['account_type']}")
        print(f"  Tx enviadas: {example_query['transactions_sent']:,}")
        print(f"  Tx recibidas: {example_query['transactions_received']:,}")
        print(f"  Destinos únicos: {example_query['unique_destinations']}")
        print(f"  Orígenes únicos: {example_query['unique_sources']}")
        print(f"  Monto enviado: {example_query['total_amount_sent']:,.2f}")
        print(f"  Monto recibido: {example_query['total_amount_received']:,.2f}")
        print(f"  Flujo neto: {example_query['net_flow']:,.2f}")

    # 6. Reportes
    print("\n" + "=" * 60)
    print("PASO 6: Generación de reportes")
    print("=" * 60)

    report = {
        "schema_version": 1,
        "scope": scope,
        "row_limit": limit,
        "edge_summary": edge_summary,
        "graph_summary": graph_summary,
        "top_pagerank": top_pagerank,
        "patterns": {
            "high_fanout_count": len(top_fanout),
            "high_fanin_count": len(top_fanin),
            "high_value_pairs_count": len(high_value),
            "cycles_found": len(cycles),
            "suspicious_accounts": len(suspicious),
        },
        "cycles_sample": cycles[:10],
        "example_query": example_query if top_pagerank else None,
    }

    _write_json_report(report, args.output)
    print(f"JSON: {args.output}")

    if args.markdown:
        _write_markdown_report(
            edge_summary, graph_summary, top_pagerank,
            top_fanout, suspicious, cycles, scope, args.markdown,
        )
        print(f"Markdown: {args.markdown}")

    print("\n[OK] Perfilado de red completado.")


if __name__ == "__main__":
    main()
