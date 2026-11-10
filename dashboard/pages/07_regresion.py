"""Regresión del monto transaccional: estimación por tipo y saldo; solo consume la API."""

import os

import pandas as pd
import requests
import streamlit as st
from bankshield.ui import configure_page

API_URL = os.environ.get("BANKSHIELD_API_URL", "http://127.0.0.1:8000").rstrip("/")
TYPES = ["PAYMENT", "TRANSFER", "CASH_OUT", "DEBIT", "CASH_IN"]
configure_page(page_title="Regresión | BankShield", page_icon="📈", layout="wide")
st.title("Estimación del monto transaccional")
st.caption("Demostración académica sobre PaySim, un conjunto de datos simulado.")
st.info("Estima `amount` a partir del tipo de operación y del saldo previo del origen. No es una alerta de "
        "fraude ni un límite de crédito, no tiene moneda real y no incluye intervalos de confianza. "
        "Con estos dos predictores se espera poco poder explicativo.")


def call_api(endpoint, method="GET", **kwargs):
    try:
        response = requests.request(method, f"{API_URL}/api/regression/{endpoint}", timeout=20, **kwargs)
        if response.status_code == 503:
            st.error("El modelo no está disponible. Revisa su generación y las versiones del entorno del servidor.")
            return None
        if response.status_code == 422:
            st.error("Los datos no cumplen el contrato: tipo válido y saldo finito no negativo.")
            return None
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        st.error("No se pudo consultar la API. Comprueba que está iniciada e inténtalo de nuevo.")
        return None


with st.form("regression_form"):
    kind = st.selectbox("Tipo de operación", TYPES, index=1)
    balance = st.number_input("Saldo previo del origen (oldbalanceOrg)", min_value=0.0, value=500.0, step=100.0)
    submitted = st.form_submit_button("Estimar monto")

if submitted:
    result = call_api("predict", "POST", json={"type": kind, "oldbalanceOrg": float(balance)})
    st.session_state["regression_prediction"] = (
        {"result": result, "input": {"type": kind, "oldbalanceOrg": float(balance)}} if result is not None else None)

prediction = st.session_state.get("regression_prediction")
if prediction:
    result = prediction["result"]
    st.metric("Monto estimado (unidades simuladas)", f"{result['prediction']:,.2f}")
    st.caption(f"Modelo seleccionado: {result['selected_model']} · identidad: {result['model_id']}")
    for text in result["limitations"]:
        st.warning(text)

st.subheader("Evaluación del modelo cargado")
if st.button("Consultar comparación y ejemplos"):
    evaluation = call_api("model")
    if evaluation is not None:
        st.caption(f"Modelo: {evaluation['model_id']}")
        if prediction and evaluation["model_id"] != prediction["result"]["model_id"]:
            st.warning("El modelo cambió desde la estimación mostrada. Vuelve a estimar para comparar.")
        comparison = evaluation.get("comparison") or {}
        for part, title in (("validation", "Validation (usada para elegir el modelo)"),
                            ("test", "Test (no usada para elegir)")):
            rows = [{"Modelo": name, "Seleccionado": "Sí" if name == evaluation["selected_model"] else "",
                     "n": scores[part]["n"], "MAE": scores[part]["mae"], "RMSE": scores[part]["rmse"],
                     "R²": scores[part]["r2"], "Sesgo medio": scores[part]["mean_bias"]}
                    for name, scores in comparison.items()]
            if rows:
                st.markdown(f"**{title}**")
                st.dataframe(pd.DataFrame(rows), hide_index=True)
        stress = [{"Modelo": name, "n": s["stress"]["n"], "MAE": s["stress"]["mae"], "RMSE": s["stress"]["rmse"]}
                  for name, s in comparison.items()]
        if stress:
            with st.expander("Stress (steps 719-743, solo fraude; no comparable con test)"):
                st.dataframe(pd.DataFrame(stress), hide_index=True)
        st.caption("MAE, RMSE y sesgo en la escala original del monto (unidades simuladas). "
                   "Sesgo = media(estimado − real).")
        examples = call_api("examples", params={"limit": 100, "offset": 0})
        if examples is not None and examples["rows"]:
            data = pd.DataFrame(examples["rows"])[["row_id", "type", "actual", "prediction"]]
            st.markdown("**Real vs estimado (ejemplos aleatorios de test)**")
            st.scatter_chart(data, x="actual", y="prediction")
            st.dataframe(data.rename(columns={"actual": "Real", "prediction": "Estimado"}), hide_index=True)
            st.caption(f"{len(data)} de {examples['total']} ejemplos; no son toda la evaluación ni solo aciertos.")
        st.json({key: evaluation.get(key) for key in ("selection_rule", "train_sample", "partitions", "versions",
                                                      "limitations")})
