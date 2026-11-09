"""Estimación numérica del monto mediante HTTP; nunca entrena ni carga joblib."""

import os
import pandas as pd
import requests
import streamlit as st
from bankshield.ui import configure_page

API_URL = os.environ.get("BANKSHIELD_API_URL", "http://127.0.0.1:8000").rstrip("/")
configure_page(page_title="Regresión | BankShield", page_icon="📈", layout="wide")
st.title("Estimación del monto transaccional")
st.info("Experimento académico sobre PaySim. Estima un monto; no es una alerta de fraude ni una recomendación de crédito. La moneda no está verificada.")


def call_api(method, endpoint, **kwargs):
    try:
        response = requests.request(method, f"{API_URL}/api/regression/{endpoint}", timeout=30, **kwargs)
        if response.status_code == 503:
            st.error("El modelo o sus artefactos no están disponibles o no son compatibles. Regenera la entrega de regresión.")
            return None
        if response.status_code == 422:
            st.error("Tipo o saldo inválido: utiliza un tipo conocido y un saldo finito no negativo.")
            return None
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        st.error("No se pudo consultar la API de regresión.")
        return None


with st.form("regression_form"):
    kind = st.selectbox("Tipo de operación", ["TRANSFER", "CASH_OUT", "PAYMENT", "DEBIT", "CASH_IN"], key="regression_type")
    balance = st.number_input("Saldo anterior del origen", min_value=0.0, value=500.0, key="regression_balance")
    submitted = st.form_submit_button("Estimar monto", key="regression_predict")
if submitted:
    inputs = {"type": kind, "oldbalanceOrg": balance}
    result = call_api("POST", "predict", json=inputs)
    st.session_state["regression_prediction"] = {"input": inputs, "result": result} if result else None
prediction = st.session_state.get("regression_prediction")
if prediction:
    st.metric("Monto estimado", f"{prediction['result']['prediction']:,.2f}")
    st.caption(f"Modelo: {prediction['result']['model_id']} · {prediction['result']['selected_model']}")
    st.write("Entrada de esta estimación:", prediction["input"])
    if prediction["input"] != {"type": kind, "oldbalanceOrg": balance}:
        st.warning("La estimación conservada corresponde a controles anteriores. Pulsa Estimar monto para actualizarla.")

st.subheader("Evaluación y comparación")
if st.button("Consultar evaluación", key="regression_evaluation"):
    st.session_state["regression_evaluation_result"] = call_api("GET", "model")
evaluation = st.session_state.get("regression_evaluation_result")
if evaluation:
    st.caption(f"Selección: {evaluation['selected_model']} por MAE de validation; sin reajuste posterior.")
    if prediction and prediction["result"]["model_id"] != evaluation["model_id"]:
        st.warning("El modelo cambió desde la estimación mostrada. Vuelve a estimar antes de compararla.")
    for partition, label in (("validation", "Validación: selección"), ("test", "Prueba independiente"),
                             ("stress", "Stress: tramo 719–743, separado de prueba")):
        st.write(label)
        st.dataframe(pd.DataFrame([{"Candidato": name, **values["overall"]}
                                  for name, values in evaluation["evaluation"][partition].items()]), hide_index=True)
    st.json({key: evaluation[key] for key in ("dataset", "sampling", "selection", "limitations")})

st.subheader("Ejemplos de prueba")
st.caption("Muestra uniforme con semilla 42; incluye errores y no representa toda la prueba.")
if st.button("Consultar ejemplos", key="regression_examples"):
    st.session_state["regression_examples_result"] = call_api("GET", "examples", params={"limit": 100, "offset": 0})
examples = st.session_state.get("regression_examples_result")
if examples:
    if evaluation and examples["model_id"] != evaluation["model_id"]:
        st.warning("Los ejemplos y la evaluación corresponden a modelos distintos; vuelve a consultar ambos.")
    else:
        frame = pd.DataFrame(examples["rows"])
        if frame.empty:
            st.info("No hay ejemplos en esta página.")
        else:
            st.scatter_chart(frame, x="actual", y="prediction", x_label="Monto observado", y_label="Monto estimado")
            st.dataframe(frame[["type", "step", "actual", "prediction"]], hide_index=True)
