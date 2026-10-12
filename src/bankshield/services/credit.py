"""Scoring y explicación por oclusión del riesgo crediticio."""

from io import BytesIO
from pathlib import Path
import hashlib
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.exceptions import InconsistentVersionWarning

from bankshield.features.credit import INPUT_FIELDS, build_credit_feature_frame, feature_columns
from bankshield.models.credit import apply_calibrator

TOP_FACTORS = 5


class CreditScorer:
    def __init__(self, model_path: Path):
        payload = Path(model_path).read_bytes()
        with warnings.catch_warnings():
            warnings.simplefilter("error", InconsistentVersionWarning)
            bundle = joblib.load(BytesIO(payload))
        if not isinstance(bundle, dict) or bundle.get("artifact_version") != 1:
            raise ValueError("Versión de artefacto de crédito no soportada")
        self.feature_set = bundle["feature_set"]
        if bundle.get("feature_columns") != feature_columns(self.feature_set):
            raise ValueError("El modelo usa un contrato de variables distinto")
        self.pipeline, self.calibrator = bundle["pipeline"], bundle["calibrator"]
        if not callable(getattr(self.pipeline, "predict_proba", None)):
            raise ValueError("El artefacto no contiene un clasificador válido")
        self.threshold = float(bundle["threshold"])
        if not np.isfinite(self.threshold) or not 0 <= self.threshold <= 1:
            raise ValueError("Umbral inválido en el artefacto")
        self.reference = bundle["reference"]
        self.metadata = bundle["metadata"]
        if not isinstance(self.metadata, dict) or not isinstance(self.reference, dict):
            raise ValueError("Metadatos de crédito inválidos")
        self.model_id = hashlib.sha256(payload).hexdigest()

    def _probability(self, frame):
        raw = self.pipeline.predict_proba(frame)[:, 1]
        probability = apply_calibrator(self.calibrator, raw)
        if not np.isfinite(probability).all() or ((probability < 0) | (probability > 1)).any():
            raise ValueError("El modelo produjo probabilidades inválidas")
        return probability

    def score(self, records):
        """Probabilidad calibrada de impago asumido y decisión frente al umbral."""
        if not records:
            return []
        frame = build_credit_feature_frame(records, self.feature_set)
        return [{"default_probability": float(p), "high_risk": bool(p >= self.threshold),
                 "threshold": self.threshold} for p in self._probability(frame)]

    def explain(self, record, top=TOP_FACTORS):
        """Atribución por oclusión: cambio de probabilidad al sustituir cada variable por su
        valor de referencia (mediana/moda de entrenamiento). Descriptiva, no causal."""
        frame = build_credit_feature_frame([record], self.feature_set)
        base = float(self._probability(frame)[0])
        variants = []
        for name in frame.columns:
            variant = frame.copy()
            variant[name] = self.reference[name]
            variants.append(variant)
        probabilities = self._probability(pd.concat(variants, ignore_index=True))
        row = frame.iloc[0]
        factors = [{"feature": name, "value": None if pd.isna(row[name]) else row[name],
                    "reference": self.reference[name], "effect": float(base - p)}
                   for name, p in zip(frame.columns, probabilities)]
        factors.sort(key=lambda f: abs(f["effect"]), reverse=True)
        return {"base_probability": base, "factors": factors[:top],
                "method": "occlusion_vs_training_median_or_mode", "causal": False}

    def evaluation(self):
        return {"model_id": self.model_id, "threshold": self.threshold, "simulation_data": False,
                "input_fields": list(INPUT_FIELDS),
                **{key: self.metadata.get(key) for key in
                   ("source", "training_input", "versions", "main_model", "partitions", "validation",
                    "test", "test_calibration_tables", "threshold_selection", "limitations")}}
