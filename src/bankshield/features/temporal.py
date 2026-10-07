"""Análisis exploratorio de la serie temporal Gold de PaySim."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt


REQUIRED_COLUMNS = (
    "step",
    "transaction_count",
    "total_amount",
    "average_amount",
    "fraud_count",
    "fraud_rate",
)


def prepare_temporal_series(gold: pd.DataFrame, seasonal_period: int = 24) -> pd.DataFrame:
    """Valida Gold y añade ciclo horario y medias móviles."""
    if seasonal_period < 2:
        raise ValueError("seasonal_period debe ser al menos 2")
    missing = sorted(set(REQUIRED_COLUMNS) - set(gold.columns))
    if missing:
        raise ValueError(f"Faltan columnas Gold requeridas: {missing}")
    if gold.empty:
        raise ValueError("La tabla Gold está vacía")

    series = gold.loc[:, list(REQUIRED_COLUMNS)].copy().sort_values("step")
    if series["step"].duplicated().any():
        raise ValueError("Gold debe tener una sola fila por step")
    expected_steps = list(
        range(int(series["step"].min()), int(series["step"].max()) + 1)
    )
    if series["step"].astype(int).tolist() != expected_steps:
        raise ValueError("Gold debe tener una secuencia regular de steps")
    if series[list(REQUIRED_COLUMNS)].isna().any().any():
        raise ValueError("Gold no puede contener valores nulos")

    first_step = int(series["step"].min())
    series["simulated_hour"] = (
        (series["step"].astype("int64") - first_step) % seasonal_period
    ).astype("int64")
    series["transaction_count_ma24"] = series["transaction_count"].rolling(
        seasonal_period, min_periods=1
    ).mean()
    series["total_amount_ma24"] = series["total_amount"].rolling(
        seasonal_period, min_periods=1
    ).mean()
    return series.reset_index(drop=True)


def final_fraud_only_start(series: pd.DataFrame) -> int | None:
    """Devuelve el inicio del tramo final cuya actividad es totalmente fraude."""
    start: int | None = None
    for row in reversed(list(series.itertuples(index=False))):
        if row.transaction_count > 0 and row.transaction_count == row.fraud_count:
            start = int(row.step)
        else:
            break
    return start


def _metric_summary(values: pd.Series) -> dict[str, float]:
    return {
        "mean": float(values.mean()),
        "median": float(values.median()),
        "std": float(values.std(ddof=1)),
        "min": float(values.min()),
        "max": float(values.max()),
    }


def summarize_temporal_series(
    series: pd.DataFrame, seasonal_period: int = 24
) -> dict:
    """Resume la serie y compara el periodo operativo con el tramo final."""
    tail_start = final_fraud_only_start(series)
    operational = series if tail_start is None else series[series["step"] < tail_start]
    tail = series.iloc[0:0] if tail_start is None else series[series["step"] >= tail_start]

    autocorrelation = {}
    for lag in (1, seasonal_period, seasonal_period * 7):
        autocorrelation[str(lag)] = {
            "transaction_count": (
                float(operational["transaction_count"].autocorr(lag=lag))
                if len(operational) > lag
                else None
            ),
            "total_amount": (
                float(operational["total_amount"].autocorr(lag=lag))
                if len(operational) > lag
                else None
            ),
        }

    hourly = (
        operational.groupby("simulated_hour", sort=True)
        .agg(
            mean_transaction_count=("transaction_count", "mean"),
            mean_total_amount=("total_amount", "mean"),
        )
        .reset_index()
    )
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "seasonal_period": seasonal_period,
        "coverage": {
            "min_step": int(series["step"].min()),
            "max_step": int(series["step"].max()),
            "steps": int(len(series)),
            "final_fraud_only_start": tail_start,
            "operational_steps": int(len(operational)),
            "tail_steps": int(len(tail)),
        },
        "operational": {
            "transaction_count": _metric_summary(operational["transaction_count"]),
            "total_amount": _metric_summary(operational["total_amount"]),
        },
        "tail": {
            "transaction_count": (
                _metric_summary(tail["transaction_count"]) if not tail.empty else None
            ),
            "total_amount": _metric_summary(tail["total_amount"]) if not tail.empty else None,
        },
        "autocorrelation": autocorrelation,
        "hourly_cycle": hourly.to_dict(orient="records"),
    }


def _format_correlation(value: float | None) -> str:
    return "No disponible" if value is None or np.isnan(value) else f"{value:.4f}"


def _shade_tail(ax: plt.Axes, tail_start: int | None, max_step: int) -> None:
    if tail_start is not None:
        ax.axvspan(
            tail_start,
            max_step,
            color="#D55E00",
            alpha=0.12,
            label="Tramo final solo fraude",
        )


def _plot_time_series(
    series: pd.DataFrame,
    value_column: str,
    rolling_column: str,
    title: str,
    y_label: str,
    output_path: Path,
    tail_start: int | None,
) -> None:
    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.plot(
        series["step"],
        series[value_column],
        color="#0072B2",
        linewidth=0.9,
        alpha=0.65,
        label="Valor por step",
    )
    ax.plot(
        series["step"],
        series[rolling_column],
        color="#E69F00",
        linewidth=2.0,
        label="Media móvil de 24 steps",
    )
    _shade_tail(ax, tail_start, int(series["step"].max()))
    ax.set_title(title)
    ax.set_xlabel("Step (hora simulada)")
    ax.set_ylabel(y_label)
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def _plot_hourly_cycle(series: pd.DataFrame, output_path: Path) -> None:
    hourly = (
        series.groupby("simulated_hour", sort=True)
        .agg(
            transaction_count=("transaction_count", "mean"),
            total_amount=("total_amount", "mean"),
        )
        .reset_index()
    )
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    axes[0].plot(
        hourly["simulated_hour"],
        hourly["transaction_count"],
        marker="o",
        color="#0072B2",
    )
    axes[0].set_title("Actividad promedio dentro del ciclo simulado de 24 horas")
    axes[0].set_ylabel("Transacciones promedio")
    axes[0].grid(axis="y", alpha=0.25)

    axes[1].plot(
        hourly["simulated_hour"],
        hourly["total_amount"],
        marker="o",
        color="#009E73",
    )
    axes[1].set_xlabel("Posición dentro del ciclo de 24 horas (0–23)")
    axes[1].set_ylabel("Monto total promedio")
    axes[1].grid(axis="y", alpha=0.25)
    axes[1].set_xticks(range(24))
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def _write_markdown(report: dict, plots: dict[str, str], path: Path) -> None:
    coverage = report["coverage"]
    operational = report["operational"]
    tail = report["tail"]
    autocorrelation = report["autocorrelation"]
    lines = [
        "# Exploración de la serie temporal",
        "",
        "Análisis generado por `scripts/analyze_forecast_series.py` sobre la tabla Gold.",
        "",
        "## Cobertura utilizada",
        "",
        f"- Serie completa: steps {coverage['min_step']}–{coverage['max_step']} "
        f"({coverage['steps']} observaciones).",
        f"- Periodo operativo para explorar patrones: {coverage['operational_steps']} steps.",
        f"- Inicio del tramo final solo fraude: step {coverage['final_fraud_only_start']}.",
        f"- Longitud del tramo final: {coverage['tail_steps']} steps.",
        "",
        "## Estadísticas del periodo operativo",
        "",
        "| Serie | Promedio | Mediana | Desv. estándar | Mínimo | Máximo |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        (
            "| Cantidad de transacciones | "
            f"{operational['transaction_count']['mean']:,.2f} | "
            f"{operational['transaction_count']['median']:,.2f} | "
            f"{operational['transaction_count']['std']:,.2f} | "
            f"{operational['transaction_count']['min']:,.0f} | "
            f"{operational['transaction_count']['max']:,.0f} |"
        ),
        (
            "| Monto total | "
            f"{operational['total_amount']['mean']:,.2f} | "
            f"{operational['total_amount']['median']:,.2f} | "
            f"{operational['total_amount']['std']:,.2f} | "
            f"{operational['total_amount']['min']:,.2f} | "
            f"{operational['total_amount']['max']:,.2f} |"
        ),
        "",
        "## Autocorrelación del periodo operativo",
        "",
        "| Rezago | Cantidad | Monto total | Interpretación inicial |",
        "| ---: | ---: | ---: | --- |",
    ]
    for lag, values in autocorrelation.items():
        label = {
            "1": "Relación con la hora anterior",
            "24": "Posible repetición diaria",
            "168": "Posible repetición semanal",
        }.get(lag, "Relación temporal")
        lines.append(
            f"| {lag} | {_format_correlation(values['transaction_count'])} | "
            f"{_format_correlation(values['total_amount'])} | {label} |"
        )

    lines += [
        "",
        "## Gráficos generados",
        "",
        f"- Cantidad por step: `{plots['transaction_count']}`.",
        f"- Monto por step: `{plots['total_amount']}`.",
        f"- Ciclo de 24 horas: `{plots['hourly_cycle']}`.",
        "",
        "## Lectura inicial",
        "",
        "- La media móvil de 24 steps permite separar el nivel general de las "
        "variaciones horarias.",
        "- La autocorrelación en el rezago 24 indicará si una línea base "
        "estacional diaria tiene sentido.",
        "- El tramo final solo fraude se conserva en Gold, pero no se mezcla "
        "automáticamente con el periodo operativo para decidir el modelo.",
    ]
    if tail["transaction_count"] is not None:
        lines += [
            "- En el tramo final, la cantidad promedio baja a "
            f"{tail['transaction_count']['mean']:,.2f} transacciones por step, "
            "por lo que debe tratarse como un cambio de comportamiento del simulador.",
        ]
    lines += [
        "",
        "## Decisiones pendientes",
        "",
        "1. Confirmar el periodo de evaluación principal y el horizonte inicial.",
        "2. Comparar Naive con Naive estacional de 24 steps.",
        "3. Mantener el tramo final como caso separado para monitoreo.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def analyze_temporal_series(
    input_path: Path,
    analysis_json: Path,
    analysis_markdown: Path,
    plots_dir: Path,
    seasonal_period: int = 24,
    base_dir: Path | None = None,
) -> dict:
    """Genera estadísticas, gráficos y reporte para la serie Gold."""
    input_path = Path(input_path)
    if not input_path.exists():
        raise ValueError(f"No existe la tabla Gold temporal: {input_path}")

    gold = pd.read_parquet(input_path)
    series = prepare_temporal_series(gold, seasonal_period=seasonal_period)
    report = summarize_temporal_series(series, seasonal_period=seasonal_period)

    plots_dir = Path(plots_dir)
    plots_dir.mkdir(parents=True, exist_ok=True)
    tail_start = report["coverage"]["final_fraud_only_start"]
    operational = (
        series
        if tail_start is None
        else series[series["step"] < tail_start].copy()
    )
    plot_paths = {
        "transaction_count": plots_dir / "transaction-count-by-step.png",
        "total_amount": plots_dir / "total-amount-by-step.png",
        "hourly_cycle": plots_dir / "simulated-hour-cycle.png",
    }
    _plot_time_series(
        series,
        "transaction_count",
        "transaction_count_ma24",
        "Cantidad de transacciones por hora simulada",
        "Cantidad de transacciones",
        plot_paths["transaction_count"],
        tail_start,
    )
    _plot_time_series(
        series,
        "total_amount",
        "total_amount_ma24",
        "Monto total por hora simulada",
        "Monto total (unidad no identificada)",
        plot_paths["total_amount"],
        tail_start,
    )
    _plot_hourly_cycle(operational, plot_paths["hourly_cycle"])

    def display(path: Path) -> str:
        if base_dir is None:
            return str(path)
        try:
            return str(path.resolve().relative_to(Path(base_dir).resolve()))
        except ValueError:
            return str(path)

    displayed_plots = {name: display(path) for name, path in plot_paths.items()}
    report["source"] = display(input_path)
    report["plots"] = displayed_plots

    analysis_json = Path(analysis_json)
    analysis_json.parent.mkdir(parents=True, exist_ok=True)
    analysis_json.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    _write_markdown(report, displayed_plots, Path(analysis_markdown))
    return report
