"""Vista analítica interactiva del módulo de Grafos de Transacciones.

Conecta con la API de BankShield para obtener datos de red en lugar de
llamar servicios internos directamente.
"""

import os
from pathlib import Path

import pandas as pd
from pyvis.network import Network
import requests
import streamlit as st
from bankshield.ui import chips, configure_page, page_header, status_notice
import streamlit.components.v1 as components

API_URL = os.environ.get("BANKSHIELD_API_URL", "http://127.0.0.1:8000").rstrip("/")
ROOT = Path(__file__).resolve().parents[2]

configure_page(
    page_title="Redes de Transacciones | BankShield",
    page_icon="🌐",
    layout="wide",
)

page_header(
    "Análisis topológico y redes de transacciones",
    "Monitoreo de aristas de pago (nameOrig → nameDest), centralidad, detección de patrones "
    "de dispersión y concentración, y comparación justa de alertas frente al volumen.",
    eyebrow="Redes y grafos",
    highlight="redes de transacciones",
    badges=(
        ("info", "Datos simulados — esquema PaySim"),
        ("network", "Consultas acotadas por muestra", "green"),
    ),
)


# ---------------------------------------------------------------
# Funciones auxiliares de comunicación con la API
# ---------------------------------------------------------------

def _call_api(endpoint: str, params: dict | None = None) -> dict | None:
    """Llama a un endpoint GET de la API de grafos y devuelve el JSON."""
    try:
        url = f"{API_URL}/api/graphs/{endpoint}"
        response = requests.get(url, params={"limit": sample_size, **(params or {})}, timeout=60)
        if response.status_code == 404:
            st.warning("Recurso no encontrado en la API.")
            return None
        if response.status_code == 400:
            st.error(f"Parámetro inválido: {response.json().get('detail', '')}")
            return None
        response.raise_for_status()
        return response.json()
    except requests.ConnectionError:
        st.error(
            "No se pudo conectar con la API. "
            "Comprueba que el servidor esté iniciado en "
            f"`{API_URL}` e inténtalo de nuevo."
        )
        return None
    except requests.Timeout:
        st.error("La solicitud a la API excedió el tiempo de espera.")
        return None
    except (requests.RequestException, ValueError) as exc:
        st.error(f"Error al consultar la API: {exc}")
        return None


COMPARISON_NOTICES = {
    "report_missing": "Comparación no disponible",
    "report_invalid": "Reporte de comparación inválido",
    "incompatible_version": "Reporte de comparación con versión incompatible",
    "sample_mismatch": "El reporte no corresponde a esta muestra",
}


def _fetch_comparison() -> tuple[dict | None, tuple[str, str] | None]:
    """Consulta el reporte preparado de comparación sin afectar otras consultas.

    Devuelve ``(datos, None)`` o ``(None, (título, detalle))``.  Un reporte
    ausente o de otra muestra no es un error de la página: solo se avisa.
    """
    try:
        response = requests.get(
            f"{API_URL}/api/graphs/evaluation",
            params={"limit": sample_size},
            timeout=60,
        )
    except requests.ConnectionError:
        return None, ("API no disponible", f"No se pudo conectar con `{API_URL}`.")
    except requests.Timeout:
        return None, ("API sin respuesta", "La solicitud excedió el tiempo de espera.")
    except requests.RequestException as exc:
        return None, ("Error al consultar la comparación", str(exc))

    if response.status_code == 503:
        try:
            detail = response.json().get("detail", {})
        except ValueError:
            detail = {}
        code = detail.get("code") if isinstance(detail, dict) else None
        message = detail.get("message") if isinstance(detail, dict) else str(detail)
        return None, (
            COMPARISON_NOTICES.get(code, "Comparación no disponible"),
            message or "Regenere la comparación para esta muestra.",
        )
    try:
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        return None, ("Error al consultar la comparación", str(exc))
    if not isinstance(payload, dict) or not payload.get("comparisons"):
        return None, (
            "Comparación no disponible",
            "La API no devolvió comparaciones para esta muestra.",
        )
    return payload, None


