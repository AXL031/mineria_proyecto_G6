"""Variables iniciales para scoring antes de ejecutar una operación."""

from bankshield.ingestion.paysim_profile import TRANSACTION_TYPES, nonnegative_number


RAW_FEATURES = ("type", "amount", "oldbalanceOrg")
MODEL_FEATURES = (*RAW_FEATURES, "amount_to_origin_balance", "exceeds_origin_balance")
EXCLUDED_FIELDS = (
    "newbalanceOrig", "newbalanceDest", "isFraud", "isFlaggedFraud",
    "nameOrig", "nameDest", "step", "oldbalanceDest",
)


def build_fraud_features(record: dict) -> dict:
    """Construye un registro sin etiquetas, IDs ni balances posteriores.

    `oldbalanceOrg` requiere confirmación de disponibilidad en el sistema real.
    No normaliza ni ajusta estadísticas usando la población de prueba.
    """
    tx_type = record.get("type")
    if tx_type not in TRANSACTION_TYPES:
        raise ValueError("type: tipo transaccional desconocido")
    amount = nonnegative_number(record.get("amount"), "amount")
    balance = nonnegative_number(record.get("oldbalanceOrg"), "oldbalanceOrg")
    return {
        "type": tx_type,
        "amount": amount,
        "oldbalanceOrg": balance,
        "amount_to_origin_balance": amount / (balance + 1.0),
        "exceeds_origin_balance": int(amount > balance),
    }


def build_fraud_feature_frame(records):
    """Versión vectorizada del mismo contrato para entrenamiento por bloques."""
    import numpy as np
    import pandas as pd

    if not set(RAW_FEATURES).issubset(records.columns):
        raise ValueError(f"Faltan predictores: {sorted(set(RAW_FEATURES) - set(records.columns))}")
    if not records["type"].isin(TRANSACTION_TYPES).all():
        raise ValueError("type: tipo transaccional desconocido o ausente")
    values = {}
    for field in ("amount", "oldbalanceOrg"):
        column = pd.to_numeric(records[field], errors="raise").astype("float64")
        if not np.isfinite(column).all() or (column < 0).any():
            raise ValueError(f"{field}: valores ausentes, negativos o no finitos")
        values[field] = column
    frame = pd.DataFrame({"type": records["type"].astype(str), **values}, index=records.index)
    frame["amount_to_origin_balance"] = frame["amount"] / (frame["oldbalanceOrg"] + 1.0)
    frame["exceeds_origin_balance"] = (frame["amount"] > frame["oldbalanceOrg"]).astype("int8")
    return frame.loc[:, list(MODEL_FEATURES)]
