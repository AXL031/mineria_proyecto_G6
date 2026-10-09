"""Contrato HTTP de fraude previo a la operación, con carga diferida del modelo."""

from functools import lru_cache
import logging
import os
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from bankshield.services.fraud import FraudScorer

router = APIRouter(prefix="/fraud", tags=["Fraude"])
logger = logging.getLogger(__name__)
DEFAULT_MODEL = Path(__file__).resolve().parents[2] / "artifacts/models/fraud/model.joblib"


class FraudRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    type: Literal["PAYMENT", "TRANSFER", "CASH_OUT", "DEBIT", "CASH_IN"]
    amount: float = Field(ge=0, strict=True)
    oldbalanceOrg: float = Field(ge=0, strict=True)


class FraudResponse(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    score: float = Field(ge=0, le=1)
    alert: bool
    threshold: float = Field(ge=0)
    score_is_calibrated: bool = False
    simulation_data: bool = True
    model_id: str


@lru_cache(maxsize=1)
def _load_scorer(path: str, modified: int, size: int) -> FraudScorer:
    return FraudScorer(Path(path))


def get_scorer() -> FraudScorer:
    path = Path(os.environ.get("BANKSHIELD_FRAUD_MODEL", str(DEFAULT_MODEL)))
    try:
        stat = path.stat()
        return _load_scorer(str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    except Exception as exc:
        logger.exception("No se pudo cargar el modelo de fraude")
        raise HTTPException(503, "Modelo de fraude no disponible; revisar artefacto y versiones en el servidor.") from exc


@router.post("/predict", response_model=FraudResponse)
def predict(transaction: FraudRequest, scorer: FraudScorer = Depends(get_scorer)):
    result = scorer.score([transaction.model_dump()])[0]
    return {**result, "simulation_data": True, "model_id": scorer.model_id}


@router.get("/model")
def model_evaluation(scorer: FraudScorer = Depends(get_scorer)):
    return scorer.evaluation()
