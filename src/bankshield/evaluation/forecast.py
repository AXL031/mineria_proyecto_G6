"""Ventanas temporales y métricas para evaluar pronósticos."""

import hashlib
import json
import platform
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from numbers import Integral
from pathlib import Path

import numpy as np
import pandas as pd

from bankshield.models.forecast import naive_forecast, seasonal_naive_forecast


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


def _configured_targets(evaluation_config: Mapping[str, object]) -> tuple[str, ...]:
    targets = evaluation_config.get("targets")
    if not isinstance(targets, Sequence) or isinstance(targets, (str, bytes)):
        raise ValueError("targets debe ser una lista")
    if not targets or any(not isinstance(target, str) or not target for target in targets):
        raise ValueError("Los objetivos deben ser nombres no vacíos")
    if len(targets) != len(set(targets)):
        raise ValueError("Los objetivos no pueden repetirse")
    return tuple(targets)


def _configured_models(
    evaluation_config: Mapping[str, object],
) -> tuple[tuple[str, ...], int]:
    models = evaluation_config.get("models")
    if not isinstance(models, Mapping):
        raise ValueError("models debe ser un objeto")
    expected = {"naive", "seasonal_naive"}
    if set(models) != expected:
        raise ValueError("El experimento requiere naive y seasonal_naive")
    seasonal = models["seasonal_naive"]
    if not isinstance(seasonal, Mapping) or "lag" not in seasonal:
        raise ValueError("seasonal_naive requiere el parámetro lag")
    lag = _positive_integer("seasonal_naive.lag", seasonal["lag"])
    return tuple(models), lag


def evaluate_forecast_baselines(
    series: pd.DataFrame,
    evaluation_config: Mapping[str, object],
) -> dict[str, object]:
    """Ejecuta ambos modelos sobre las mismas ventanas y agrega sus métricas."""

    if not isinstance(series, pd.DataFrame):
        raise TypeError("La serie debe ser un DataFrame")
    targets = _configured_targets(evaluation_config)
    missing_targets = [target for target in targets if target not in series.columns]
    if missing_targets:
        raise ValueError("Faltan objetivos en Gold: " + ", ".join(missing_targets))

    windows = backtest_windows_from_config(evaluation_config)
    model_names, seasonal_lag = _configured_models(evaluation_config)
    metrics_config = evaluation_config.get("metrics")
    if not isinstance(metrics_config, Mapping):
        raise ValueError("metrics debe ser un objeto")

    window_reports = []
    for window in windows:
        train, test = split_backtest_window(series, window)
        results = {}
        for target in targets:
            history = train[target].to_numpy()
            actual = test[target].to_numpy()
            predictions = {
                "naive": naive_forecast(history, window.horizon),
                "seasonal_naive": seasonal_naive_forecast(
                    history,
                    window.horizon,
                    seasonal_period=seasonal_lag,
                ),
            }
            results[target] = {
                model: {
                    "metrics": calculate_forecast_metrics(actual, predictions[model])
                }
                for model in model_names
            }

        window_reports.append(
            {
                "id": window.id,
                "train": {
                    "start_step": window.train_start_step,
                    "end_step": window.train_end_step,
                    "rows": int(len(train)),
                },
                "test": {
                    "start_step": window.test_start_step,
                    "end_step": window.test_end_step,
                    "rows": int(len(test)),
                },
                "results": results,
            }
        )

    aggregates = {}
    for target in targets:
        aggregates[target] = {}
        for model in model_names:
            aggregates[target][model] = {
                metric: float(
                    np.mean(
                        [
                            window["results"][target][model]["metrics"][metric]
                            for window in window_reports
                        ]
                    )
                )
                for metric in ("mae", "rmse", "smape")
            }
            aggregates[target][model]["window_count"] = len(window_reports)

    numeric_steps = pd.to_numeric(series["step"], errors="coerce")
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": evaluation_config.get("experiment_id"),
        "versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "series_coverage": {
            "rows": int(len(series)),
            "min_step": int(numeric_steps.min()),
            "max_step": int(numeric_steps.max()),
        },
        "protocol": {
            "targets": list(targets),
            "horizon": evaluation_config.get("horizon"),
            "operational_period": dict(evaluation_config["operational_period"]),
            "monitoring_period": dict(evaluation_config.get("monitoring_period", {})),
            "models": dict(evaluation_config["models"]),
            "metrics": dict(metrics_config),
        },
        "windows": window_reports,
        "aggregates": aggregates,
    }


def _file_sha256(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest()


def _display_path(path: Path, base_dir: Path | None) -> str:
    if base_dir is not None:
        try:
            return str(path.resolve().relative_to(Path(base_dir).resolve()))
        except ValueError:
            pass
    return str(path)


def run_forecast_baseline_evaluation(
    input_path: Path,
    output_path: Path,
    evaluation_config: Mapping[str, object],
    *,
    base_dir: Path | None = None,
) -> dict[str, object]:
    """Lee Gold, ejecuta el backtesting y escribe el reporte JSON."""

    input_path = Path(input_path)
    output_path = Path(output_path)
    if not input_path.exists():
        raise ValueError(f"No existe la tabla Gold temporal: {input_path}")

    targets = _configured_targets(evaluation_config)
    series = pd.read_parquet(input_path, columns=["step", *targets])
    report = evaluate_forecast_baselines(series, evaluation_config)
    report["source"] = {
        "path": _display_path(input_path, base_dir),
        "format": "parquet",
        "sha256": _file_sha256(input_path),
    }
    report["output"] = {
        "path": _display_path(output_path, base_dir),
        "format": "json",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return report
