"""Reclamos CFPB: clasificación de narrativa, tendencias y revisión de errores por HTTP."""

import os

import pandas as pd
import requests
import streamlit as st
from bankshield.ui import configure_page, status_notice

API_URL = os.environ.get("BANKSHIELD_API_URL", "http://127.0.0.1:8000").rstrip("/")
configure_page(page_title="Reclamos | BankShield", page_icon="🗣", layout="wide")
st.title("Reclamos y clasificación de producto")
st.caption("Narrativas públicas de CFPB. El modelo se entrenó con textos en inglés.")
st.info("El producto sugerido describe el tema del texto. Las puntuaciones no están calibradas y no predicen la resolución del reclamo.")


def call_api(endpoint, narrative=None):
    try:
        if narrative is None:
            response = requests.get(f"{API_URL}/api/complaints/{endpoint}", timeout=30)
        else:
            response = requests.post(f"{API_URL}/api/complaints/{endpoint}", json={"narrative": narrative}, timeout=30)
        if response.status_code == 503:
            st.error("El artefacto de reclamos no está disponible. Ejecuta la preparación de la demo.")
            return None
        if response.status_code == 422:
            detail = response.json().get("detail")
            st.warning(detail if isinstance(detail, str) else "Escribe una narrativa en inglés de al menos cinco palabras.")
            return None
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        st.error("No se pudo consultar reclamos. Comprueba que la API esté iniciada.")
        return None


with st.form("complaint_narrative"):
    narrative = st.text_area("Narrativa en inglés", value="My credit report contains an account that does not belong to me. I disputed the incorrect information with the credit bureau but it has not been removed.", height=140)
    submitted = st.form_submit_button("Clasificar reclamo")
if submitted:
    st.session_state["complaints_prediction"] = call_api("predict", narrative)
prediction = st.session_state.get("complaints_prediction")
if prediction:
    status_notice("info", f"Producto sugerido: {prediction['product']}",
                  "Clasificación del tema del texto; no indica que el reclamo haya sido resuelto.")
    st.dataframe(pd.DataFrame(prediction["alternatives"]).rename(columns={"product": "Producto", "score": "Puntuación"}), hide_index=True)

st.subheader("Cobertura y tendencias")
if st.button("Consultar tendencias"):
    st.session_state["complaints_summary"] = call_api("summary")
summary = st.session_state.get("complaints_summary")
if summary:
    columns = st.columns(3)
    columns[0].metric("Reclamos", f"{summary['total_complaints']:,}")
    columns[1].metric("Con narrativa", f"{summary['with_narrative']:,}")
    columns[2].metric("Cobertura de texto", f"{summary['with_narrative'] / summary['total_complaints']:.1%}")
    st.caption(f"Periodo: {summary['first_date']} a {summary['last_date']}. Los agregados incluyen reclamos sin texto; el clasificador solo se entrenó con narrativas suficientes.")
    st.line_chart(pd.DataFrame(summary["monthly"]).set_index("month")[["complaints", "narratives"]])
    st.dataframe(pd.DataFrame(summary["products"]), hide_index=True)

st.subheader("Evaluación cronológica y ejemplos")
if st.button("Consultar evaluación"):
    st.session_state["complaints_evaluation"] = call_api("model")
evaluation = st.session_state.get("complaints_evaluation")
if evaluation:
    st.dataframe(pd.DataFrame([{"Modelo": key, "Macro-F1": value["macro_f1"], "Exactitud": value["accuracy"], "Top-3": value["top3_accuracy"]} for key, value in evaluation["test"].items()]), hide_index=True)
    st.caption("Prueba temporal independiente; solo narrativas publicadas. La revisión humana cruzada sigue pendiente.")
if st.button("Consultar ejemplos de prueba"):
    st.session_state["complaints_examples"] = call_api("examples")
examples = st.session_state.get("complaints_examples")
if examples:
    for title, key in (("Aciertos", "correct_examples"), ("Errores con puntuación alta", "high_confidence_errors")):
        with st.expander(title, expanded=True):
            st.dataframe(pd.DataFrame(examples[key]), hide_index=True)
