"""Vista analítica interactiva del módulo de Grafos de Transacciones."""

import json
from pathlib import Path

import networkx as nx
import pandas as pd
from pyvis.network import Network
import streamlit as st
import streamlit.components.v1 as components

from bankshield.features.graph import (
    build_transaction_graph,
    compute_graph_summary,
    compute_node_metrics,
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

st.set_page_config(
    page_title="Redes de Transacciones | BankShield",
    page_icon="🌐",
    layout="wide",
)

# Estilos CSS especializados
st.markdown(
    """
    <style>
    .module-header {
        font-size: 2.1rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.2rem;
    }
    .module-sub {
        font-size: 1rem;
        color: #64748B;
        margin-bottom: 1.2rem;
    }
    .badge-sim {
        background-color: #E0E7FF;
        color: #3730A3;
        font-weight: 600;
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        display: inline-block;
        margin-bottom: 1rem;
    }
    .kpi-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #E2E8F0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="module-header">🌐 Análisis Topológico y Redes de Transacciones</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="module-sub">Monitoreo de aristas de pago (nameOrig → nameDest), centralidad de intermediación y detección de patrones de dispersión/concentración.</div>',
    unsafe_allow_html=True,
)
st.markdown('<span class="badge-sim">ℹ️ Datos Simulados — Esquema PaySim</span>', unsafe_allow_html=True)

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data/bronze/transactions/PS_20174392719_1491204439457_log.csv"


@st.cache_data(show_spinner="Procesando topología de aristas en memoria...")
def load_graph_data(sample_limit: int):
    """Carga y construye el grafo de transacciones con cache."""
    edges = read_transaction_edges(DATA_PATH, limit=sample_limit)
    G = build_transaction_graph(edges)
    summary = compute_graph_summary(G)
    edge_summary = summarize_edges(edges)
    node_metrics = compute_node_metrics(G)
    return G, summary, edge_summary, node_metrics


# Barra lateral de configuración y filtros
with st.sidebar:
    st.header("⚙️ Parámetros de Análisis")
    sample_size = st.select_slider(
        "Muestra de transacciones iniciales",
        options=[10_000, 25_000, 50_000, 100_000],
        value=50_000,
        format_func=lambda x: f"{x:,} filas",
    )
    st.caption("Carga particiones acotadas para mantener fluidez en el navegador.")

try:
    G, summary, edge_summary, node_metrics = load_graph_data(sample_size)
except Exception as e:
    st.error(f"Error al cargar datos transaccionales: {e}")
    st.stop()

# -------------------------------------------------------------
# SECCIÓN 1: KPIs GLOBALES DE LA RED
# -------------------------------------------------------------
st.markdown("### 📊 Indicadores Globales de la Red")
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Nodos Únicos", f"{summary['nodos']:,}")
col2.metric("Aristas Únicas", f"{summary['aristas_unicas']:,}")
col3.metric("Densidad de Red", f"{summary['densidad']:.6f}")
col4.metric("Volumen Analizado", f"${edge_summary['monto_total']:,.0f}")
col5.metric("Aristas con Fraude", f"{summary['pares_con_fraude']:,}", delta=f"{edge_summary['tasa_fraude']:.2%}")

# -------------------------------------------------------------
# SECCIÓN 2: PESTAÑAS DE ANÁLISIS
# -------------------------------------------------------------
tab_subgraph, tab_patterns, tab_ranking, tab_theory = st.tabs([
    "🔍 Explorador Interactivo de Subgrafos",
    "⚠️ Detección de Patrones Atípicos",
    "🏆 Ranking de Centralidad (PageRank)",
    "📖 Metodología y Contrato",
])

# -------------------------------------------------------------
# TAB 1: VISUALIZACIÓN INTERACTIVA DE SUBGRAFOS (PYVIS)
# -------------------------------------------------------------
with tab_subgraph:
    st.subheader("Visualización del Subgrafo Ego")
    st.markdown("Inspecciona las transacciones directas entrantes y salientes de una cuenta seleccionada.")

    sub_col1, sub_col2, sub_col3 = st.columns([2, 1, 1])

    # Sugerir cuentas interesantes (top PageRank o cuentas con fraude)
    top_candidates = node_metrics.head(10).index.tolist()
    default_acc = top_candidates[0] if top_candidates else ""

    with sub_col1:
        account_input = st.text_input(
            "Identificador de Cuenta (ej. C985934102 o M1979787155):",
            value=default_acc,
        )
    with sub_col2:
        depth_input = st.selectbox("Profundidad de vecindad (saltos)", options=[1, 2], index=0)
    with sub_col3:
        st.write("")
        st.write("")
        btn_search = st.button("Buscar y Graficar", type="primary")

    if account_input:
        if account_input not in G:
            st.warning(f"La cuenta `{account_input}` no fue encontrada en la muestra de {sample_size:,} transacciones.")
        else:
            try:
                acc_info = query_account(G, account_input)
                sub_data = query_subgraph(G, account_input, depth=depth_input)

                # Tarjetas de resumen de la cuenta
                mcol1, mcol2, mcol3, mcol4 = st.columns(4)
                mcol1.metric("Tipo de Cuenta", acc_info["account_type"].capitalize())
                mcol2.metric("Monto Enviado", f"${acc_info['total_amount_sent']:,.2f}")
                mcol3.metric("Monto Recibido", f"${acc_info['total_amount_received']:,.2f}")
                mcol4.metric("Flujo Neto", f"${acc_info['net_flow']:,.2f}")

                # Generar grafo Pyvis interactivo
                net = Network(height="520px", width="100%", directed=True, bgcolor="#ffffff", font_color="#1e293b")
                net.force_atlas_2based(gravity=-60, central_gravity=0.01, spring_length=120)

                # Nodos
                for n in sub_data["nodes"]:
                    node_id = n["id"]
                    is_center = n.get("is_center", False)
                    acc_type = n.get("account_type", "cliente")

                    if is_center:
                        color = "#EF4444"  # Rojo para el centro
                        size = 28
                    elif acc_type == "comercio":
                        color = "#10B981"  # Verde para comercios
                        size = 18
                    else:
                        color = "#3B82F6"  # Azul para clientes
                        size = 18

                    label = f"{node_id}\n({acc_type})"
                    title = f"Cuenta: {node_id}<br>Tipo: {acc_type}<br>Enviadas: {n.get('transactions_sent')}<br>Recibidas: {n.get('transactions_received')}"
                    net.add_node(node_id, label=label, title=title, color=color, size=size)

                # Aristas
                for e in sub_data["edges"]:
                    u, v = e["source"], e["target"]
                    amt = e.get("total_amount", 0.0)
                    frauds = e.get("fraud_count", 0)
                    edge_color = "#DC2626" if frauds > 0 else "#94A3B8"
                    title = f"Monto: ${amt:,.2f}<br>Transacciones: {e.get('weight')}<br>Fraudes: {frauds}"
                    net.add_edge(u, v, title=title, value=max(1, int(e.get("weight", 1))), color=edge_color)

                # Renderizar HTML del canvas interactivo
                html_path = ROOT / "artifacts/reports/graph/subgraph_view.html"
                html_path.parent.mkdir(parents=True, exist_ok=True)
                net.save_graph(str(html_path))
                html_content = html_path.read_text(encoding="utf-8")
                components.html(html_content, height=550)

                # Tablas con detalle de transacciones
                with st.expander("📄 Ver detalle tabular de conexiones"):
                    c_out, c_in = st.columns(2)
                    with c_out:
                        st.markdown("**Destinos (Envíos)**")
                        if acc_info["outgoing_connections"]:
                            st.dataframe(pd.DataFrame(acc_info["outgoing_connections"]), use_container_width=True)
                        else:
                            st.caption("Sin transacciones salientes registradas.")
                    with c_in:
                        st.markdown("**Orígenes (Recepciones)**")
                        if acc_info["incoming_connections"]:
                            st.dataframe(pd.DataFrame(acc_info["incoming_connections"]), use_container_width=True)
                        else:
                            st.caption("Sin transacciones entrantes registradas.")

            except Exception as exc:
                st.error(f"Error al procesar subgrafo: {exc}")

# -------------------------------------------------------------
# TAB 2: DETECCIÓN DE PATRONES SOSPECHOSOS
# -------------------------------------------------------------
with tab_patterns:
    st.subheader("Detección de Patrones en Topología Transaccional")
    st.markdown(
        """
        Los detectores evalúan anomalías estructurales comúnmente asociadas con dispersión de fondos
        (*layering/fan-out*), embudos de captación (*fan-in*) y operaciones circulares.
        """
    )

    pat_col1, pat_col2 = st.columns(2)
    with pat_col1:
        fanout_p = st.slider("Percentil para Alto Fan-out (Dispersión)", 90.0, 99.9, 95.0, 0.5)
    with pat_col2:
        fanin_p = st.slider("Percentil para Alto Fan-in (Concentración)", 90.0, 99.9, 95.0, 0.5)

    suspicious_df = combine_suspicion_indicators(
        G, node_metrics, fanout_percentile=fanout_p, fanin_percentile=fanin_p
    )

    st.markdown(f"**Cuentas con Alertas Activas Detectadas:** `{len(suspicious_df):,}`")

    if not suspicious_df.empty:
        # Formatear lista de patrones para visualización
        display_df = suspicious_df.copy()
        display_df["patterns"] = display_df["patterns"].apply(lambda pts: " • ".join(pts))
        st.dataframe(
            display_df.head(50),
            use_container_width=True,
            column_config={
                "account": st.column_config.TextColumn("Cuenta"),
                "account_type": st.column_config.TextColumn("Tipo"),
                "patterns": st.column_config.TextColumn("Patrones Activos"),
                "pattern_count": st.column_config.NumberColumn("Nº Alertas"),
                "fraud_count": st.column_config.NumberColumn("Fraudes Asociados"),
                "pagerank": st.column_config.NumberColumn("PageRank", format="%.6f"),
            },
        )
    else:
        st.info("No se registraron cuentas que superen los umbrales seleccionados.")

# -------------------------------------------------------------
# TAB 3: RANKING DE CENTRALIDAD
# -------------------------------------------------------------
with tab_ranking:
    st.subheader("Top Nodos por Influencia y Flujo de Fondos")

    r_col1, r_col2 = st.columns([1, 1])
    with r_col1:
        metric_choice = st.selectbox(
            "Criterio de Ordenamiento:",
            options=[
                ("pagerank", "PageRank (Prestigio/Conectividad)"),
                ("weighted_in_degree", "Grado de Entrada Ponderado (Nº Tx Recibidas)"),
                ("weighted_out_degree", "Grado de Salida Ponderado (Nº Tx Enviadas)"),
                ("total_amount_received", "Monto Total Recibido ($)"),
                ("total_amount_sent", "Monto Total Enviado ($)"),
                ("net_flow", "Flujo Neto ($)"),
            ],
            format_func=lambda x: x[1],
        )[0]
    with r_col2:
        n_top = st.slider("Cantidad de Nodos a Mostrar", 5, 50, 20)

    top_data = query_top_accounts(G, metric=metric_choice, top_n=n_top)
    st.dataframe(pd.DataFrame(top_data), use_container_width=True)

# -------------------------------------------------------------
# TAB 4: METODOLOGÍA Y CONTRATO DE VARIABLES
# -------------------------------------------------------------
with tab_theory:
    st.subheader("Especificación Metodológica y Límites")
    st.markdown(
        """
        - **Definición de Arista:** Transacción dirigida `nameOrig → nameDest`. Si ocurren múltiples operaciones
          entre el mismo par, se agregan conservando el volumen total, promedio, tipos y marcas de fraude.
        - **Identificación:** Nodos que comienzan con `M` corresponden a comercios (*merchants*); los que comienzan
          con `C` corresponden a clientes comunes.
        - **Exclusiones Preventivas:** No se incluyen saldos posteriores (`newbalanceOrig`, `newbalanceDest`) para evitar
          sesgos temporales y fugas de información.
        - **Límites:** El dataset PaySim es un entorno simulado de dinero móvil; las métricas demuestran capacidades
          analíticas de grafos y no deben extrapolarse como comportamiento verificado de clientes financieros reales.
        """
    )
