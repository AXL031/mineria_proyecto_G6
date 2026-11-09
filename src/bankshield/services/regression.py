"""Inferencia del pipeline guardado y consultas con identidad coherente."""

from pathlib import Path

import joblib
import numpy as np
from threadpoolctl import threadpool_limits

from bankshield.analytics_contract import strict_json, validate_model_versions
from bankshield.features.regression import FEATURES, build_regression_features
from bankshield.models.regression import predict
from bankshield.transforms.silver_transactions import file_sha256


class RegressionScorer:
    def __init__(self, path):
        self.path = Path(path)
        self.model_id = file_sha256(self.path).lower()
        self.report = strict_json(self.path.with_name("metrics.json"))
        if self.report.get("schema_version") != 1 or self.report.get("model_id") != self.model_id:
            raise ValueError("Modelo y métricas de regresión no coinciden")
        validate_model_versions(self.report["versions"])
        # Solo artefactos locales producidos offline; ninguna ruta proviene de una petición.
        payload = joblib.load(self.path)
        if payload.get("schema_version") != 1 or payload["metadata"].get("feature_columns") != list(FEATURES):
            raise ValueError("Esquema del modelo incompatible")
        for key, value in payload["metadata"].items():
            if self.report.get(key) != value:
                raise ValueError(f"Métricas distintas de las del pipeline: {key}")
        self.model = payload["model"]

    def score(self, records):
        with threadpool_limits(limits=2):
            values = predict(self.model, build_regression_features(records))
        return [{"model_id": self.model_id, "target": "amount", "prediction": float(value),
                 "selected_model": self.report["selected_model"], "simulation_data": True,
                 "limitations": self.report["limitations"]} for value in values]

    def evaluation(self):
        return self.report

    def examples(self, limit=20, offset=0):
        path = self.path.with_name("examples.json")
        payload = strict_json(path)
        if (payload.get("schema_version") != 1 or payload.get("model_id") != self.model_id
                or file_sha256(path).lower() != self.report["export"]["examples_sha256"]):
            raise ValueError("Ejemplos incompatibles con el modelo")
        rows = payload["rows"]
        if len(rows) > 200 or len(rows) != self.report["export"]["examples_count"]:
            raise ValueError("Cantidad de ejemplos incompatible")
        for row in rows:
            if (row["model_id"] != self.model_id or row["partition"] != "test"
                    or row["dataset_sha256"] != self.report["dataset"]["dataset_sha256"]
                    or row["source_sha256"] != self.report["dataset"]["source_sha256"]
                    or not np.isfinite([row["actual"], row["prediction"]]).all()
                    or min(row["actual"], row["prediction"]) < 0):
                raise ValueError("Fila de ejemplos inválida")
        return {"schema_version": 1, "model_id": self.model_id, "total": len(rows),
                "limit": limit, "offset": offset, "rows": rows[offset:offset + limit],
                "sampling": payload["sampling"]}
