"""Riesgo crediticio: solicitud, probabilidad calibrada y factores; solo consume la API."""

import os

import pandas as pd
import requests
import streamlit as st

API_URL = os.environ.get("BANKSHIELD_API_URL", "http://127.0.0.1:8000").rstrip("/")
st.set_page_config(page_title="Crédito | BankShield", page_icon="🛡️", layout="wide")
st.title("Riesgo crediticio")
st.caption("Demostración académica sobre un dataset público de solicitudes de préstamo.")
st.info("La clase positiva es un impago **asumido**: el significado de `loan_status` no está confirmado por la "
        "fuente. La probabilidad está calibrada con datos históricos, pero no define un monto ni un límite "
        "de crédito: ese cálculo requiere pérdida en caso de impago, plazo, margen y costo de fondeo.")

FACTOR_NAMES = {
    "person_age": "Edad", "person_income": "Ingreso anual", "person_emp_length": "Antigüedad laboral (años)",
    "loan_amnt": "Monto solicitado", "loan_percent_income": "Monto / ingreso",
    "cb_person_cred_hist_length": "Historial crediticio (años)",
    "person_home_ownership": "Vivienda", "loan_intent": "Finalidad",
    "cb_person_default_on_file": "Impago previo registrado",
}


def call_api(method, endpoint, **kwargs):
    try:
        response = requests.request(method, f"{API_URL}/api/credit/{endpoint}", timeout=20, **kwargs)
        if response.status_code == 503:
            st.error("El modelo no está disponible. Revisa su generación y las versiones del entorno del servidor.")
            return None
        if response.status_code == 422:
            st.error("Los datos no cumplen el contrato de la solicitud (rangos o coherencia edad/antigüedad).")
            return None
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        st.error("No se pudo consultar la API. Comprueba que está iniciada e inténtalo de nuevo.")
        return None


with st.form("credit_application"):
    left, right = st.columns(2)
    age = left.number_input("Edad", min_value=18, max_value=100, value=30, step=1)
    income = left.number_input("Ingreso anual", min_value=1.0, value=55000.0, step=1000.0)
    unknown_emp = left.checkbox("Antigüedad laboral desconocida")
    emp = left.number_input("Antigüedad laboral (años)", min_value=0.0, max_value=60.0, value=4.0)
    history = left.number_input("Historial crediticio (años)", min_value=0, max_value=60, value=5, step=1)
    home = right.selectbox("Vivienda", ["RENT", "MORTGAGE", "OWN", "OTHER"])
    intent = right.selectbox("Finalidad", ["PERSONAL", "EDUCATION", "MEDICAL", "VENTURE",
                                           "HOMEIMPROVEMENT", "DEBTCONSOLIDATION"])
    amount = right.number_input("Monto solicitado", min_value=1.0, value=10000.0, step=500.0)
    default_file = right.selectbox("Impago previo registrado", ["N", "Y"])
    submitted = st.form_submit_button("Evaluar solicitud")

if submitted:
    application = {
        "person_age": int(age), "person_income": float(income),
        "person_home_ownership": home, "person_emp_length": None if unknown_emp else float(emp),
        "loan_intent": intent, "loan_amnt": float(amount),
        "cb_person_default_on_file": default_file, "cb_person_cred_hist_length": int(history),
    }
    result = call_api("POST", "predict", json=application)
    st.session_state["credit_prediction"] = {"result": result, "input": application} if result is not None else None

prediction = st.session_state.get("credit_prediction")
if prediction:
    result = prediction["result"]
    columns = st.columns(3)
    columns[0].metric("Probabilidad de impago (asumido)", f"{result['default_probability']:.1%}")
    columns[1].metric("Umbral de alto riesgo", f"{result['threshold']:.1%}")
    columns[2].metric("Clasificación", "Alto riesgo" if result["high_risk"] else "Riesgo bajo")
    st.caption(f"Modelo: {result['model_id']}")
    st.write("Se marca alto riesgo cuando la probabilidad es mayor o igual al umbral. "
             "El umbral procede de costes académicos supuestos (aprobar a un moroso cuesta 5× rechazar a un buen pagador).")
    with st.expander("Factores que más mueven la probabilidad", expanded=True):
        rows = [{"Variable": FACTOR_NAMES.get(f["feature"], f["feature"]), "Valor": str(f["value"]),
                 "Referencia (mediana/moda)": str(f["reference"]), "Efecto en probabilidad": f["effect"]}
                for f in result["factors"]]
        st.dataframe(pd.DataFrame(rows), hide_index=True)
        st.caption("Efecto = probabilidad con el dato real − probabilidad al sustituirlo por la referencia del "
                   "entrenamiento. Es una descripción del modelo, no una relación causal; positivo sube el riesgo.")

st.subheader("Evaluación del modelo cargado")
if st.button("Consultar métricas y versión"):
    evaluation = call_api("GET", "model")
    if evaluation is not None:
        st.caption(f"Modelo: {evaluation['model_id']}")
        if prediction and evaluation["model_id"] != prediction["result"]["model_id"]:
            st.warning("El modelo cambió desde la predicción mostrada. Vuelve a evaluar para comparar.")
        test = evaluation.get("test") or {}
        rows = [{"Modelo": name, "ROC-AUC": r["roc_auc"], "AP": r["average_precision"], "Brier": r["brier"],
                 "ECE": r["ece"], "Precisión": r["precision"], "Recall": r["recall"]}
                for name, r in test.items()]
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True)
            st.caption("Partición aleatoria estratificada sin fecha ni cliente: puede sobreestimar el desempeño "
                       "sobre clientes futuros. Los modelos «sin calibrar» usan umbral 0.5 solo como referencia.")
        else:
            st.warning("El artefacto no incluye métricas de prueba.")
        st.json({key: evaluation.get(key) for key in
                 ("source", "training_input", "main_model", "partitions", "versions",
                  "threshold_selection", "limitations")})
