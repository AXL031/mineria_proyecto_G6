"""Modelos de referencia y Holt-Winters para series temporales."""

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


def holt_winters_forecast(
    history: Sequence[float],
    horizon: int,
    *,
    seasonal_periods: int = 24,
    trend: str | None = "add",
    seasonal: str = "add",
    damped_trend: bool = False,
    clip_lower: float | None = 0.0,
) -> np.ndarray:
    """Ajusta Holt-Winters al historial y pronostica sin usar datos futuros.

    El recorte inferior es parte del contrato del dominio: cantidades y montos
    no pueden ser negativos. Se puede desactivar pasando ``clip_lower=None``.
    """

    values = _validated_history(history)
    horizon = _positive_integer("horizon", horizon)
    seasonal_periods = _positive_integer("seasonal_periods", seasonal_periods)
    if len(values) < 2 * seasonal_periods:
        raise ValueError(
            "El historial debe contener al menos dos periodos estacionales completos"
        )
    if trend not in {None, "add"}:
        raise ValueError("trend debe ser null o 'add'")
    if seasonal != "add":
        raise ValueError("seasonal debe ser 'add'")
    if not isinstance(damped_trend, bool):
        raise ValueError("damped_trend debe ser booleano")
    if damped_trend and trend is None:
        raise ValueError("damped_trend requiere una tendencia")
    if clip_lower is not None:
        try:
            clip_lower = float(clip_lower)
        except (TypeError, ValueError) as error:
            raise ValueError("clip_lower debe ser numérico o null") from error
        if not np.isfinite(clip_lower):
            raise ValueError("clip_lower debe ser finito")

    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    fitted = ExponentialSmoothing(
        values,
        trend=trend,
        damped_trend=damped_trend,
        seasonal=seasonal,
        seasonal_periods=seasonal_periods,
        initialization_method="estimated",
    ).fit(optimized=True, remove_bias=False)
    if not bool(fitted.mle_retvals.get("success", False)):
        raise ValueError("El ajuste Holt-Winters no convergió")
    prediction = np.asarray(fitted.forecast(horizon), dtype="float64")
    if not np.isfinite(prediction).all():
        raise ValueError("Holt-Winters produjo valores no finitos")
    if clip_lower is not None:
        prediction = np.maximum(prediction, clip_lower)
    return prediction
