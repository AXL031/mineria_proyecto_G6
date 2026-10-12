"""Servicio de proyección temporal para la API y el panel."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from bankshield.models.forecast import naive_forecast


TARGETS = ("transaction_count", "total_amount")


def _validated_series(series: pd.DataFrame, target: str) -> pd.DataFrame:
    if target not in TARGETS:
        raise ValueError("Objetivo de pronóstico no soportado")
    if not isinstance(series, pd.DataFrame):
        raise TypeError("La serie debe ser un DataFrame")
    missing = sorted({"step", target}.difference(series.columns))
    if missing:
        raise ValueError("Faltan columnas de la serie: " + ", ".join(missing))
    if series.empty:
        raise ValueError("La serie temporal está vacía")

    selected = series.loc[:, ["step", target]].copy().sort_values("step")
    selected["step"] = pd.to_numeric(selected["step"], errors="coerce")
    selected[target] = pd.to_numeric(selected[target], errors="coerce")
    if selected.isna().any().any() or not np.isfinite(selected).all().all():
        raise ValueError("La serie contiene valores inválidos")
    if not np.equal(selected["step"], np.floor(selected["step"])).all():
        raise ValueError("Los steps deben ser enteros")
    selected["step"] = selected["step"].astype("int64")
    if selected["step"].duplicated().any():
        raise ValueError("La serie contiene steps duplicados")
    expected = np.arange(selected["step"].min(), selected["step"].max() + 1)
    if not np.array_equal(selected["step"].to_numpy(), expected):
        raise ValueError("La serie debe contener steps consecutivos")
    if (selected[target] < 0).any():
        raise ValueError("El objetivo debe ser no negativo")
    return selected.reset_index(drop=True)


def _positive_integer(name: str, value: object, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ValueError(f"{name} debe estar entre 1 y {maximum}")
    return value


def _empirical_change_interval(
    values: np.ndarray,
    forecast: np.ndarray,
    *,
    lower_quantile: float = 0.1,
    upper_quantile: float = 0.9,
) -> tuple[np.ndarray, np.ndarray]:
    lower = np.empty(len(forecast), dtype="float64")
    upper = np.empty(len(forecast), dtype="float64")
    for index, prediction in enumerate(forecast, start=1):
        changes = values[index:] - values[:-index]
        lower[index - 1] = max(
            0.0,
            min(prediction, prediction + np.quantile(changes, lower_quantile)),
        )
        upper[index - 1] = max(
            prediction,
            prediction + np.quantile(changes, upper_quantile),
        )
    return lower, upper


def build_forecast_projection(
    series: pd.DataFrame,
    *,
    target: str,
    horizon: int = 24,
    history_steps: int = 168,
) -> dict[str, object]:
    """Construye una proyección Naive y un intervalo empírico no calibrado."""

    horizon = _positive_integer("horizon", horizon, 168)
    history_steps = _positive_integer("history_steps", history_steps, 718)
    selected = _validated_series(series, target)
    if len(selected) <= horizon:
        raise ValueError("La serie no tiene historial suficiente para el horizonte")

    values = selected[target].to_numpy(dtype="float64")
    prediction = naive_forecast(values, horizon)
    lower, upper = _empirical_change_interval(values, prediction)
    last_step = int(selected["step"].iloc[-1])
    visible = selected.tail(min(history_steps, len(selected)))
    history = [
        {"step": int(row.step), "value": float(getattr(row, target))}
        for row in visible.itertuples(index=False)
    ]
    forecast = [
        {
            "step": last_step + offset,
            "prediction": float(prediction[offset - 1]),
            "lower": float(lower[offset - 1]),
            "upper": float(upper[offset - 1]),
        }
        for offset in range(1, horizon + 1)
    ]
    return {
        "target": target,
        "selected_model": "naive",
        "last_observed_step": last_step,
        "last_observed_value": float(values[-1]),
        "horizon": horizon,
        "history": history,
        "forecast": forecast,
        "uncertainty": {
            "method": "empirical_horizon_change_quantiles",
            "lower_quantile": 0.1,
            "upper_quantile": 0.9,
            "calibrated": False,
        },
        "simulation_data": True,
        "limitations": [
            "Naive repite la última observación y no anticipa cambios de régimen.",
            "El intervalo resume cambios históricos y no tiene cobertura calibrada.",
            "Los steps son horas simuladas de PaySim, no fechas reales.",
        ],
    }


def monitoring_summary(report: Mapping[str, object]) -> dict[str, object]:
    """Valida los campos mínimos del reporte antes de exponerlo por HTTP."""

    required = (
        "experiment_id",
        "reference",
        "observed",
        "changes",
        "type_mix",
        "thresholds",
        "alerts",
        "alert_count",
        "status",
        "limitations",
    )
    missing = sorted(set(required).difference(report))
    if missing:
        raise ValueError("El reporte de monitoreo está incompleto: " + ", ".join(missing))
    if report["status"] not in {"stable", "change_detected"}:
        raise ValueError("El estado de monitoreo no es compatible")
    return {key: report[key] for key in required}
