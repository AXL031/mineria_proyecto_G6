"""Modelos de referencia para pronósticos de series temporales."""

from collections.abc import Sequence
from numbers import Integral

import numpy as np


def _positive_integer(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value < 1:
        raise ValueError(f"{name} debe ser un entero positivo")
    return int(value)


def _validated_history(history: Sequence[float]) -> np.ndarray:
    try:
        values = np.asarray(history, dtype="float64")
    except (TypeError, ValueError) as error:
        raise ValueError("El historial debe contener valores numéricos") from error
    if values.ndim != 1 or not len(values):
        raise ValueError("El historial debe ser un vector no vacío")
    if not np.isfinite(values).all():
        raise ValueError("El historial debe contener valores finitos")
    return values


def naive_forecast(history: Sequence[float], horizon: int) -> np.ndarray:
    """Repite el último valor observado durante todo el horizonte."""

    values = _validated_history(history)
    horizon = _positive_integer("horizon", horizon)
    return np.full(horizon, values[-1], dtype="float64")


def seasonal_naive_forecast(
    history: Sequence[float],
    horizon: int,
    seasonal_period: int = 24,
) -> np.ndarray:
    """Repite el último ciclo observado para pronosticar el siguiente."""

    values = _validated_history(history)
    horizon = _positive_integer("horizon", horizon)
    seasonal_period = _positive_integer("seasonal_period", seasonal_period)
    if len(values) < seasonal_period:
        raise ValueError(
            "El historial debe contener al menos un periodo estacional completo"
        )

    last_cycle = values[-seasonal_period:]
    repetitions = int(np.ceil(horizon / seasonal_period))
    return np.tile(last_cycle, repetitions)[:horizon].copy()