def _format_metric(metric: dict | None) -> str:
    """Muestra valor con numerador/denominador, o el motivo si es nulo."""
    if not isinstance(metric, dict):
        return "n/d"
    if metric.get("value") is None:
        return f"n/d ({metric.get('null_reason', 'sin motivo')})"
    return f"{metric['value']:.2%} ({metric['numerator']:,}/{metric['denominator']:,})"


# Barra lateral de configuración y filtros
with st.sidebar:
    st.header(":material/tune: Parámetros de análisis")
    sample_size = st.select_slider(
        "Muestra de transacciones iniciales",
        options=[10_000, 25_000, 50_000, 100_000],
        value=int(os.environ.get("BANKSHIELD_GRAPH_SAMPLE", "50000")),
        format_func=lambda x: f"{x:,} filas",
    )
    st.caption("Carga particiones acotadas para mantener fluidez en el navegador.")

# ---------------------------------------------------------------
# Carga del resumen global desde la API
# ---------------------------------------------------------------
api_summary = _call_api("summary", {"limit": sample_size})
if api_summary is None:
    st.stop()

summary = api_summary["graph_summary"]
edge_summary = api_summary["edges_summary"]

# -------------------------------------------------------------
# SECCIÓN 1: KPIs GLOBALES DE LA RED
# -------------------------------------------------------------
st.subheader(":material/monitoring: Indicadores globales de la red")
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Nodos Únicos", f"{summary['nodos']:,}")
col2.metric("Aristas Únicas", f"{summary['aristas_unicas']:,}")
col3.metric("Densidad de Red", f"{summary['densidad']:.6f}")
col4.metric("Volumen Analizado", f"${edge_summary['monto_total']:,.0f}")
col5.metric("Aristas con Fraude", f"{summary['pares_con_fraude']:,}", delta=f"{edge_summary['tasa_fraude']:.2%}")

# -------------------------------------------------------------
# SECCIÓN 2: PESTAÑAS DE ANÁLISIS
# -------------------------------------------------------------
with st.container(key="graph-tabs"):
    tab_subgraph, tab_patterns, tab_ranking, tab_compare, tab_theory = st.tabs([
        ":material/travel_explore: Explorador de subgrafos",
        ":material/warning: Patrones atípicos",
        ":material/leaderboard: Ranking de centralidad",
        ":material/balance: Comparación red vs volumen",
        ":material/menu_book: Metodología y contrato",
    ])

