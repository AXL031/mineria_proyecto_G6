"""Variables de comportamiento por cuenta de destino reincidente.

Construye una fila por cuenta destino que recibió al menos
``min_transactions`` operaciones, con métricas de actividad, monto,
composición por tipo, contrapartes y fraude. Las cuentas que reciben una sola
vez se excluyen porque no aportan comportamiento estable (ver
``docs/transacciones/segmentacion.md``).

Se incluyen variables absolutas (para el perfil) y variables sin escala
(proporciones, concentración y dispersión) para que el agrupamiento no se
reduzca a un corte por tamaño.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from bankshield.ingestion.paysim_profile import TRANSACTION_TYPES

REQUIRED_COLUMNS = ("nameDest", "nameOrig", "type", "amount", "step", "isFraud")
ACCOUNT_COLUMN = "account"
TYPE_SHARE_COLUMNS = tuple(f"share_{name.lower()}" for name in TRANSACTION_TYPES)
BEHAVIOR_COLUMNS = (
    "n_received",
    "n_sent",
    "total_received",
    "total_sent",
    "net_flow",
    "mean_received_amount",
    "std_received_amount",
    "cv_received_amount",
    "max_received_amount",
    "amount_concentration",
    "distinct_senders",
    "sender_concentration",
    "active_steps",
    "activity_density",
    *TYPE_SHARE_COLUMNS,
    "fraud_received",
    "fraud_rate_received",
)


def _safe_divide(numerator: pd.Series | pd.DataFrame, denominator: pd.Series | pd.DataFrame) -> pd.Series | pd.DataFrame:
    """Divide evitando cero: donde el denominador no es positivo, devuelve 0."""
    if hasattr(numerator, "to_numpy") and hasattr(denominator, "to_numpy"):
        numbers = numerator.to_numpy(dtype="float64")
        divisors = denominator.to_numpy(dtype="float64")
    result = np.divide(numbers, divisors, out=np.zeros_like(numbers), where=divisors > 0)
    if numbers.ndim > 1 or isinstance(numerator, pd.DataFrame):
        index = numerator.index if hasattr(numerator, "index") else pd.RangeIndex(numbers.shape[0])
        columns = numerator.columns if hasattr(numerator, "columns") else None
        return pd.DataFrame(result, index=index, columns=columns)
    index = numerator.index if hasattr(numerator, "index") else pd.RangeIndex(len(numbers))
    return pd.Series(result, index=index, dtype="float64")
    numbers = pd.to_numeric(numerator, errors="raise")
    divisors = pd.to_numeric(denominator, errors="raise")
    result = np.divide(numbers, divisors, out=np.zeros_like(numbers), where=divisors > 0)
    return result


def build_account_features(
    transactions: pd.DataFrame, min_transactions: int = 10
) -> pd.DataFrame:
    """Agrega comportamiento por cuenta destino con actividad >= umbral."""
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(transactions.columns))
    if missing_columns:
        raise ValueError(f"Faltan columnas requeridas: {missing_columns}")
    if transactions.empty:
        raise ValueError("El dataset transaccional está vacío")
    if min_transactions < 1:
        raise ValueError("min_transactions debe ser un entero positivo")

    amount = pd.to_numeric(transactions["amount"], errors="raise").astype("float64")
    fraud = pd.to_numeric(transactions["isFraud"], errors="raise")
    if not np.isfinite(amount).all() or (amount < 0).any():
        raise ValueError("amount debe ser finito y no negativo")
    if not fraud.isin([0, 1]).all():
        raise ValueError("isFraud debe contener únicamente 0 o 1")
    if not transactions["type"].isin(TRANSACTION_TYPES).all():
        raise ValueError("type: tipo transaccional desconocido o ausente")

    source = transactions.loc[:, list(REQUIRED_COLUMNS)].copy()
    source["amount"] = amount
    source["isFraud"] = fraud.astype("int64")

    received = source.groupby("nameDest", sort=True, observed=True).agg(
        n_received=("amount", "size"),
        total_received=("amount", "sum"),
        mean_received_amount=("amount", "mean"),
        std_received_amount=("amount", "std"),
        max_received_amount=("amount", "max"),
        distinct_senders=("nameOrig", "nunique"),
        active_steps=("step", "nunique"),
        fraud_received=("isFraud", "sum"),
    )
    received = received.loc[received["n_received"] >= min_transactions]

    sent = source.groupby("nameOrig", sort=True, observed=True).agg(
        n_sent=("amount", "size"),
        total_sent=("amount", "sum"),
    )

    type_counts = (
        source.groupby(["nameDest", "type"], observed=True)
        .size()
        .unstack(fill_value=0)
    )
    for tx in TRANSACTION_TYPES:
        if tx not in type_counts.columns:
            type_counts[tx] = 0
    type_counts = type_counts.reindex(columns=list(TRANSACTION_TYPES), fill_value=0)
    type_shares = type_counts.div(type_counts.sum(axis=1), axis=0).fillna(0).astype("float64")
    type_shares.columns = list(TYPE_SHARE_COLUMNS)

    features = received.join(sent, how="left").join(type_shares, how="left")
    features["n_sent"] = features["n_sent"].fillna(0).astype("int64")
    features["total_sent"] = features["total_sent"].fillna(0.0).astype("float64")
    features["std_received_amount"] = features["std_received_amount"].fillna(0.0)
    for column in TYPE_SHARE_COLUMNS:
        features[column] = features[column].fillna(0.0).astype("float64")

    features["net_flow"] = features["total_received"] - features["total_sent"]
    features["cv_received_amount"] = _safe_divide(
        features["std_received_amount"], features["mean_received_amount"]
    )
    features["amount_concentration"] = _safe_divide(
        features["max_received_amount"], features["total_received"]
    )
    features["sender_concentration"] = 1.0 - _safe_divide(
        features["distinct_senders"], features["n_received"]
    )
    features["activity_density"] = _safe_divide(
        features["n_received"], features["active_steps"]
    ).replace(0.0, np.nan).fillna(1.0)
    features["fraud_rate_received"] = features["fraud_received"] / features["n_received"]

    features = features.rename_axis(ACCOUNT_COLUMN).reset_index()
    features["account"] = features["account"].astype(str)
    ordered = [ACCOUNT_COLUMN, *BEHAVIOR_COLUMNS]
    return (
        features.loc[:, ordered]
        .sort_values("n_received", ascending=False)
        .reset_index(drop=True)
    )
