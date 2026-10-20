"""Pronóstico de volumen y monitoreo temporal mediante la API."""

import os

import pandas as pd
import requests
import streamlit as st
from bankshield.ui import configure_page


API_URL = os.environ.get("BANKSHIELD_API_URL", "http://127.0.0.1:8000").rstrip("/")
configure_page(page_title="Pronósticos | BankShield", page_icon="📈", layout="wide")
st.title("Pronósticos y monitoreo transaccional")
st.caption("Demostración académica sobre horas simuladas de PaySim.")
st.info(
    "El modelo seleccionado es Naive porque obtuvo el menor MAE frente a Naive "
    "estacional y Holt-Winters. Los intervalos son descriptivos y no están calibrados."
)


def call_api(endpoint: str, params: dict | None = None):
    try:
        response = requests.get(
            f"{API_URL}/api/forecast/{endpoint}",
            params=params,
            timeout=30,
        )
        if response.status_code == 503:
            st.error(
                "El artefacto temporal no está disponible. Ejecuta la construcción "
                "Gold y el monitoreo antes de iniciar la API."
            )
            return None
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        st.error("No se pudo consultar la API temporal. Comprueba que esté iniciada.")
        return None


left, middle, right = st.columns(3)
target_label = left.selectbox(
    "Objetivo",
    ["Cantidad de transacciones", "Monto total"],
)
target = (
    "transaction_count" if target_label == "Cantidad de transacciones" else "total_amount"
)
horizon = middle.slider("Horizonte (steps)", min_value=1, max_value=72, value=24)
history_steps = right.slider(
    "Historia visible (steps)", min_value=24, max_value=336, value=168, step=24
)

if st.button("Generar proyección", type="primary"):
    result = call_api(
        "projection",
        {"target": target, "horizon": horizon, "history_steps": history_steps},
    )
    st.session_state["forecast_projection"] = result

projection = st.session_state.get("forecast_projection")
if projection:
    if projection["target"] != target:
        st.warning("La proyección mostrada corresponde al objetivo consultado anteriormente.")
    metrics = st.columns(3)
    value_format = ",.0f" if projection["target"] == "transaction_count" else ",.2f"
    metrics[0].metric(
        "Último valor observado",
        format(projection["last_observed_value"], value_format),
    )
    metrics[1].metric("Último step", projection["last_observed_step"])
    metrics[2].metric("Modelo seleccionado", projection["selected_model"])

    history = pd.DataFrame(projection["history"]).rename(columns={"value": "Historia"})
    forecast = pd.DataFrame(projection["forecast"]).rename(
        columns={"prediction": "Pronóstico", "lower": "Límite inferior", "upper": "Límite superior"}
    )
    chart = history.set_index("step").join(
        forecast.set_index("step")[["Pronóstico", "Límite inferior", "Límite superior"]],
        how="outer",
    )
    st.line_chart(chart)
    st.caption(
        "Los límites utilizan los percentiles 10 y 90 de cambios históricos para "
        "cada horizonte. No son intervalos probabilísticos calibrados."
    )
    with st.expander("Limitaciones del pronóstico"):
        for limitation in projection["limitations"]:
            st.write(f"- {limitation}")

st.divider()
st.subheader("Cambio histórico del tramo final")
if st.button("Consultar monitoreo"):
    st.session_state["forecast_monitoring"] = call_api("monitoring")

monitoring = st.session_state.get("forecast_monitoring")
if monitoring:
    status = monitoring["status"]
    if status == "change_detected":
        st.warning(
            f"Cambio detectado: {monitoring['alert_count']} indicadores superan "
            "los umbrales descriptivos."
        )
    else:
        st.success("No se detectaron cambios por encima de los umbrales.")

    reference = monitoring["reference"]
    observed = monitoring["observed"]
    changes = monitoring["changes"]
    columns = st.columns(4)
    columns[0].metric(
        "Transacciones observadas",
        f"{observed['transaction_count']:,}",
        f"{changes['transaction_count_relative_change']:.1%}",
    )
    columns[1].metric(
        "Monto observado",
        f"{observed['total_amount']:,.2f}",
        f"{changes['total_amount_relative_change']:.1%}",
    )
    columns[2].metric(
        "Monto promedio",
        f"{observed['average_amount']:,.2f}",
        f"{changes['average_amount_relative_change']:.1%}",
    )
    columns[3].metric(
        "Tasa de fraude",
        f"{observed['fraud_rate']:.1%}",
        f"{changes['fraud_rate_absolute_change']:+.1%}",
    )
    st.caption(
        f"Referencia: steps {reference['start_step']}–{reference['end_step']}; "
        f"observado: {observed['start_step']}–{observed['end_step']}."
    )

    type_rows = [
        {
            "Tipo": category,
            "Referencia": values["reference_share"] * 100,
            "Observado": values["observed_share"] * 100,
            "Cambio pp": values["percentage_point_change"] * 100,
        }
        for category, values in monitoring["type_mix"]["categories"].items()
    ]
    st.dataframe(
        pd.DataFrame(type_rows),
        hide_index=True,
        column_config={
            "Referencia": st.column_config.NumberColumn(format="%.2f%%"),
            "Observado": st.column_config.NumberColumn(format="%.2f%%"),
            "Cambio pp": st.column_config.NumberColumn(format="%+.2f"),
        },
    )
    st.caption(
        "Las proporciones de la tabla se comparan descriptivamente. PaySim es una "
        "simulación y el tramo final contiene solo transacciones etiquetadas como fraude."
    )
