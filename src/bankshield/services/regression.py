"""Servicio de estimación del monto: carga verificada del artefacto, métricas y ejemplos."""

from io import BytesIO
import hashlib
import json
from pathlib import Path
import warnings

import joblib
import numpy as np
from sklearn.exceptions import InconsistentVersionWarning

from bankshield.features.regression import FEATURE_COLUMNS, INPUT_FIELDS, build_regression_feature_frame
import bankshield.models.regression  # noqa: F401  (clases necesarias para deserializar)


class RegressionEstimator:
    def __init__(self, model_path: Path):
        model_path = Path(model_path)
        payload = model_path.read_bytes()
        self.model_id = hashlib.sha256(payload).hexdigest()
        with warnings.catch_warnings():
            warnings.simplefilter("error", InconsistentVersionWarning)
            bundle = joblib.load(BytesIO(payload))
        if not isinstance(bundle, dict) or bundle.get("artifact_version") != 1:
            raise ValueError("Versión de artefacto de regresión no soportada")
        if bundle.get("feature_columns") != FEATURE_COLUMNS or bundle.get("input_fields") != list(INPUT_FIELDS):
            raise ValueError("El modelo usa un contrato de variables distinto")
        self.model, self.selected_model = bundle["model"], bundle["selected_model"]
        self.metadata = bundle["metadata"]
        if not callable(getattr(self.model, "predict", None)) or not isinstance(self.metadata, dict):
            raise ValueError("Artefacto de regresión inválido")
        folder = model_path.parent
        self.metrics = self._sibling(folder / "metrics.json", "model_id")
        self.examples = self._sibling(folder / "examples.json", "model_id")
        if self.metrics.get("model_sha256") != self.model_id:
            raise ValueError("Las métricas no corresponden a este modelo")

    def _sibling(self, path, key):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get(key) != self.model_id:
            raise ValueError(f"{Path(path).name} pertenece a otro modelo")
        return data

    def predict(self, kind, balance):
        frame = build_regression_feature_frame([kind], [balance])
        value = float(np.asarray(self.model.predict(frame), dtype=float)[0])
        if not np.isfinite(value) or value < 0:
            raise ValueError("El modelo produjo una estimación inválida")
        return value

    def evaluation(self):
        keys = ("target", "input_fields", "selected_model", "selection_rule", "partitions", "train_sample",
                "amount_band_cuts", "comparison", "metrics", "versions", "limitations", "simulation_data",
                "dataset_sha256", "source_sha256")
        return {"model_id": self.model_id, "feature_columns": FEATURE_COLUMNS,
                **{key: self.metrics.get(key) for key in keys}}

    def examples_page(self, limit, offset):
        rows = self.examples["rows"]
        return {"model_id": self.model_id, "total": len(rows), "limit": limit, "offset": offset,
                "note": self.examples.get("note"), "rows": rows[offset:offset + limit]}
