"""Variables de la regresión del monto: solo `type` y `oldbalanceOrg`.

Prohibido usar `amount`, `amount_bin`, saldos posteriores, etiquetas, IDs o step.
"""

import math

import numpy as np
import pandas as pd

TYPES = ("PAYMENT", "TRANSFER", "CASH_OUT", "DEBIT", "CASH_IN")
INPUT_FIELDS = ("type", "oldbalanceOrg")
TARGET = "amount"
FEATURE_COLUMNS = ["type", "oldbalanceOrg", "log_oldbalance", "zero_balance"]
NUMERIC_COLUMNS = ["oldbalanceOrg", "log_oldbalance", "zero_balance"]


def validate_inputs(types, balances):
    """Verifica catálogo de tipos y saldos finitos no negativos (los booleanos no son números)."""
    types = pd.Series(types, dtype="object")
    if not types.isin(TYPES).all():
        raise ValueError("type fuera del catálogo PaySim")
    if any(isinstance(v, (bool, np.bool_)) for v in balances):
        raise ValueError("oldbalanceOrg debe ser numérico")
    values = np.asarray(balances, dtype="float64")
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("oldbalanceOrg debe ser finito y no negativo")
    return types.to_numpy(), values


def build_regression_feature_frame(types, balances):
    """Matriz de predictores; ninguna columna depende del objetivo ni de campos posteriores."""
    kinds, values = validate_inputs(types, balances)
    return pd.DataFrame({
        "type": pd.Categorical(kinds, categories=list(TYPES)).astype(object),
        "oldbalanceOrg": values,
        "log_oldbalance": np.log1p(values),
        "zero_balance": (values == 0).astype("float64"),
    }, columns=FEATURE_COLUMNS)


def frame_from_dataset(frame):
    """Predictores desde una tabla D1 ignorando cualquier otra columna."""
    return build_regression_feature_frame(frame["type"].to_numpy(), frame["oldbalanceOrg"].to_numpy())
