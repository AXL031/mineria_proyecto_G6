"""Contrato HTTP de estimación del monto; solo consulta el artefacto offline."""

from functools import lru_cache
import logging
import os
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from bankshield.services.regression import RegressionScorer

router = APIRouter(prefix="/regression", tags=["Regresión numérica"])
logger = logging.getLogger(__name__)
DEFAULT_MODEL = Path(__file__).resolve().parents[2] / "artifacts/models/regression/model.joblib"


class RegressionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    type: Literal["PAYMENT", "TRANSFER", "CASH_OUT", "DEBIT", "CASH_IN"]
    oldbalanceOrg: float = Field(ge=0, strict=True)


@lru_cache(maxsize=2)
def _load(path, signatures):
    return RegressionScorer(path)


def get_scorer():
    path = Path(os.environ.get("BANKSHIELD_REGRESSION_MODEL", str(DEFAULT_MODEL)))
    try:
        # Invalidar también cuando se reemplaza solo el JSON de métricas.
        signatures = tuple((p.stat().st_mtime_ns, p.stat().st_size) for p in (path, path.with_name("metrics.json")))
        return _load(str(path.resolve()), signatures)
    except Exception as exc:
        logger.warning("Regresión no disponible: %s", type(exc).__name__)
        raise HTTPException(503, "Modelo de regresión ausente o incompatible; regenerar modelo y métricas.") from exc


@router.post("/predict")
def predict(request: RegressionRequest, scorer=Depends(get_scorer)):
    try:
        return scorer.score([request.model_dump()])[0]
    except (ValueError, OverflowError) as exc:
        raise HTTPException(503, "El modelo no puede producir una estimación finita para esta entrada.") from exc


@router.get("/model")
def model(scorer=Depends(get_scorer)):
    return scorer.evaluation()


@router.get("/examples")
def examples(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), scorer=Depends(get_scorer)):
    try:
        return scorer.examples(limit, offset)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(503, "Ejemplos ausentes o incompatibles con el modelo de regresión.") from exc
