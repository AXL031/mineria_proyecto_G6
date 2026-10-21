"""Endpoints de proyección y monitoreo temporal."""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from bankshield.services.forecast import (
    build_forecast_projection,
    monitoring_summary,
)


router = APIRouter(prefix="/forecast", tags=["Pronósticos"])
logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOLD = ROOT / "data/gold/forecast/transactions_hourly.parquet"
DEFAULT_MONITORING = ROOT / "artifacts/reports/forecast_monitoring.json"


@lru_cache(maxsize=1)
def _load_series(path: str, modified: int, size: int) -> pd.DataFrame:
    return pd.read_parquet(path)


def get_series() -> pd.DataFrame:
    path = Path(os.environ.get("BANKSHIELD_FORECAST_GOLD", str(DEFAULT_GOLD)))
    try:
        stat = path.stat()
        return _load_series(str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    except Exception as exc:
        logger.exception("No se pudo cargar la serie Gold temporal")
        raise HTTPException(
            503,
            "Serie Gold temporal no disponible; ejecutar build_forecast_gold.py.",
        ) from exc


@lru_cache(maxsize=1)
def _load_monitoring(path: str, modified: int, size: int) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def get_monitoring_report() -> dict[str, object]:
    path = Path(
        os.environ.get("BANKSHIELD_FORECAST_MONITORING", str(DEFAULT_MONITORING))
    )
    try:
        stat = path.stat()
        return _load_monitoring(str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    except Exception as exc:
        logger.exception("No se pudo cargar el reporte de monitoreo temporal")
        raise HTTPException(
            503,
            "Monitoreo temporal no disponible; ejecutar monitor_forecast_shift.py.",
        ) from exc


@router.get("/projection")
def projection(
    target: Literal["transaction_count", "total_amount"] = "transaction_count",
    horizon: int = Query(default=24, ge=1, le=168),
    history_steps: int = Query(default=168, ge=24, le=718),
    series: pd.DataFrame = Depends(get_series),
):
    try:
        return build_forecast_projection(
            series,
            target=target,
            horizon=horizon,
            history_steps=history_steps,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(500, "La serie Gold no cumple el contrato temporal.") from exc


@router.get("/monitoring")
def monitoring(report: dict[str, object] = Depends(get_monitoring_report)):
    try:
        return monitoring_summary(report)
    except ValueError as exc:
        raise HTTPException(503, "El reporte de monitoreo no es compatible.") from exc
