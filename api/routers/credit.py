"""Contrato HTTP de riesgo crediticio con carga diferida del modelo."""

from functools import lru_cache
import logging
import os
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from bankshield.services.credit import CreditScorer

router = APIRouter(prefix="/credit", tags=["Crédito"])
logger = logging.getLogger(__name__)
DEFAULT_MODEL = Path(__file__).resolve().parents[2] / "artifacts/models/credit/model.joblib"


class CreditRequest(BaseModel):
    """Solo variables de la solicitud; grado y tasa los fija el prestamista y no se aceptan."""
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    person_age: int = Field(ge=18, le=100, strict=True)
    person_income: float = Field(gt=0, strict=True)
    person_home_ownership: Literal["RENT", "MORTGAGE", "OWN", "OTHER"]
    person_emp_length: Optional[float] = Field(default=None, ge=0, le=60, strict=True)
    loan_intent: Literal["PERSONAL", "EDUCATION", "MEDICAL", "VENTURE", "HOMEIMPROVEMENT",
                         "DEBTCONSOLIDATION"]
    loan_amnt: float = Field(gt=0, strict=True)
    cb_person_default_on_file: Literal["Y", "N"]
    cb_person_cred_hist_length: int = Field(ge=0, le=60, strict=True)

    @model_validator(mode="after")
    def _plausible(self):
        working = self.person_age - 14
        if self.person_emp_length is not None and self.person_emp_length > working:
            raise ValueError("person_emp_length excede la edad laboral posible")
        if self.cb_person_cred_hist_length > working + 1:
            raise ValueError("cb_person_cred_hist_length excede la edad posible")
        return self


class Factor(BaseModel):
    feature: str
    value: Optional[float | str] = None
    reference: float | str
    effect: float


class CreditResponse(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    default_probability: float = Field(ge=0, le=1)
    high_risk: bool
    threshold: float = Field(ge=0, le=1)
    factors: list[Factor]
    explanation_method: str
    explanation_is_causal: bool = False
    label_semantics_confirmed: bool = False
    credit_limit_recommended: None = None
    model_id: str


@lru_cache(maxsize=1)
def _load_scorer(path: str, modified: int, size: int) -> CreditScorer:
    return CreditScorer(Path(path))


def get_scorer() -> CreditScorer:
    path = Path(os.environ.get("BANKSHIELD_CREDIT_MODEL", str(DEFAULT_MODEL)))
    try:
        stat = path.stat()
        return _load_scorer(str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    except Exception as exc:
        logger.exception("No se pudo cargar el modelo de crédito")
        raise HTTPException(503, "Modelo de crédito no disponible; revisar artefacto y versiones en el servidor.") from exc


@router.post("/predict", response_model=CreditResponse)
def predict(application: CreditRequest, scorer: CreditScorer = Depends(get_scorer)):
    record = application.model_dump()
    result = scorer.score([record])[0]
    explanation = scorer.explain(record)
    return {**result, "factors": explanation["factors"], "explanation_method": explanation["method"],
            "explanation_is_causal": False, "label_semantics_confirmed": False, "model_id": scorer.model_id}


@router.get("/model")
def model_evaluation(scorer: CreditScorer = Depends(get_scorer)):
    return scorer.evaluation()
