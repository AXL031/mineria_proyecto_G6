"""Scoring y asociaciones descriptivas para la API y página de fraude."""

from pathlib import Path
from io import BytesIO
import hashlib
import json
import warnings

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from sklearn.exceptions import InconsistentVersionWarning

from bankshield.features.fraud import MODEL_FEATURES, build_fraud_feature_frame
from bankshield.features.fraud_patterns import RULES, summarize_rules


class FraudScorer:
    def __init__(self, model_path: Path):
        self.model_path = Path(model_path)
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

    def patterns(self, report_path=None) -> dict:
        """Solo sirve un reporte de asociaciones vinculado al modelo vigente."""
        path = Path(report_path) if report_path else self.model_path.with_name("patterns.json")
        report = json.loads(path.read_text(encoding="utf-8"))
        if (not isinstance(report, dict)
                or report.get("schema_version") != 1 or report.get("model_id") != self.model_id
                or report.get("training_input") != self.metadata.get("training_input")
                or report.get("method") != "fixed_antecedents_descriptive_association"
                or report.get("rules_selected_using_test") is not False):
            raise ValueError("Reporte de patrones incompatible con el modelo")
        for name, expected in self.metadata["partitions"].items():
            partitions = report.get("partitions", {})
            if not isinstance(partitions, dict):
                raise ValueError("Particiones de patrones inválidas")
            observed = partitions.get(name, {})
            if (not isinstance(observed, dict) or observed.get("rows") != expected["rows"]
                    or observed.get("fraud") != expected["fraud"]):
                raise ValueError("Particiones de patrones incompatibles")
            rows = observed.get("rules", [])
            if (not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows)
                    or [row.get("id") for row in rows] != list(RULES)):
                raise ValueError("Reglas descriptivas incompatibles")
            counts = {}
            for row in rows:
                matches, positives = row.get("matches"), row.get("fraud_matches")
                if (type(matches) is not int or type(positives) is not int
                        or not 0 <= matches <= expected["rows"]
                        or not 0 <= positives <= min(matches, expected["fraud"])):
                    raise ValueError("Recuentos de reglas inválidos")
                counts[row["id"]] = [matches, positives]
            if observed != summarize_rules(expected["rows"], expected["fraud"], counts):
                raise ValueError("Métricas de patrones inconsistentes")
        return report
