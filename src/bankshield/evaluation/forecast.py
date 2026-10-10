"""Ventanas temporales y métricas para evaluar pronósticos."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from numbers import Integral

import numpy as np
import pandas as pd


def _positive_integer(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value < 1:
        raise ValueError(f"{name} debe ser un entero positivo")
    return int(value)


@dataclass(frozen=True)
class BacktestWindow:
    """Rangos inclusivos de entrenamiento y evaluación de una ventana."""

    id: str
    train_start_step: int
    train_end_step: int
    test_start_step: int
    test_end_step: int

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("El identificador de la ventana no puede estar vacío")
        for field in (
            "train_start_step",
            "train_end_step",
            "test_start_step",
            "test_end_step",
        ):
            object.__setattr__(self, field, _positive_integer(field, getattr(self, field)))
        if self.train_start_step > self.train_end_step:
            raise ValueError("El inicio de entrenamiento supera su final")
        if self.test_start_step > self.test_end_step:
            raise ValueError("El inicio de evaluación supera su final")
        if self.train_end_step >= self.test_start_step:
            raise ValueError("El entrenamiento debe ser anterior a la evaluación")
        if self.test_start_step != self.train_end_step + 1:
            raise ValueError("Entrenamiento y evaluación deben ser periodos consecutivos")

    @property
    def horizon(self) -> int:
        return self.test_end_step - self.test_start_step + 1


def validate_backtest_windows(
    windows: Sequence[BacktestWindow],
    *,
    expected_horizon: int | None = None,
    operational_start_step: int | None = None,
    operational_end_step: int | None = None,
) -> tuple[BacktestWindow, ...]:
    """Valida horizonte, límites y expansión cronológica de las ventanas."""

    validated = tuple(windows)
    if not validated:
        raise ValueError("Se requiere al menos una ventana de backtesting")
    if not all(isinstance(window, BacktestWindow) for window in validated):
        raise TypeError("Todas las ventanas deben ser BacktestWindow")

    if expected_horizon is not None:
        expected_horizon = _positive_integer("expected_horizon", expected_horizon)
        if any(window.horizon != expected_horizon for window in validated):
            raise ValueError("Todas las ventanas deben respetar el horizonte esperado")

    if (operational_start_step is None) != (operational_end_step is None):
        raise ValueError("Se requieren ambos límites del periodo operativo")
    if operational_start_step is not None and operational_end_step is not None:
        operational_start_step = _positive_integer(
            "operational_start_step", operational_start_step
        )
        operational_end_step = _positive_integer(
            "operational_end_step", operational_end_step
        )
        if operational_start_step > operational_end_step:
            raise ValueError("El periodo operativo es inválido")
        if any(
            window.train_start_step < operational_start_step
            or window.test_end_step > operational_end_step
            for window in validated
        ):
            raise ValueError("Una ventana queda fuera del periodo operativo")

    identifiers = [window.id for window in validated]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Los identificadores de ventana deben ser únicos")

    first_train_start = validated[0].train_start_step
    for previous, current in zip(validated, validated[1:]):
        if current.train_start_step != first_train_start:
            raise ValueError("Las ventanas deben usar entrenamiento expansivo")
        if current.train_end_step != previous.test_end_step:
            raise ValueError("Cada entrenamiento debe incorporar la evaluación anterior")
        if current.test_start_step != previous.test_end_step + 1:
            raise ValueError("Las ventanas de evaluación deben ser consecutivas")

    return validated


def generate_expanding_windows(
    *,
    train_start_step: int,
    first_train_end_step: int,
    horizon: int,
    folds: int,
) -> tuple[BacktestWindow, ...]:
    """Genera ventanas consecutivas con un origen de entrenamiento fijo."""

    train_start_step = _positive_integer("train_start_step", train_start_step)
    first_train_end_step = _positive_integer(
        "first_train_end_step", first_train_end_step
    )
    horizon = _positive_integer("horizon", horizon)
    folds = _positive_integer("folds", folds)
    if train_start_step > first_train_end_step:
        raise ValueError("El inicio de entrenamiento supera su final")

    windows = []
    for index in range(folds):
        train_end_step = first_train_end_step + index * horizon
        test_start_step = train_end_step + 1
        windows.append(
            BacktestWindow(
                id=f"W{index + 1:02d}",
                train_start_step=train_start_step,
                train_end_step=train_end_step,
                test_start_step=test_start_step,
                test_end_step=test_start_step + horizon - 1,
            )
        )
    return validate_backtest_windows(windows, expected_horizon=horizon)


def backtest_windows_from_config(
    evaluation_config: Mapping[str, object],
) -> tuple[BacktestWindow, ...]:
    """Construye y valida las ventanas declaradas en la configuración."""

    if not isinstance(evaluation_config, Mapping):
        raise TypeError("La configuración de evaluación debe ser un objeto")
    definitions = evaluation_config.get("backtest_windows")
    if not isinstance(definitions, Sequence) or isinstance(definitions, (str, bytes)):
        raise ValueError("backtest_windows debe ser una lista")

    required_fields = {
        "id",
        "train_start_step",
        "train_end_step",
        "test_start_step",
        "test_end_step",
    }
    windows = []
    for index, definition in enumerate(definitions, start=1):
        if not isinstance(definition, Mapping):
            raise ValueError(f"La ventana {index} debe ser un objeto")
        missing = required_fields.difference(definition)
        if missing:
            raise ValueError(
                f"Faltan campos en la ventana {index}: {', '.join(sorted(missing))}"
            )
        windows.append(
            BacktestWindow(
                id=definition["id"],
                train_start_step=definition["train_start_step"],
                train_end_step=definition["train_end_step"],
                test_start_step=definition["test_start_step"],
                test_end_step=definition["test_end_step"],
            )
        )

    operational_period = evaluation_config.get("operational_period")
    if not isinstance(operational_period, Mapping):
        raise ValueError("Falta operational_period en la configuración")
    if "start_step" not in operational_period or "end_step" not in operational_period:
        raise ValueError("El periodo operativo requiere start_step y end_step")

    return validate_backtest_windows(
        windows,
        expected_horizon=evaluation_config.get("horizon"),
        operational_start_step=operational_period["start_step"],
        operational_end_step=operational_period["end_step"],
    )


def split_backtest_window(
    series: pd.DataFrame,
    window: BacktestWindow,
    *,
    step_column: str = "step",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa una serie regular sin permitir steps duplicados o ausentes."""

    if not isinstance(series, pd.DataFrame):
        raise TypeError("La serie debe ser un DataFrame")
    if step_column not in series.columns:
        raise ValueError(f"Falta la columna temporal {step_column}")
    if series.empty:
        raise ValueError("La serie temporal está vacía")

    numeric_steps = pd.to_numeric(series[step_column], errors="coerce")
    if numeric_steps.isna().any() or not np.isfinite(numeric_steps).all():
        raise ValueError("Los steps deben ser números finitos")
    if not np.equal(numeric_steps, np.floor(numeric_steps)).all():
        raise ValueError("Los steps deben ser enteros")

    ordered = series.assign(**{step_column: numeric_steps.astype("int64")}).sort_values(
        step_column, kind="stable"
    )
    if ordered[step_column].duplicated().any():
        raise ValueError("La serie contiene steps duplicados")

    train = ordered.loc[
        ordered[step_column].between(window.train_start_step, window.train_end_step)
    ].copy()
    test = ordered.loc[
        ordered[step_column].between(window.test_start_step, window.test_end_step)
    ].copy()

    expected_train = np.arange(window.train_start_step, window.train_end_step + 1)
    expected_test = np.arange(window.test_start_step, window.test_end_step + 1)
    if not np.array_equal(train[step_column].to_numpy(), expected_train):
        raise ValueError(f"Faltan steps de entrenamiento para {window.id}")
    if not np.array_equal(test[step_column].to_numpy(), expected_test):
        raise ValueError(f"Faltan steps de evaluación para {window.id}")
    if train[step_column].max() >= test[step_column].min():
        raise ValueError("Se detectó fuga temporal entre entrenamiento y evaluación")

    return train.reset_index(drop=True), test.reset_index(drop=True)


