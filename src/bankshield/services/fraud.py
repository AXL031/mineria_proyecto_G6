"""Scoring reutilizable para la futura API y página de fraude."""

from pathlib import Path
from io import BytesIO
import hashlib
import warnings

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from sklearn.exceptions import InconsistentVersionWarning

from bankshield.features.fraud import MODEL_FEATURES, build_fraud_feature_frame


class FraudScorer:
    def __init__(self, model_path: Path):
        payload = Path(model_path).read_bytes()
        with warnings.catch_warnings():
            warnings.simplefilter("error", InconsistentVersionWarning)
            bundle = joblib.load(BytesIO(payload))
        if not isinstance(bundle, dict) or bundle.get("artifact_version") != 1:
            raise ValueError("Versión de artefacto de fraude no soportada")
        if bundle.get("feature_columns") != list(MODEL_FEATURES):
            raise ValueError("El modelo usa un contrato de variables distinto")
        self.pipeline = bundle["pipeline"]
        if not callable(getattr(self.pipeline, "predict_proba", None)):
            raise ValueError("El artefacto no contiene un clasificador válido")
        self.threshold = float(bundle["threshold"])
        if not np.isfinite(self.threshold) or self.threshold < 0:
            raise ValueError("Umbral inválido en el artefacto")
        self.metadata = bundle["metadata"]
        if not isinstance(self.metadata, dict):
            raise ValueError("Metadatos de fraude inválidos")
        self.model_id = hashlib.sha256(payload).hexdigest()

    def score(self, records: list[dict]) -> list[dict]:
        if not records:
            return []
        features = build_fraud_feature_frame(pd.DataFrame(records))
        with threadpool_limits(limits=1):
            scores = self.pipeline.predict_proba(features)[:, 1]
        if not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
            raise ValueError("El clasificador produjo scores inválidos")
        return [{"score": float(score), "alert": bool(score >= self.threshold),
                 "threshold": self.threshold, "score_is_calibrated": False} for score in scores]

    def evaluation(self) -> dict:
        """Métricas embebidas en el modelo; no carga un JSON ajeno al artefacto."""
        return {"model_id": self.model_id, "threshold": self.threshold,
                "simulation_data": True, "score_is_calibrated": False,
                **{key: self.metadata.get(key) for key in
                   ("source", "training_input", "versions", "partitions", "validation",
                    "test", "threshold_selection", "limitations")}}