# -------------------------------------------------------------
# TAB 1: VISUALIZACIÓN INTERACTIVA DE SUBGRAFOS (PYVIS)
# -------------------------------------------------------------
with tab_subgraph:
    st.subheader("Visualización del Subgrafo Ego")
    st.markdown("Inspecciona las transacciones directas entrantes y salientes de una cuenta seleccionada.")

    sub_col1, sub_col2, sub_col3 = st.columns([2, 1, 1])

    # Obtener cuentas sugeridas del ranking para el placeholder
    top_for_suggest = _call_api("top", {"metric": "pagerank", "top_n": 10})
    top_candidates = (
        [r["account"] for r in top_for_suggest["results"]]
        if top_for_suggest and top_for_suggest.get("results")
        else []
    )
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
        # Consultar detalle de la cuenta a la API
        acc_data = _call_api(f"account/{account_input}")
        sub_data_resp = _call_api(f"subgraph/{account_input}", {"depth": depth_input})

        if (
            acc_data is not None
            and "data" in acc_data
            and sub_data_resp is not None
            and "data" in sub_data_resp
        ):
            acc_info = acc_data["data"]
            sub_data = sub_data_resp["data"]

            # Tarjetas de resumen de la cuenta
            mcol1, mcol2, mcol3, mcol4 = st.columns(4)
            mcol1.metric("Tipo de Cuenta", acc_info["account_type"].capitalize())
            mcol2.metric("Monto Enviado", f"${acc_info['total_amount_sent']:,.2f}")
            mcol3.metric("Monto Recibido", f"${acc_info['total_amount_received']:,.2f}")
            mcol4.metric("Flujo Neto", f"${acc_info['net_flow']:,.2f}")

            # Generar grafo Pyvis interactivo
            net = Network(height="520px", width="100%", directed=True, bgcolor="#ffffff", font_color="#3C4043", cdn_resources="in_line")
            net.force_atlas_2based(gravity=-60, central_gravity=0.01, spring_length=120)

            # Nodos
            for n in sub_data["nodes"]:
                node_id = n["id"]
                is_center = n.get("is_center", False)
                acc_type = n.get("account_type", "cliente")

                if is_center:
                    color = "#FBBC05"  # Amarillo: selección, no nivel de riesgo
                    size = 28
                elif acc_type == "comercio":
                    color = "#34A853"  # Verde para comercios
                    size = 18
                else:
                    color = "#4285F4"  # Azul para clientes
                    size = 18

                label = f"{node_id}\n({acc_type})"
                title = f"Cuenta: {node_id}<br>Tipo: {acc_type}<br>Enviadas: {n.get('transactions_sent')}<br>Recibidas: {n.get('transactions_received')}"
                net.add_node(node_id, label=label, title=title, color=color, size=size)

            # Aristas
            for e in sub_data["edges"]:
                u, v = e["source"], e["target"]
                amt = e.get("total_amount", 0.0)
                frauds = e.get("fraud_count", 0)
                edge_color = "#EA4335" if frauds > 0 else "#9AA0A6"
                title = f"Monto: ${amt:,.2f}<br>Transacciones: {e.get('weight')}<br>Fraudes: {frauds}"
                net.add_edge(u, v, title=title, value=max(1, int(e.get("weight", 1))), color=edge_color)

            # Renderizar HTML del canvas interactivo
            # HTML embebido sin escritura intermedia: evita codificaciones de Windows
            # y que sesiones simultáneas sobrescriban el mismo subgrafo.
            html_content = net.generate_html()
            components.html(html_content, height=550)
            st.caption("Amarillo: cuenta seleccionada · Azul: clientes · Verde: comercios · Rojo en conexiones: fraude etiquetado en la muestra.")

            # Tablas con detalle de transacciones
            with st.expander(":material/table_view: Ver detalle tabular de conexiones"):
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
        fanout_p = st.slider("Percentil para Alto Fan-out (Dispersión)", 90.0, 99.9, 95.0, 0.5,
                            help="Un percentil mayor selecciona menos cuentas, con conexiones salientes más inusuales.")
    with pat_col2:
        fanin_p = st.slider("Percentil para Alto Fan-in (Concentración)", 90.0, 99.9, 95.0, 0.5,
                           help="Un percentil mayor selecciona menos cuentas, con conexiones entrantes más inusuales.")

    patterns_resp = _call_api(
        "patterns/suspicious",
        {"fanout_pct": fanout_p, "fanin_pct": fanin_p},
    )

    if patterns_resp is not None:
        total_detected = patterns_resp.get("total_detected", 0)
        results = patterns_resp.get("results", [])

        if total_detected:
            status_notice("warning", f"{total_detected:,} cuentas con patrones atípicos",
                          "Revisar las conexiones y los patrones de cada cuenta. Una anomalía estructural no confirma fraude.")
        else:
            status_notice("info", "Sin patrones por encima de estos umbrales",
                          "El resultado corresponde a la muestra y filtros actuales; no garantiza ausencia de fraude.")

        if results:
            display_df = pd.DataFrame(results)
            display_df["patterns"] = display_df["patterns"].apply(
                lambda pts: " • ".join(pts) if isinstance(pts, list) else str(pts)
            )
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

    top_resp = _call_api("top", {"metric": metric_choice, "top_n": n_top})
    if top_resp is not None:
        st.dataframe(pd.DataFrame(top_resp["results"]), use_container_width=True)

