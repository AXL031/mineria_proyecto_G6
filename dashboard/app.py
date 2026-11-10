"""Punto de entrada del panel: navegación por secciones con títulos e iconos.

``scripts/start_demo.ps1`` ejecuta ``streamlit run dashboard/app.py``. Cada
página sigue siendo un script independiente que llama a ``configure_page``;
este archivo solo define el menú y conserva las rutas existentes.
"""

from pathlib import Path

import streamlit as st

HERE = Path(__file__).resolve().parent

st.logo(str(HERE / "assets/bankshield-logo.svg"), size="large")

PAGES = {
    "": [
        st.Page("inicio.py", title="Inicio", icon=":material/home:", default=True),
    ],
    "Riesgo y fraude": [
        st.Page("pages/01_fraude.py", title="Detección de fraude", icon=":material/shield:", url_path="fraude"),
        st.Page("pages/02_credito.py", title="Riesgo crediticio", icon=":material/credit_card:", url_path="credito"),
        st.Page("pages/07_regresion.py", title="Regresión del monto", icon=":material/stacked_line_chart:", url_path="regresion"),
    ],
    "Transacciones": [
        st.Page("pages/03_redes.py", title="Redes de transacciones", icon=":material/hub:", url_path="redes"),
        st.Page("pages/04_pronosticos.py", title="Pronósticos", icon=":material/trending_up:", url_path="pronosticos"),
        st.Page("pages/06_segmentos.py", title="Segmentos de cuentas", icon=":material/category:", url_path="segmentos"),
    ],
    "Texto": [
        st.Page("pages/05_reclamos.py", title="Reclamos y NLP", icon=":material/forum:", url_path="reclamos"),
    ],
}

st.navigation(PAGES, position="sidebar").run()
