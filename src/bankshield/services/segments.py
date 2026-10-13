"""Consulta de segmentos de cuentas de destino reincidentes.

Lee los artefactos locales generados por ``scripts/segment_transactions.py``: la
tabla de cuentas etiquetadas y el reporte con métricas y perfiles. Si un
artefacto no existe o no cumple el esquema, lanza ``SegmentsArtifactError`` para
que la API responda 503 con un mensaje claro y la página muestre el estado.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SEGMENTS_PARQUET = ROOT / "data" / "gold" / "segments" / "account_segments.parquet"
DEFAULT_REPORT_JSON = ROOT / "artifacts" / "reports" / "segments.json"
ACCOUNT_COLUMN = "account"


class SegmentsArtifactError(FileNotFoundError):
    """Artefacto local de segmentos ausente o con esquema inválido."""


def _require(path: Path, kind: str) -> Path:
    if not path.exists():
        raise SegmentsArtifactError(
            f"No existe el artefacto de segmentos ({kind}): {path}. "
            "Genere 'data/gold/segments/account_segments.parquet' y "
            "'artifacts/reports/segments.json' con scripts/segment_transactions.py."
        )
    return path


def load_segments(parquet_path: Optional[Path] = None) -> pd.DataFrame:
    """Carga la tabla de cuentas etiquetadas por segmento."""
    path = _require(Path(parquet_path or DEFAULT_SEGMENTS_PARQUET), "tabla de cuentas")
    frame = pd.read_parquet(path)
    if ACCOUNT_COLUMN not in frame.columns or "segment" not in frame.columns:
        raise SegmentsArtifactError(
            "El Parquet de segmentos no contiene las columnas 'account' y 'segment'."
        )
    return frame


def load_report(report_path: Optional[Path] = None) -> Dict[str, Any]:
    """Carga el reporte JSON con métricas, perfiles y línea base."""
    path = _require(Path(report_path or DEFAULT_REPORT_JSON), "reporte de métricas")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_summary(report_path: Optional[Path] = None) -> Dict[str, Any]:
    """Resumen del reporte: métricas de calidad, recuentos y perfiles."""
    report = load_report(report_path)
    return {
        "schema_version": report.get("schema_version"),
        "source": report.get("source"),
        "min_transactions": report.get("min_transactions"),
        "total_accounts": report.get("total_accounts"),
        "metrics": report.get("metrics"),
        "profiles": report.get("profiles"),
        "baseline_profiles": report.get("baseline_profiles"),
    }


def get_accounts_by_segment(
    segment_id: int,
    limit: Optional[int] = None,
    offset: int = 0,
    parquet_path: Optional[Path] = None,
) -> pd.DataFrame:
    """Cuentas de un segmento, con paginación opcional."""
    frame = load_segments(parquet_path)
    if segment_id not in set(frame["segment"].unique()):
        raise KeyError(f"No existe el segmento {segment_id}")
    subset = frame.loc[frame["segment"] == segment_id].iloc[offset:]
    if limit is not None:
        subset = subset.head(limit)
    return subset.reset_index(drop=True)


def get_account(
    segment_id: int, account_id: str | int, parquet_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Fila de comportamiento de una cuenta dentro de un segmento."""
    frame = load_segments(parquet_path)
    mask = (frame["segment"] == segment_id) & (
        frame[ACCOUNT_COLUMN].astype(str) == str(account_id)
    )
    row = frame.loc[mask]
    if row.empty:
        raise KeyError(
            f"No se encontró la cuenta {account_id} en el segmento {segment_id}"
        )
    return row.iloc[0].to_dict()


def json_safe(record: Dict[str, Any]) -> Dict[str, Any]:
    """Convierte NaN de pandas a None para que la respuesta sea JSON válido."""
    return {
        key: None if isinstance(value, float) and math.isnan(value) else value
        for key, value in record.items()
    }
