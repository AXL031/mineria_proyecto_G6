"""Scoring reutilizable para la futura API y página de fraude."""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from bankshield.features.fraud import MODEL_FEATURES, build_fraud_feature_frame


class FraudScorer:
    def __init__(self, model_path: Path):
        bundle = joblib.load(model_path)
        if not isinstance(bundle, dict) or bundle.get("artifact_version") != 1:
            raise ValueError("Versión de artefacto de fraude no soportada")
        if bundle.get("feature_columns") != list(MODEL_FEATURES):
            raise ValueError("El modelo usa un contrato de variables distinto")
        self.pipeline = bundle["pipeline"]
        self.threshold = float(bundle["threshold"])
        if not np.isfinite(self.threshold) or self.threshold < 0:
            raise ValueError("Umbral inválido en el artefacto")
        self.metadata = bundle["metadata"]

    def score(self, records: list[dict]) -> list[dict]:
        if not records:
            return []
        features = build_fraud_feature_frame(pd.DataFrame(records))
        with threadpool_limits(limits=1):
            scores = self.pipeline.predict_proba(features)[:, 1]
        return [{"score": float(score), "alert": bool(score >= self.threshold),
                 "threshold": self.threshold, "score_is_calibrated": False} for score in scores]