def _metric_arrays(
    actual: Sequence[float], predicted: Sequence[float]
) -> tuple[np.ndarray, np.ndarray]:
    try:
        actual_array = np.asarray(actual, dtype="float64")
        predicted_array = np.asarray(predicted, dtype="float64")
    except (TypeError, ValueError) as error:
        raise ValueError("Los valores reales y pronosticados deben ser numéricos") from error
    if actual_array.ndim != 1 or predicted_array.ndim != 1:
        raise ValueError("Los valores reales y pronosticados deben ser vectores")
    if not len(actual_array) or len(actual_array) != len(predicted_array):
        raise ValueError("Los vectores deben ser no vacíos y tener igual longitud")
    if not np.isfinite(actual_array).all() or not np.isfinite(predicted_array).all():
        raise ValueError("Los valores reales y pronosticados deben ser finitos")
    return actual_array, predicted_array


def mean_absolute_error(
    actual: Sequence[float], predicted: Sequence[float]
) -> float:
    actual_array, predicted_array = _metric_arrays(actual, predicted)
    return float(np.mean(np.abs(actual_array - predicted_array)))


def root_mean_squared_error(
    actual: Sequence[float], predicted: Sequence[float]
) -> float:
    actual_array, predicted_array = _metric_arrays(actual, predicted)
    return float(np.sqrt(np.mean(np.square(actual_array - predicted_array))))


def symmetric_mean_absolute_percentage_error(
    actual: Sequence[float], predicted: Sequence[float]
) -> float:
    actual_array, predicted_array = _metric_arrays(actual, predicted)
    denominator = np.abs(actual_array) + np.abs(predicted_array)
    contributions = np.divide(
        200.0 * np.abs(actual_array - predicted_array),
        denominator,
        out=np.zeros_like(denominator),
        where=denominator != 0,
    )
    return float(np.mean(contributions))


def calculate_forecast_metrics(
    actual: Sequence[float], predicted: Sequence[float]
) -> dict[str, float]:
    """Calcula las tres métricas acordadas con una sola validación de entrada."""

    actual_array, predicted_array = _metric_arrays(actual, predicted)
    absolute_error = np.abs(actual_array - predicted_array)
    denominator = np.abs(actual_array) + np.abs(predicted_array)
    smape_terms = np.divide(
        200.0 * absolute_error,
        denominator,
        out=np.zeros_like(denominator),
        where=denominator != 0,
    )
    return {
        "mae": float(np.mean(absolute_error)),
        "rmse": float(np.sqrt(np.mean(np.square(actual_array - predicted_array)))),
        "smape": float(np.mean(smape_terms)),
    }
