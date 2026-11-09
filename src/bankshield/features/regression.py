"""Predictores de monto: exclusivamente tipo y saldo anterior, sin el objetivo."""

import numpy as np
import pandas as pd

from bankshield.ingestion.paysim_profile import TRANSACTION_TYPES

FEATURES = ("type", "oldbalanceOrg", "log_origin_balance", "zero_origin_balance")


def build_regression_features(records):
    frame = pd.DataFrame(records)
    if not {"type", "oldbalanceOrg"}.issubset(frame.columns):
        raise ValueError("Se requieren type y oldbalanceOrg")
    if not frame.type.isin(TRANSACTION_TYPES).all():
        raise ValueError("Tipo PaySim desconocido")
    if frame.oldbalanceOrg.map(lambda value: isinstance(value, (bool, np.bool_))).any():
        raise ValueError("Saldo booleano inválido")
    balance = pd.to_numeric(frame.oldbalanceOrg, errors="raise").to_numpy(dtype=float)
    if not np.isfinite(balance).all() or (balance < 0).any():
        raise ValueError("Saldo debe ser finito y no negativo")
    return pd.DataFrame({"type": frame.type.to_numpy(), "oldbalanceOrg": balance,
                         "log_origin_balance": np.log1p(balance),
                         "zero_origin_balance": (balance == 0).astype(float)}, index=frame.index)
