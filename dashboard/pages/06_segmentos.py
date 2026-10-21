"""Vista de segmentos que consume exclusivamente la API de BankShield.

Los resultados provienen de los artefactos generados por
``scripts/segment_transactions.py``. El agrupamiento no usa la etiqueta de
fraude; ``fraud_rate`` aparece solo para describir cada segmento ya formado.
"""

import os

import pandas as pd
import requests
import streamlit as st
from bankshield.ui import configure_page

API_URL = os.environ.get("BANKSHIELD_API_URL", "http://127.0.0.1:8000").rstrip("/")

configure_page(page_title="Segmentos | BankShield", page_icon="🧩", layout="wide")
st.title("Segmentos de cuentas destino")
st.caption("Agrupamiento de cuentas reincidentes (>= 10 transacciones recibidas) sobre PaySim.")
st.info(
    "El agrupamiento no usa la etiqueta de fraude: `fraud_rate` se muestra solo "
    "para describir cada grupo tras formarlo. PaySim es una simulación; los "
    "segmentos no representan clientes reales."
)


def call_api(endpoint):
    try:
        response = requests.get(f"{API_URL}/api/segments/{endpoint}", timeout=20)
        if response.status_code == 503:
            st.error(
                "Faltan los artefactos de segmentos. Genéralos con "
                "scripts/segment_transactions.py y revisa el estado del servidor."
            )
            return None
        if response.status_code == 404:
            st.warning("El recurso solicitado no existe.")
            return None
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        st.error("No se pudo consultar la API. Comprueba que está iniciada e inténtalo de nuevo.")
        return None


summary = call_api("summary")
if summary is None:
    st.stop()

metrics = summary["metrics"]
columns = st.columns(4)
columns[0].metric("Cuentas reincidentes", f"{summary['total_accounts']:,}")
columns[1].metric("k elegido", metrics["chosen_k"])
columns[2].metric("Silueta", f"{metrics['silhouette']:.4f}")
columns[3].metric("Estabilidad ARI", f"{metrics['mean_stability_ari']:.4f}")

st.subheader("Selección de k y estabilidad")
silhouette = pd.DataFrame(
    [{"k": int(k), "Silueta (muestra)": value} for k, value in metrics["silhouette_by_k"].items()]
).sort_values("k")
st.dataframe(silhouette, hide_index=True, use_container_width=True)
st.caption(
    "La silueta se calcula sobre una muestra por costo computacional. "
    "Estabilidad: ARI medio en remuestras (1 = muy estable)."
)

st.subheader("Perfiles por segmento (KMeans)")
st.dataframe(pd.DataFrame(summary["profiles"]), hide_index=True, use_container_width=True)

st.subheader("Línea base (cuantiles de actividad)")
st.dataframe(pd.DataFrame(summary["baseline_profiles"]), hide_index=True, use_container_width=True)

st.subheader("Explorar cuentas del segmento")
segments = sorted({row["segment"] for row in summary["profiles"]})
segment_id = st.selectbox("Segmento", segments)
limit = st.slider("Cuentas a mostrar", min_value=10, max_value=500, value=50, step=10)

accounts = call_api(f"{segment_id}/accounts?limit={limit}")
if accounts is not None:
    st.caption(f"{accounts['count']:,} cuentas mostradas del segmento {segment_id}.")
    st.dataframe(pd.DataFrame(accounts["accounts"]), hide_index=True, use_container_width=True)