# -------------------------------------------------------------
# TAB 4: COMPARACIÓN DE ALERTAS DE RED VS REFERENCIA POR VOLUMEN
# -------------------------------------------------------------
with tab_compare:
    st.subheader("Comparación de alertas de red frente a una referencia por volumen")
    st.markdown(
        "Ambos métodos ordenan el **mismo universo de cuentas** y seleccionan **el mismo número "
        "de cuentas (k)**. Es una evaluación exploratoria sobre la misma muestra observada; no "
        "es una predicción temporal ni evidencia sobre la red completa."
    )
    comparison, comparison_notice = _fetch_comparison()
    if comparison_notice:
        status_notice("warning", *comparison_notice)
        st.caption(
            "Las demás pestañas siguen disponibles. Para esta muestra, ejecute "
            "`scripts/evaluate_graph_alerts.py --limit <filas> --comparison-output ...`."
        )
    else:
        sample = comparison.get("sample", {})
        steps = f"steps {sample.get('min_step')}–{sample.get('max_step')}"
        st.markdown(
            f"**Muestra:** primeras {sample.get('requested_limit', 0):,} filas solicitadas "
            f"({sample.get('rows_read', 0):,} leídas, {steps}) · "
            f"**Universo:** {comparison.get('universe_size', 0):,} cuentas · "
            f"**Análisis:** `{comparison.get('analysis_id', '')}`"
        )
        st.markdown(chips([("info", "Datos simulados — evaluación retrospectiva")]), unsafe_allow_html=True)

        rows = []
        for item in comparison["comparisons"]:
            net = item.get("network_indicators", {})
            ref = item.get("volume_reference", {})
            levels = (
                ("Precisión de cuentas", "cuenta", "account_precision"),
                ("Recall de cuentas positivas", "cuenta", "account_recall"),
                ("Precisión de transacciones cubiertas", "transacción", "covered_transaction_precision"),
                ("Cobertura de fraude", "transacción", "fraud_coverage"),
            )
            for label, level, key in levels:
                diff = (item.get("difference") or {}).get(key)
                rows.append({
                    "k": item.get("k"),
                    "Métrica": label,
                    "Nivel": level,
                    "Red (indicadores)": _format_metric(net.get(key)),
                    "Referencia por volumen": _format_metric(ref.get(key)),
                    "Diferencia (pp)": "n/d" if diff is None else f"{diff * 100:+.2f}",
                })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption(
            "Las métricas de **cuenta** cuentan cuentas positivas (origen o destino de un fraude "
            "etiquetado); las de **transacción** cuentan cada fila cubierta una sola vez. "
            "Diferencia = red − referencia a igual k; no se elige un k ganador por el fraude observado."
        )

        with st.expander("Presupuestos, cobertura y conteos"):
            counts = []
            for item in comparison["comparisons"]:
                for name, label in (("network_indicators", "Red"), ("volume_reference", "Volumen")):
                    block = item.get(name, {})
                    counts.append({
                        "k": item.get("k"),
                        "k solicitado": ", ".join(str(v) for v in item.get("requested_budgets", [])),
                        "Método": label,
                        "Cuentas seleccionadas": block.get("selected_accounts"),
                        "Cuentas positivas": block.get("positive_accounts_selected"),
                        "Transacciones cubiertas": block.get("covered_transactions"),
                        "Fraudes cubiertos": block.get("covered_fraud_transactions"),
                    })
            st.dataframe(pd.DataFrame(counts), use_container_width=True, hide_index=True)

        with st.expander("Limitaciones"):
            for limitation in comparison.get("limitations", []):
                st.markdown(f"- {limitation}")

# -------------------------------------------------------------
# TAB 5: METODOLOGÍA Y CONTRATO DE VARIABLES
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
        - **Conexión:** Esta página consume la API REST de BankShield. Los datos se cargan bajo demanda;
          el tamaño de muestra controla la carga en el servidor.
        """
    )
