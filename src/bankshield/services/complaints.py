"""Consulta del clasificador de producto y de los agregados CFPB para la demo."""

from io import BytesIO
import hashlib
import json
from pathlib import Path
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.exceptions import InconsistentVersionWarning

from bankshield.features.text_cleaning import clean_narrative


class ComplaintsScorer:
    def __init__(self, model_path: Path):
        payload = Path(model_path).read_bytes()
        with warnings.catch_warnings():
            warnings.simplefilter("error", InconsistentVersionWarning)
            bundle = joblib.load(BytesIO(payload))
        if not isinstance(bundle, dict) or bundle.get("artifact_version") != 1:
            raise ValueError("Artefacto NLP incompatible")
        self.pipeline = bundle["pipeline"]
        self.metadata = bundle["metadata"]
        self.classes = [str(value) for value in self.pipeline.classes_]
        if bundle.get("classes") != self.classes or len(self.classes) < 2:
            raise ValueError("Clases del artefacto incompatibles")
        if not isinstance(self.metadata, dict) or not callable(getattr(self.pipeline, "predict_proba", None)):
            raise ValueError("Modelo NLP inválido")
        self.minimum_words = int(self.metadata["config"]["min_words"])
        self.model_id = hashlib.sha256(payload).hexdigest()

    def predict(self, narrative: str) -> dict:
        cleaned = clean_narrative(narrative)
        if len(cleaned.split()) < self.minimum_words:
            raise ValueError(f"Escribe al menos {self.minimum_words} palabras en inglés")
        vectorizer = self.pipeline.named_steps["tfidf"]
        if vectorizer.transform([cleaned]).nnz == 0:
            raise ValueError("El texto no contiene términos reconocidos; usa una narrativa en inglés")
        scores = np.asarray(self.pipeline.predict_proba([cleaned])[0], dtype=float)
        if len(scores) != len(self.classes) or not np.isfinite(scores).all() or (scores < 0).any():
            raise RuntimeError("El modelo produjo puntuaciones inválidas")
        ranked = np.argsort(-scores)[:3]
        return {
            "product": self.classes[int(ranked[0])],
            "alternatives": [{"product": self.classes[int(i)], "score": float(scores[i])} for i in ranked],
            "scores_calibrated": False,
            "model_id": self.model_id,
            "language": "en",
            "clean_word_count": len(cleaned.split()),
        }

    def evaluation(self) -> dict:
        return {
            "model_id": self.model_id, "classes": self.classes,
            "scores_calibrated": False, "language": "en",
            **{key: self.metadata.get(key) for key in
               ("versions", "source", "training_input", "partitions", "cuts", "exclusions",
                "main_model", "test", "top_terms", "limitations")},
        }


def complaints_summary(path: Path) -> dict:
    frame = pd.read_parquet(path, columns=["date_received", "product", "has_narrative"])
    if frame.empty or frame["date_received"].isna().any():
        raise ValueError("Silver de reclamos inválido")
    dates = pd.to_datetime(frame["date_received"])
    monthly = frame.assign(month=dates.dt.strftime("%Y-%m")).groupby("month").agg(
        complaints=("product", "size"), narratives=("has_narrative", "sum"))
    return {
        "total_complaints": len(frame),
        "with_narrative": int(frame["has_narrative"].sum()),
        "first_date": dates.min().date().isoformat(), "last_date": dates.max().date().isoformat(),
        "products": [{"product": str(name), "complaints": int(count)}
                     for name, count in frame["product"].value_counts().items()],
        "monthly": [{"month": str(month), "complaints": int(row.complaints),
                     "narratives": int(row.narratives)} for month, row in monthly.iterrows()],
    }


def complaints_examples(path: Path, scorer: ComplaintsScorer) -> dict:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("model_input_sha256") != scorer.metadata["training_input"]["sha256"]:
        raise ValueError("Los ejemplos proceden de otro conjunto de datos")
    required = ("test_rows", "errors", "correct_examples", "high_confidence_errors")
    if not all(key in report for key in required):
        raise ValueError("Reporte de ejemplos incompleto")
    return {key: report[key] for key in required}
