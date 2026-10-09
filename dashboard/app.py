"""Portal Principal de BankShield Analytics."""

import streamlit as st

st.set_page_config(
    page_title="BankShield Analytics",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos personalizados para apariencia bancaria y profesional
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.4rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #475569;
        margin-bottom: 1.5rem;
    }
    .card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }
    .compliance-box {
        background-color: #FEF3C7;
        border-left: 4px solid #F59E0B;
        padding: 0.8rem 1rem;
        border-radius: 4px;
        color: #92400E;
        font-size: 0.9rem;
        margin-bottom: 1.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="main-title">🛡️ BankShield Analytics</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Plataforma académica integral de minería de datos y analítica financiera</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="compliance-box">
        ⚠️ <strong>Aviso Académico / Compliance:</strong> Los módulos presentados operan sobre datasets
        públicos y simulados (PaySim). Las predicciones y métricas son de carácter exploratorio y de apoyo a la decisión.
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📌 Módulos de la Plataforma")
    st.markdown(
        """
        - 🌐 **Redes y Grafos de Transacciones** (*Disponible*): Topología de relaciones `nameOrig → nameDest`,
          detección de comunidades/patrones atípicos y visualización interactiva de subgrafos.
        - 🕵️ **Detección de Fraude Supervisado** (*Disponible mediante API*): Formulario de predicción, umbral y métricas del modelo cargado.
        - 💳 **Riesgo Crediticio y Explicabilidad** (*En desarrollo*): Scoring y calibración de probabilidad de impago.
        - 🗣️ **Reclamos y NLP** (*En desarrollo*): Análisis semántico de quejas de clientes CFPB.
        - 📈 **Pronósticos de Flujo** (*En desarrollo*): Proyección de volúmenes transaccionales temporales.
        """
    )

with col2:
    st.markdown("### 🧭 Cómo Navegar")
    st.markdown(
        """
        Utiliza el menú lateral para acceder a **Fraude** y **Redes y Grafos**.
        En Fraude puedes evaluar una operación y consultar las métricas del modelo mediante la API.
        En Redes y Grafos encontrarás:
        
        1. **Métricas Topológicas:** KPIs globales de conectividad y volumen operado.
        2. **Explorador Interactivo de Subgrafos:** Búsqueda por cuenta y renderizado con física en tiempo real.
        3. **Detección de Patrones de Alerta:** Monitoreo de anomalías tipo abanico (*fan-out*), concentración (*fan-in*) y circularidad.
        4. **Ranking de Centralidad:** Identificación de nodos clave mediante PageRank.
        """
    )

st.divider()
st.caption("BankShield Analytics v0.1.0 — Proyecto Grupal de Minería de Datos (G6)")
