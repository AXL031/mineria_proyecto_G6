"""Contrato HTTP del módulo de segmentación de cuentas de destino.

Expone el resumen del reporte (métricas, perfiles y línea base) y la consulta de
cuentas por segmento. Los artefactos se generan con
``scripts/segment_transactions.py``; si faltan, la API responde 503 con un
mensaje que indica cómo reconstruirlos.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query

from bankshield.services import segments as segments_service

router = APIRouter(prefix="/segments", tags=["Segmentos"])


def _paths() -> tuple[Path, Path]:
    parquet = Path(
        os.environ.get(
            "BANKSHIELD_SEGMENTS_PARQUET", str(segments_service.DEFAULT_SEGMENTS_PARQUET)
        )
    )
    report = Path(
        os.environ.get(
            "BANKSHIELD_SEGMENTS_REPORT", str(segments_service.DEFAULT_REPORT_JSON)
        )
    )
    return parquet, report


@router.get("/summary")
def summary() -> Dict[str, Any]:
    """Métricas de segmentación, perfiles por segmento y línea base."""
    _, report = _paths()
    try:
        return segments_service.get_summary(report)
    except segments_service.SegmentsArtifactError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{segment_id}/accounts")
def accounts(
    segment_id: int,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """Cuentas de un segmento con paginación; 404 si el segmento no existe."""
    parquet, _ = _paths()
    try:
        frame = segments_service.get_accounts_by_segment(
            segment_id, limit=limit, offset=offset, parquet_path=parquet
        )
    except segments_service.SegmentsArtifactError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    records = [segments_service.json_safe(row) for row in frame.to_dict(orient="records")]
    return {"segment": segment_id, "count": len(records), "accounts": records}


@router.get("/{segment_id}/account/{account_id}")
def account(segment_id: int, account_id: str) -> Dict[str, Any]:
    """Comportamiento de una cuenta dentro de un segmento; 404 si no existe."""
    parquet, _ = _paths()
    try:
        record = segments_service.get_account(
            segment_id, account_id, parquet_path=parquet
        )
    except segments_service.SegmentsArtifactError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return segments_service.json_safe(record)
