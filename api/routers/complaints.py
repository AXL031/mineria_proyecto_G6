"""Producto sugerido por narrativa, evaluación y tendencias de reclamos CFPB."""

from functools import lru_cache
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from bankshield.services.complaints import ComplaintsScorer, complaints_examples, complaints_summary

ROOT = Path(__file__).resolve().parents[2]
router = APIRouter(prefix="/complaints", tags=["Reclamos"])
logger = logging.getLogger(__name__)


class NarrativeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    narrative: str = Field(min_length=10, max_length=20000, strict=True)


@lru_cache(maxsize=1)
def _load_scorer(path: str, modified: int, size: int) -> ComplaintsScorer:
    return ComplaintsScorer(Path(path))


def get_scorer() -> ComplaintsScorer:
    path = Path(os.environ.get("BANKSHIELD_COMPLAINTS_MODEL", str(ROOT / "artifacts/models/complaints/model.joblib")))
    try:
        stat = path.stat()
        return _load_scorer(str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    except Exception as exc:
        logger.warning("No se pudo cargar el modelo de reclamos: %s", type(exc).__name__)
        raise HTTPException(503, "Modelo de reclamos no disponible; reconstruir con train_complaints.py.") from exc


@router.post("/predict")
def predict(request: NarrativeRequest, scorer: ComplaintsScorer = Depends(get_scorer)):
    try:
        return scorer.predict(request.narrative)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/model")
def evaluation(scorer: ComplaintsScorer = Depends(get_scorer)):
    return scorer.evaluation()


@lru_cache(maxsize=1)
def _load_summary(path: str, modified: int, size: int) -> dict:
    return complaints_summary(Path(path))


@router.get("/summary")
def summary():
    path = Path(os.environ.get("BANKSHIELD_COMPLAINTS_SILVER", str(ROOT / "data/silver/complaints/complaints.parquet")))
    try:
        stat = path.stat()
        return _load_summary(str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    except Exception as exc:
        raise HTTPException(503, "Silver de reclamos no disponible; ejecutar build_silver_complaints.py.") from exc


@router.get("/examples")
def examples(scorer: ComplaintsScorer = Depends(get_scorer)):
    path = Path(os.environ.get("BANKSHIELD_COMPLAINTS_EXAMPLES", str(ROOT / "artifacts/reports/complaints/error_examples.json")))
    try:
        return complaints_examples(path, scorer)
    except Exception as exc:
        raise HTTPException(503, "Ejemplos no disponibles; ejecutar analyze_complaints_errors.py.") from exc
