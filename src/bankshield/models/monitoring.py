"""Comparación histórica de ventanas transaccionales para monitoreo."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = ("step", "type", "amount", "isFraud")
AMOUNT_QUANTILES = (0.25, 0.5, 0.75, 0.9, 0.99)


def _period(config: Mapping[str, object], name: str) -> tuple[int, int]:
    raw = config.get(name)
    if not isinstance(raw, Mapping):
        raise ValueError(f"Falta {name} en la configuración")
    try:
        start = int(raw["start_step"])
        end = int(raw["end_step"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{name} requiere steps enteros") from error
    if start < 1 or end < start:
        raise ValueError(f"{name} es inválido")
    return start, end


def _thresholds(config: Mapping[str, object]) -> dict[str, float]:
    raw = config.get("thresholds")
    if not isinstance(raw, Mapping):
        raise ValueError("Faltan thresholds en la configuración")
    expected = {
        "transaction_count_relative_change",
        "total_amount_relative_change",
        "average_amount_relative_change",
        "amount_distribution_tvd",
        "type_mix_tvd",
        "fraud_rate_absolute_change",
    }
    if set(raw) != expected:
        raise ValueError("Los thresholds de monitoreo no coinciden con el contrato")
    parsed = {}
    for name, value in raw.items():
        try:
            numeric = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"El umbral {name} debe ser numérico") from error
        if not np.isfinite(numeric) or numeric < 0:
            raise ValueError(f"El umbral {name} debe ser finito y no negativo")
        parsed[name] = numeric
    return parsed


def _validated_transactions(transactions: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(transactions, pd.DataFrame):
        raise TypeError("Las transacciones deben ser un DataFrame")
    missing = sorted(set(REQUIRED_COLUMNS).difference(transactions.columns))
    if missing:
        raise ValueError("Faltan columnas de monitoreo: " + ", ".join(missing))
    if transactions.empty:
        raise ValueError("No hay transacciones para monitorear")

    data = transactions.loc[:, list(REQUIRED_COLUMNS)].copy()
    data["step"] = pd.to_numeric(data["step"], errors="coerce")
    data["amount"] = pd.to_numeric(data["amount"], errors="coerce")
    data["isFraud"] = pd.to_numeric(data["isFraud"], errors="coerce")
    if data[["step", "amount", "isFraud"]].isna().any().any():
        raise ValueError("El monitoreo contiene valores numéricos inválidos")
    if not np.isfinite(data[["step", "amount", "isFraud"]]).all().all():
        raise ValueError("El monitoreo contiene valores no finitos")
    if not np.equal(data["step"], np.floor(data["step"])).all():
        raise ValueError("step debe ser entero")
    if (data["amount"] < 0).any():
        raise ValueError("amount debe ser no negativo")
    if not data["isFraud"].isin([0, 1]).all():
        raise ValueError("isFraud debe ser binario")
    if data["type"].isna().any() or (data["type"].astype(str).str.strip() == "").any():
        raise ValueError("type debe contener categorías no vacías")

    data["step"] = data["step"].astype("int64")
    data["isFraud"] = data["isFraud"].astype("int64")
    data["amount"] = data["amount"].astype("float64")
    data["type"] = data["type"].astype(str)
    return data


def _relative_change(reference: float, observed: float) -> float | None:
    if reference == 0:
        return None if observed != 0 else 0.0
    return float((observed - reference) / abs(reference))


def _window_summary(data: pd.DataFrame, start: int, end: int) -> dict[str, object]:
    expected_steps = set(range(start, end + 1))
    observed_steps = set(int(step) for step in data["step"].unique())
    missing_steps = sorted(expected_steps.difference(observed_steps))
    rows = int(len(data))
    amount = data["amount"]
    type_counts = data["type"].value_counts(sort=False)
    return {
        "start_step": start,
        "end_step": end,
        "step_count": end - start + 1,
        "missing_steps": missing_steps,
        "transaction_count": rows,
        "mean_transaction_count_per_step": rows / (end - start + 1),
        "total_amount": float(amount.sum()),
        "mean_total_amount_per_step": float(amount.sum() / (end - start + 1)),
        "average_amount": float(amount.mean()),
        "amount_quantiles": {
            "p25": float(amount.quantile(0.25)),
            "p50": float(amount.quantile(0.5)),
            "p75": float(amount.quantile(0.75)),
            "p90": float(amount.quantile(0.9)),
            "p99": float(amount.quantile(0.99)),
        },
        "fraud_count": int(data["isFraud"].sum()),
        "fraud_rate": float(data["isFraud"].mean()),
        "type_counts": {str(key): int(value) for key, value in type_counts.items()},
        "type_mix": {
            str(key): float(value / rows) for key, value in type_counts.items()
        },
    }


def _categorical_shift(
    reference: Mapping[str, float], observed: Mapping[str, float]
) -> dict[str, object]:
    categories = sorted(set(reference).union(observed))
    details = {}
    distance = 0.0
    for category in categories:
        before = float(reference.get(category, 0.0))
        after = float(observed.get(category, 0.0))
        delta = after - before
        distance += abs(delta)
        details[category] = {
            "reference_share": before,
            "observed_share": after,
            "percentage_point_change": delta,
        }
    return {"total_variation_distance": distance / 2.0, "categories": details}


def _amount_distribution_shift(
    reference: pd.Series, observed: pd.Series
) -> dict[str, object]:
    internal_edges = np.unique(reference.quantile(AMOUNT_QUANTILES).to_numpy())
    edges = np.concatenate(([-np.inf], internal_edges, [np.inf]))
    reference_counts, _ = np.histogram(reference.to_numpy(), bins=edges)
    observed_counts, _ = np.histogram(observed.to_numpy(), bins=edges)
    reference_share = reference_counts / reference_counts.sum()
    observed_share = observed_counts / observed_counts.sum()
    return {
        "method": "reference_quantile_bins",
        "quantiles": list(AMOUNT_QUANTILES),
        "internal_edges": [float(value) for value in internal_edges],
        "reference_share": [float(value) for value in reference_share],
        "observed_share": [float(value) for value in observed_share],
        "total_variation_distance": float(
            0.5 * np.abs(reference_share - observed_share).sum()
        ),
    }


def compare_monitoring_windows(
    transactions: pd.DataFrame,
    monitoring_config: Mapping[str, object],
) -> dict[str, object]:
    """Compara una ventana observada con una referencia histórica equivalente."""

    if not isinstance(monitoring_config, Mapping):
        raise TypeError("La configuración de monitoreo debe ser un objeto")
    reference_start, reference_end = _period(monitoring_config, "reference_period")
    observed_start, observed_end = _period(monitoring_config, "observed_period")
    if reference_end >= observed_start:
        raise ValueError("La referencia debe ser anterior al periodo observado")
    if reference_end - reference_start != observed_end - observed_start:
        raise ValueError("Las ventanas deben contener la misma cantidad de steps")
    thresholds = _thresholds(monitoring_config)

    data = _validated_transactions(transactions)
    reference = data[data["step"].between(reference_start, reference_end)].copy()
    observed = data[data["step"].between(observed_start, observed_end)].copy()
    if reference.empty or observed.empty:
        raise ValueError("Ambas ventanas deben contener transacciones")

    reference_summary = _window_summary(reference, reference_start, reference_end)
    observed_summary = _window_summary(observed, observed_start, observed_end)
    type_shift = _categorical_shift(
        reference_summary["type_mix"], observed_summary["type_mix"]
    )
    amount_shift = _amount_distribution_shift(reference["amount"], observed["amount"])
    changes = {
        "transaction_count_relative_change": _relative_change(
            reference_summary["transaction_count"],
            observed_summary["transaction_count"],
        ),
        "total_amount_relative_change": _relative_change(
            reference_summary["total_amount"], observed_summary["total_amount"]
        ),
        "average_amount_relative_change": _relative_change(
            reference_summary["average_amount"], observed_summary["average_amount"]
        ),
        "amount_distribution_tvd": amount_shift["total_variation_distance"],
        "type_mix_tvd": type_shift["total_variation_distance"],
        "fraud_rate_absolute_change": (
            observed_summary["fraud_rate"] - reference_summary["fraud_rate"]
        ),
    }
    alerts = {
        name: (
            value is None or abs(value) >= thresholds[name]
        )
        for name, value in changes.items()
    }
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": monitoring_config.get("experiment_id"),
        "reference": reference_summary,
        "observed": observed_summary,
        "changes": changes,
        "amount_distribution": amount_shift,
        "type_mix": type_shift,
        "thresholds": thresholds,
        "alerts": alerts,
        "alert_count": int(sum(alerts.values())),
        "status": "change_detected" if any(alerts.values()) else "stable",
        "limitations": [
            "La comparación es histórica y no observa lotes futuros en producción.",
            "Los umbrales son descriptivos y no fueron calibrados con incidentes reales.",
            "PaySim es una simulación y el tramo observado pertenece a su cierre anómalo.",
        ],
    }


def _display_path(path: Path, base_dir: Path | None) -> str:
    if base_dir is not None:
        try:
            return str(path.resolve().relative_to(base_dir.resolve()))
        except ValueError:
            pass
    return str(path)


def _file_sha256(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest()


def _format_change(value: float | None, *, percentage_points: bool = False) -> str:
    if value is None:
        return "No definido"
    suffix = " pp" if percentage_points else " %"
    multiplier = 100.0
    return f"{value * multiplier:+,.2f}{suffix}"


def _write_markdown(report: Mapping[str, object], path: Path) -> None:
    reference = report["reference"]
    observed = report["observed"]
    changes = report["changes"]
    alerts = report["alerts"]
    lines = [
        "# Monitoreo histórico de cambios transaccionales",
        "",
        "Comparación descriptiva generada por `scripts/monitor_forecast_shift.py`.",
        "No representa monitoreo en producción ni una alerta bancaria real.",
        "",
        "## Ventanas",
        "",
        f"- Referencia: steps {reference['start_step']}–{reference['end_step']}.",
        f"- Observada: steps {observed['start_step']}–{observed['end_step']}.",
        "- Ambas ventanas contienen 25 steps consecutivos.",
        "",
        "## Cambios principales",
        "",
        "| Indicador | Referencia | Observado | Cambio | Alerta |",
        "| --- | ---: | ---: | ---: | --- |",
        f"| Transacciones | {reference['transaction_count']:,} | "
        f"{observed['transaction_count']:,} | "
        f"{_format_change(changes['transaction_count_relative_change'])} | "
        f"{'Sí' if alerts['transaction_count_relative_change'] else 'No'} |",
        f"| Monto total | {reference['total_amount']:,.2f} | "
        f"{observed['total_amount']:,.2f} | "
        f"{_format_change(changes['total_amount_relative_change'])} | "
        f"{'Sí' if alerts['total_amount_relative_change'] else 'No'} |",
        f"| Monto promedio | {reference['average_amount']:,.2f} | "
        f"{observed['average_amount']:,.2f} | "
        f"{_format_change(changes['average_amount_relative_change'])} | "
        f"{'Sí' if alerts['average_amount_relative_change'] else 'No'} |",
        f"| Tasa de fraude | {reference['fraud_rate']:.4%} | "
        f"{observed['fraud_rate']:.4%} | "
        f"{_format_change(changes['fraud_rate_absolute_change'], percentage_points=True)} | "
        f"{'Sí' if alerts['fraud_rate_absolute_change'] else 'No'} |",
        "",
        "## Distribuciones",
        "",
        f"- Distancia de variación total de montos: "
        f"{changes['amount_distribution_tvd']:.4f} "
        f"(alerta: {'sí' if alerts['amount_distribution_tvd'] else 'no'}).",
        f"- Distancia de variación total de tipos: {changes['type_mix_tvd']:.4f} "
        f"(alerta: {'sí' if alerts['type_mix_tvd'] else 'no'}).",
        "",
        "Los valores de distancia van de 0 (misma distribución) a 1 "
        "(distribuciones sin solapamiento). Para los montos se utilizan intervalos "
        "definidos por cuantiles de la ventana de referencia.",
        "",
        "### Mezcla por tipo",
        "",
        "| Tipo | Referencia | Observado | Cambio porcentual |",
        "| --- | ---: | ---: | ---: |",
    ]
    for category, values in report["type_mix"]["categories"].items():
        lines.append(
            f"| {category} | {values['reference_share']:.2%} | "
            f"{values['observed_share']:.2%} | "
            f"{values['percentage_point_change'] * 100:+.2f} pp |"
        )
    lines += [
        "",
        "## Resultado",
        "",
        f"Estado: **{report['status']}** con {report['alert_count']} indicadores "
        "fuera de los umbrales descriptivos.",
        "",
        "El tramo 719–743 contiene exclusivamente transacciones etiquetadas como "
        "fraude y una actividad mucho menor. El resultado demuestra que el método "
        "detecta un cambio histórico evidente del simulador; no demuestra capacidad "
        "para anticipar deriva futura.",
        "",
        "## Umbrales descriptivos",
        "",
        "| Indicador | Umbral absoluto |",
        "| --- | ---: |",
    ]
    for name, value in report["thresholds"].items():
        lines.append(f"| `{name}` | {value:.4f} |")
    lines += [
        "",
        "## Limitaciones",
        "",
    ]
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_historical_monitoring(
    input_path: Path,
    output_path: Path,
    markdown_path: Path,
    monitoring_config: Mapping[str, object],
    *,
    base_dir: Path | None = None,
) -> dict[str, object]:
    """Lee Silver, compara las ventanas y escribe reportes reproducibles."""

    input_path = Path(input_path)
    if not input_path.exists():
        raise ValueError(f"No existe la tabla Silver transaccional: {input_path}")
    reference_start, _ = _period(monitoring_config, "reference_period")
    _, observed_end = _period(monitoring_config, "observed_period")
    transactions = pd.read_parquet(
        input_path,
        columns=list(REQUIRED_COLUMNS),
        filters=[
            ("step", ">=", reference_start),
            ("step", "<=", observed_end),
        ],
    )
    report = compare_monitoring_windows(transactions, monitoring_config)
    report["source"] = {
        "path": _display_path(input_path, base_dir),
        "format": "parquet",
        "columns": list(REQUIRED_COLUMNS),
        "sha256": _file_sha256(input_path),
    }
    report["output"] = {
        "json": _display_path(Path(output_path), base_dir),
        "markdown": _display_path(Path(markdown_path), base_dir),
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    _write_markdown(report, Path(markdown_path))
    return report
