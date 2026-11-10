"""Portal Principal de BankShield Analytics."""

import streamlit as st
from bankshield.ui import configure_page, module_cards, page_header, status_notice

configure_page(
    page_title="BankShield Analytics",
    page_icon="🛡",
    layout="wide",
    initial_sidebar_state="expanded",
)

page_header(
    "BankShield Analytics",
    "Plataforma académica de minería de datos y analítica financiera: fraude, riesgo, "
    "redes, pronósticos, reclamos, segmentos y regresión sobre datos públicos y simulados.",
    eyebrow="Proyecto grupal de Minería de Datos · G6",
    highlight="Analytics",
    badges=(
        ("database", "PaySim · CFPB · Riesgo crediticio"),
        ("network", "API REST + panel"),
        ("info", "Resultados exploratorios", "yellow"),
    ),
)

status_notice(
    "warning",
    "Aviso académico",
    "Los módulos operan sobre datasets públicos y simulados (PaySim). Las predicciones y "
    "métricas son exploratorias y de apoyo a la decisión; no describen clientes reales.",
)

st.subheader(":material/apps: Módulos de la plataforma")
module_cards([
    {"icon": "shield", "tone": "red", "title": "Detección de fraude",
     "text": "Evalúa una operación con el modelo supervisado, su umbral y sus métricas."},
    {"icon": "credit-card", "tone": "blue", "title": "Riesgo crediticio",
     "text": "Probabilidad calibrada de impago y factores que explican cada solicitud."},
    {"icon": "network", "tone": "green", "title": "Redes de transacciones",
     "text": "Topología nameOrig → nameDest, patrones atípicos, subgrafos y comparación red vs volumen."},
    {"icon": "trending-up", "tone": "yellow", "title": "Pronósticos de flujo",
     "text": "Proyección del volumen o monto por hora y monitoreo del cambio histórico."},
    {"icon": "message", "tone": "cyan", "title": "Reclamos y NLP",
     "text": "Producto sugerido por narrativa, tendencias y ejemplos de errores de CFPB."},
    {"icon": "layers", "tone": "green", "title": "Segmentos de cuentas",
     "text": "Agrupamiento de cuentas destino reincidentes sin usar la etiqueta de fraude."},
    {"icon": "line-chart", "tone": "blue", "title": "Regresión del monto",
     "text": "Estimación del monto transaccional por tipo de operación y saldo previo."},
])

st.subheader(":material/explore: Cómo navegar")
col_steps, col_tip = st.columns([3, 2], gap="large")
with col_steps:
    st.markdown(
        """
        1. **Elige un módulo** en el menú lateral; cada página consume la API de BankShield.
        2. **Ajusta los parámetros** de la página (muestra, umbrales, formulario) y consulta los resultados.
        3. **Revisa los avisos** de cada módulo: indican el alcance y los límites de los datos.
        4. **Contrasta** las métricas con la documentación en `docs/` antes de interpretarlas.
        """
    )
with col_tip:
    with st.container(border=True):
        st.markdown("**:material/hub: Redes y grafos**")
        st.markdown(
            "Métricas topológicas, explorador interactivo de subgrafos, patrones de abanico y "
            "concentración, ranking por PageRank y comparación justa red vs referencia por volumen."
        )

st.divider()
st.caption("BankShield Analytics v0.1.0 — Proyecto Grupal de Minería de Datos (G6)")
