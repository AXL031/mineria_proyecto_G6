"""Demostración de fraude que consume exclusivamente la API."""

import os

import pandas as pd
import requests
import streamlit as st

API_URL = os.environ.get("BANKSHIELD_API_URL", "http://127.0.0.1:8000").rstrip("/")
st.set_page_config(page_title="Fraude | BankShield", page_icon="🛡️", layout="wide")
st.title("Detección de fraude")
st.caption("Demostración sobre transacciones simuladas de PaySim.")
st.info("El score no es una probabilidad calibrada. La alerta usa el umbral elegido en validación; los montos no tienen una moneda verificada.")
st.caption("El saldo anterior debe estar disponible antes de ejecutar la operación. Si no se dispone de él, este modelo no aplica; no sustituirlo por el saldo posterior ni inventar un valor.")


def call_api(method, endpoint, **kwargs):
    try:
        response = requests.request(method, f"{API_URL}/api/fraud/{endpoint}", timeout=20, **kwargs)
        if response.status_code == 503:
            if endpoint == "patterns":
                st.error("Los patrones no están disponibles. Genera el reporte para el modelo vigente y revisa que el modelo pueda cargarse.")
            else:
                st.error("El modelo no está disponible. Revisa su generación y las versiones del entorno del servidor.")
            return None
        if response.status_code == 422:
            st.error("Los datos enviados no cumplen el contrato de la transacción.")
            return None
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        st.error("No se pudo consultar la API. Comprueba que está iniciada e inténtalo de nuevo.")
        return None


with st.form("fraud_transaction"):
    tx_type = st.selectbox("Tipo de operación", ["TRANSFER", "CASH_OUT", "PAYMENT", "DEBIT", "CASH_IN"])
    amount = st.number_input("Monto solicitado", min_value=0.0, value=1000.0)
    balance = st.number_input("Saldo anterior del origen", min_value=0.0, value=500.0)
    submitted = st.form_submit_button("Evaluar transacción")

if submitted:
    transaction = {"type": tx_type, "amount": amount, "oldbalanceOrg": balance}
    result = call_api("POST", "predict", json=transaction)
    st.session_state["fraud_prediction"] = {"result": result, "input": transaction} if result is not None else None

prediction = st.session_state.get("fraud_prediction")
if prediction:
    result, transaction = prediction["result"], prediction["input"]
    columns = st.columns(3)
    columns[0].metric("Score", f"{result['score']:.6f}")
    columns[1].metric("Umbral", f"{result['threshold']:.6f}")
    columns[2].metric("Alerta", "Sí" if result["alert"] else "No")
    st.caption(f"Modelo: {result['model_id']}")
    st.write("La alerta se activa cuando el score es mayor o igual al umbral.")
    with st.expander("Condiciones observadas de la entrada"):
        amount, balance = transaction["amount"], transaction["oldbalanceOrg"]
        st.write(f"Monto / (saldo + 1): {amount / (balance + 1):.4f}")
        st.write(f"Monto supera saldo: {'sí' if amount > balance else 'no'}.")
        st.caption("Estas condiciones describen las variables de entrada; no son atribuciones causales ni una explicación de la decisión del modelo.")

st.subheader("Evaluación del modelo cargado")
if st.button("Consultar métricas y versión"):
    evaluation = call_api("GET", "model")
    if evaluation is not None:
        st.caption(f"Modelo: {evaluation['model_id']}")
        if prediction and evaluation["model_id"] != prediction["result"]["model_id"]:
            st.warning("El modelo cambió desde la predicción mostrada. Vuelve a evaluar para comparar con estas métricas.")
        test = evaluation.get("test") or {}
        selected = test.get("classifier_selected")
        if selected:
            st.dataframe(pd.DataFrame([{
                "AP": selected["average_precision"], "Precisión": selected["precision"],
                "Recall": selected["recall"], "F1": selected["f1"],
                **selected["confusion"],
            }]), hide_index=True)
            st.caption("Evaluación temporal histórica del artefacto; no mide el desempeño de la transacción individual.")
        else:
            st.warning("El artefacto no incluye métricas de prueba.")
        st.json({key: evaluation.get(key) for key in
                 ("source", "training_input", "partitions", "versions", "threshold_selection", "limitations")})

st.subheader("Patrones descriptivos")
st.caption("Asociaciones históricas entre condiciones de entrada y la etiqueta de fraude. No son causas, atribuciones del modelo ni reglas de decisión bancaria.")
if st.button("Consultar patrones históricos"):
    patterns = call_api("GET", "patterns")
    if patterns is not None:
        st.caption(f"Modelo: {patterns['model_id']}")
        if prediction and patterns["model_id"] != prediction["result"]["model_id"]:
            st.warning("El modelo cambió desde la predicción mostrada. Vuelve a evaluar para comparar.")
        for name, title in (("train", "Entrenamiento"), ("validation", "Validación"), ("test", "Prueba")):
            part = patterns["partitions"][name]
            with st.expander(f"{title}: {part['rows']:,} operaciones", expanded=name == "test"):
                st.write(f"Prevalencia de fraude: {part['prevalence']:.4%}")
                st.dataframe(pd.DataFrame([
                    {"Regla": row["description"], "Coincidencias": row["matches"],
                     "Fraudes": row["fraud_matches"], "Soporte": f"{row['support']:.2%}",
                     "Confianza": f"{row['confidence']:.2%}" if row["confidence"] is not None else "N/D",
                     "Lift": f"{row['lift']:.2f}" if row["lift"] is not None else "N/D",
                     "Cobertura": f"{row['fraud_coverage']:.2%}" if row["fraud_coverage"] is not None else "N/D"} for row in part["rules"]
                ]), hide_index=True)
        st.caption("Soporte: fracción de operaciones que cumplen la regla. Confianza: proporción de fraude entre coincidencias. Lift: confianza / prevalencia. Cobertura: fracción de fraudes cubiertos. Las reglas se solapan y no se suman. Se definieron sin seleccionar por resultados en prueba.")
