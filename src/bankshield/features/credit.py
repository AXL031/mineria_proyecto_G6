"""Contrato de variables de crédito: esquema, validez y matriz del modelo."""

import numpy as np
import pandas as pd

RAW_COLUMNS = (
    "person_age", "person_income", "person_home_ownership", "person_emp_length",
    "loan_intent", "loan_grade", "loan_amnt", "loan_int_rate", "loan_status",
    "loan_percent_income", "cb_person_default_on_file", "cb_person_cred_hist_length",
)
CATEGORIES = {
    "person_home_ownership": ("MORTGAGE", "OTHER", "OWN", "RENT"),
    "loan_intent": ("DEBTCONSOLIDATION", "EDUCATION", "HOMEIMPROVEMENT", "MEDICAL",
                    "PERSONAL", "VENTURE"),
    "loan_grade": ("A", "B", "C", "D", "E", "F", "G"),
    "cb_person_default_on_file": ("N", "Y"),
}
MIN_ADULT_AGE = 18
MAX_PLAUSIBLE_AGE = 100
MIN_WORKING_AGE = 14

# Variables conocidas en la solicitud, antes de que el prestamista fije condiciones.
APPLICATION_NUMERIC = ("person_age", "person_income", "person_emp_length", "loan_amnt",
                       "loan_percent_income", "cb_person_cred_hist_length")
APPLICATION_CATEGORICAL = ("person_home_ownership", "loan_intent", "cb_person_default_on_file")
# Las asigna el prestamista tras evaluar el riesgo; solo se usan en la variante comparativa.
PRICING_NUMERIC = ("loan_int_rate",)
PRICING_CATEGORICAL = ("loan_grade",)

FEATURE_SETS = {
    "application": (APPLICATION_NUMERIC, APPLICATION_CATEGORICAL),
    "with_pricing": (APPLICATION_NUMERIC + PRICING_NUMERIC,
                     APPLICATION_CATEGORICAL + PRICING_CATEGORICAL),
}
INPUT_FIELDS = ("person_age", "person_income", "person_emp_length", "loan_amnt",
                "cb_person_cred_hist_length", "person_home_ownership", "loan_intent",
                "cb_person_default_on_file")


def feature_columns(feature_set):
    numeric, categorical = FEATURE_SETS[feature_set]
    return list(numeric) + list(categorical)


def invalid_reasons(frame):
    """Serie de texto con el primer motivo por el que una fila no es utilizable ('' si lo es)."""
    reason = pd.Series("", index=frame.index, dtype="object")

    def mark(mask, text):
        mask = mask.fillna(True).to_numpy(dtype=bool)
        reason[mask & (reason == "").to_numpy()] = text

    age, income = frame["person_age"], frame["person_income"]
    emp, amount = frame["person_emp_length"], frame["loan_amnt"]
    mark(~frame["loan_status"].isin([0, 1]), "loan_status_invalid")
    for column, allowed in CATEGORIES.items():
        mark(~frame[column].isin(allowed), f"{column}_unknown_category")
    mark(~(age.between(MIN_ADULT_AGE, MAX_PLAUSIBLE_AGE)), "age_out_of_range")
    mark(~(income > 0), "income_not_positive")
    mark(~(amount > 0), "loan_amount_not_positive")
    mark(emp.notna() & ((emp < 0) | (emp > age - MIN_WORKING_AGE)), "emp_length_impossible")
    mark(~(frame["cb_person_cred_hist_length"].between(0, age - MIN_WORKING_AGE + 1)),
         "credit_history_impossible")
    return reason


def build_credit_feature_frame(records, feature_set="application"):
    """Valida entradas y crea la matriz en el orden del contrato; no usa la etiqueta."""
    frame = pd.DataFrame(records).copy()
    columns = feature_columns(feature_set)
    base = [name for name in columns if name != "loan_percent_income"]
    missing = [name for name in base if name not in frame.columns]
    if missing:
        raise ValueError(f"Faltan variables: {missing}")
    numeric = [name for name in columns if name in set(FEATURE_SETS[feature_set][0])]
    for name in numeric:
        if name in frame.columns:
            frame[name] = pd.to_numeric(frame[name], errors="raise")
    if "loan_percent_income" not in frame.columns:
        frame["loan_percent_income"] = frame["loan_amnt"] / frame["person_income"]
    for name in ("person_income", "loan_amnt", "person_age"):
        if not (frame[name] > 0).all() or not np.isfinite(frame[name]).all():
            raise ValueError(f"{name} debe ser positivo y finito")
    for name, allowed in CATEGORIES.items():
        if name in columns and not frame[name].isin(allowed).all():
            raise ValueError(f"{name} contiene categorías no admitidas")
    result = frame[columns].copy()
    result[list(numeric)] = result[list(numeric)].astype("float64")
    return result
