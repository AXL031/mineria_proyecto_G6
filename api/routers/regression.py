"""Contrato HTTP de estimación del monto transaccional con carga diferida del modelo."""

from functools import lru_cache
import logging
import os
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from bankshield.services.regression import RegressionEstimator

router = APIRouter(prefix="/regression", tags=["Regresión"])
logger = logging.getLogger(__name__)
DEFAULT_MODEL = Path(__file__).resolve().parents[2] / "artifacts/models/regression/model.joblib"
LIMITATION = "Estimación académica; no constituye una alerta de fraude."


class RegressionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    type: Literal["PAYMENT", "TRANSFER", "CASH_OUT", "DEBIT", "CASH_IN"]
    oldbalanceOrg: float = Field(ge=0, strict=True)


class RegressionResponse(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    model_id: str
    target: str
    prediction: float = Field(ge=0)
    selected_model: str
    simulation_data: bool
    limitations: list[str]


@lru_cache(maxsize=1)
def _load(path: str, modified: int, size: int) -> RegressionEstimator:
    return RegressionEstimator(Path(path))


def get_estimator() -> RegressionEstimator:
    path = Path(os.environ.get("BANKSHIELD_REGRESSION_MODEL", str(DEFAULT_MODEL)))
    try:
        stat = path.stat()
        return _load(str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    except Exception as exc:
        logger.exception("No se pudo cargar el modelo de regresión")
        raise HTTPException(503, "Modelo de regresión no disponible; revisar artefactos y versiones.") from exc


@router.post("/predict", response_model=RegressionResponse)
def predict(request: RegressionRequest, estimator: RegressionEstimator = Depends(get_estimator)):
    return {"model_id": estimator.model_id, "target": "amount",
            "prediction": estimator.predict(request.type, request.oldbalanceOrg),
            "selected_model": estimator.selected_model, "simulation_data": True, "limitations": [LIMITATION]}


@router.get("/model")
def model_evaluation(estimator: RegressionEstimator = Depends(get_estimator)):
    return estimator.evaluation()


@router.get("/examples")
def examples(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
             estimator: RegressionEstimator = Depends(get_estimator)):
    return estimator.examples_page(limit, offset)
