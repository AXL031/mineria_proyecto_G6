"""Regresión del monto transaccional (SEV-01): referencia por tipo, Ridge y boosting.

Objetivo `amount`; entradas `type` y `oldbalanceOrg`. Todo ajuste usa solo la muestra de
entrenamiento; la selección usa solo validation; test y stress se informan sin reajustar.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import time

import joblib
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import sklearn
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from bankshield.features.regression import (
    FEATURE_COLUMNS, INPUT_FIELDS, NUMERIC_COLUMNS, TYPES, frame_from_dataset)

ARTIFACT_VERSION = 1
EVALUATED = ("validation", "test", "stress")
READ_COLUMNS = ["row_id", "step", "partition", "type", "amount", "oldbalanceOrg"]
LIMITATIONS = [
    "Estimación académica de un monto simulado (PaySim); no es una alerta de fraude ni un límite de crédito.",
    "No hay moneda real ni intervalos de confianza.",
    "Stress (steps 719-743, solo fraude) se informa aparte de test y no entra en la selección.",
    "Los predictores son solo tipo y saldo previo; se espera poco poder explicativo.",
]
SELECTION_ORDER = ("reference", "ridge_alpha_1", "ridge_alpha_10", "hist_gradient_boosting")


@dataclass(frozen=True)
class RegressionConfig:
    random_state: int = 42
    max_train_rows: int | None = 200000
    tie_tolerance: float = 1e-9
    ridge_alphas: tuple = (1.0, 10.0)
    boosting: dict = field(default_factory=lambda: {
        "max_iter": 100, "max_leaf_nodes": 15, "learning_rate": 0.1, "min_samples_leaf": 20})
    examples_rows: int = 200
    chunk_rows: int = 500000

    @classmethod
    def from_mapping(cls, mapping):
        known = {k: v for k, v in mapping.items() if k in cls.__dataclass_fields__}
        if "ridge_alphas" in known:
            known["ridge_alphas"] = tuple(known["ridge_alphas"])
        return cls(**known)


class MedianByType:
    """Referencia: mediana de train por tipo; mediana global si el tipo no tuvo observaciones."""

    def __init__(self, medians, global_median):
        self.medians, self.global_median = dict(medians), float(global_median)

    @classmethod
    def fit(cls, frame, target):
        data = pd.DataFrame({"type": frame["type"].to_numpy(), "y": np.asarray(target, dtype=float)})
        return cls(data.groupby("type")["y"].median().to_dict(), float(np.median(data["y"])))

    def predict(self, frame):
        return frame["type"].map(self.medians).fillna(self.global_median).to_numpy(dtype=float)


class LogAmountRegressor:
    """Ajusta log1p(amount), convierte con expm1 y recorta a cero (regla de dominio)."""

    def __init__(self, estimator):
        self.model = TransformedTargetRegressor(regressor=estimator, func=np.log1p, inverse_func=np.expm1,
                                                check_inverse=False)

    def fit(self, frame, target):
        self.model.fit(frame, np.asarray(target, dtype=float))
        return self

    def predict(self, frame):
        return np.clip(np.asarray(self.model.predict(frame), dtype=float), 0.0, None)


def _preprocessor(scaled):
    return ColumnTransformer([("type", OneHotEncoder(categories=[list(TYPES)], handle_unknown="error"), ["type"]),
                              ("num", StandardScaler() if scaled else "passthrough", NUMERIC_COLUMNS)])


def candidate_builders(config):
    builders = {"reference": None}
    for alpha in config.ridge_alphas:
        builders[f"ridge_alpha_{alpha:g}"] = lambda a=alpha: LogAmountRegressor(
            Pipeline([("prep", _preprocessor(True)), ("model", Ridge(alpha=a))]))
    params = {**config.boosting, "random_state": config.random_state}
    builders["hist_gradient_boosting"] = lambda: LogAmountRegressor(
        Pipeline([("prep", _preprocessor(False)), ("model", HistGradientBoostingRegressor(**params))]))
    return builders


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_dataset_hashes(report_path):
    """Huellas de Silver (`source`) y D1 (`output`) publicadas por la construcción de D1."""
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    try:
        return {"source": str(report["source"]["sha256"]).lower(), "dataset": str(report["output"]["sha256"]).lower()}
    except (KeyError, TypeError) as exc:
        raise ValueError("El reporte de D1 no incluye las huellas de Silver y D1") from exc


def select_train_sample(partition_values, config):
    """Muestra uniforme sin reemplazo (PCG64, semilla fija) solo dentro de train.

    Devuelve posiciones ordenadas en el archivo y la descripción del muestreo; la huella cubre
    los row_id seleccionados (row_id = posición ordinal base 1 en Silver)."""
    train_pos = np.flatnonzero(np.asarray(partition_values) == "train")
    available = int(train_pos.size)
    if config.max_train_rows is None or config.max_train_rows >= available:
        chosen = train_pos
    else:
        chosen = np.sort(np.random.default_rng(config.random_state).choice(
            train_pos, size=config.max_train_rows, replace=False))
    return chosen, {"algorithm": "numpy_default_rng_uniform_without_replacement_train_only",
                    "seed": config.random_state, "rows_available": available, "rows_used": int(chosen.size)}


class Accumulator:
    """Sumas por grupo para MAE, RMSE, R² y sesgo en bloques, sin retener predicciones."""

    def __init__(self):
        self.groups = {}

    def add(self, key, actual, prediction):
        error = prediction - actual
        row = self.groups.setdefault(key, np.zeros(6))
        row += [actual.size, np.abs(error).sum(), (error ** 2).sum(), error.sum(), actual.sum(), (actual ** 2).sum()]

    def total(self, predicate):
        return sum((row for key, row in self.groups.items() if predicate(key)), np.zeros(6))


def summarize(row):
    n = int(row[0])
    if n == 0:
        return {"n": 0, "mae": None, "rmse": None, "r2": None, "mean_bias": None,
                "r2_unavailable_reason": "sin observaciones"}
    sst = row[5] - row[4] ** 2 / n
    out = {"n": n, "mae": float(row[1] / n), "rmse": math.sqrt(row[2] / n), "mean_bias": float(row[3] / n)}
    if n < 2 or sst <= 1e-9 * max(1.0, abs(row[5])):
        out.update(r2=None, r2_unavailable_reason="varianza cero o n insuficiente")
    else:
        out.update(r2=float(1.0 - row[2] / sst), r2_unavailable_reason=None)
    return out


def iter_blocks(path, partitions, chunk_rows):
    """Bloques del Parquet D1 restringidos a las particiones pedidas."""
    for batch in pq.ParquetFile(path).iter_batches(batch_size=chunk_rows, columns=READ_COLUMNS):
        frame = batch.to_pandas()
        frame = frame[frame["partition"].isin(partitions)]
        if len(frame):
            yield frame


def amount_cuts(amounts):
    return [float(q) for q in np.quantile(amounts, [1 / 3, 2 / 3])]


def band_labels(cuts):
    return [f"<= {cuts[0]:.2f}", f"({cuts[0]:.2f}, {cuts[1]:.2f}]", f"> {cuts[1]:.2f}"]


def band_index(amounts, cuts):
    return np.searchsorted(np.asarray(cuts), amounts, side="left")


def evaluate(path, models, cuts, config):
    """Una pasada por D1: métricas por partición, tipo y tramo de monto para cada modelo."""
    accumulators = {name: Accumulator() for name in models}
    for block in iter_blocks(path, EVALUATED, config.chunk_rows):
        features = frame_from_dataset(block)
        actual = block["amount"].to_numpy(dtype=float)
        bands = band_index(actual, cuts)
        partition, kinds = block["partition"].to_numpy(), block["type"].to_numpy()
        for name, model in models.items():
            prediction = np.asarray(model.predict(features), dtype=float)
            if not np.isfinite(prediction).all() or (prediction < 0).any():
                raise ValueError("Predicciones no finitas o negativas")
            for part in EVALUATED:
                in_part = partition == part
                for kind in TYPES:
                    sel = in_part & (kinds == kind)
                    if sel.any():
                        accumulators[name].add((part, "type", kind), actual[sel], prediction[sel])
                for band in range(3):
                    sel = in_part & (bands == band)
                    if sel.any():
                        accumulators[name].add((part, "band", band), actual[sel], prediction[sel])
    labels, empty = band_labels(cuts), np.zeros(6)
    return {name: {part: {
        "overall": summarize(acc.total(lambda k, p=part: k[0] == p and k[1] == "type")),
        "by_type": {kind: summarize(acc.groups.get((part, "type", kind), empty)) for kind in TYPES},
        "by_amount_band": {labels[b]: summarize(acc.groups.get((part, "band", b), empty)) for b in range(3)},
    } for part in EVALUATED} for name, acc in accumulators.items()}


def choose_model(metrics, config):
    """Menor MAE de validation; un empate dentro de tolerancia favorece el orden de simplicidad."""
    maes = {name: metrics[name]["validation"]["overall"]["mae"] for name in metrics}
    best = min(maes.values())
    for name in SELECTION_ORDER:
        if name in maes and maes[name] <= best + config.tie_tolerance:
            return name
    raise ValueError("Sin candidato elegible")


PREDICTION_SCHEMA = pa.schema([
    ("row_id", pa.int64()), ("step", pa.int64()), ("partition", pa.string()), ("type", pa.string()),
    ("actual", pa.float64()), ("prediction", pa.float64()), ("model_id", pa.string()),
    ("source_sha256", pa.string()), ("dataset_sha256", pa.string())])


def export_predictions(path, model, model_id, hashes, output_path, config):
    """Predicciones del modelo seleccionado para todas las filas de validation/test/stress."""
    total = 0
    with pq.ParquetWriter(output_path, PREDICTION_SCHEMA, compression="snappy") as writer:
        for block in iter_blocks(path, EVALUATED, config.chunk_rows):
            prediction = np.asarray(model.predict(frame_from_dataset(block)), dtype=float)
            size = len(block)
            writer.write_table(pa.table({
                "row_id": block["row_id"].astype("int64").to_numpy(), "step": block["step"].astype("int64").to_numpy(),
                "partition": block["partition"].astype(str).to_numpy(), "type": block["type"].astype(str).to_numpy(),
                "actual": block["amount"].to_numpy(dtype=float), "prediction": prediction,
                "model_id": [model_id] * size, "source_sha256": [hashes["source"]] * size,
                "dataset_sha256": [hashes["dataset"]] * size}, schema=PREDICTION_SCHEMA))
            total += size
    return total


def build_examples(predictions_path, model_id, count, seed):
    """Muestra determinista de test (sin escoger aciertos) desde las predicciones exportadas."""
    table = pq.read_table(predictions_path, filters=[("partition", "=", "test")]).to_pandas()
    table = table.sort_values("row_id").reset_index(drop=True)
    if len(table) > count:
        table = table.iloc[np.sort(np.random.default_rng(seed).choice(len(table), size=count, replace=False))]
    return {"model_id": model_id, "partition": "test", "seed": seed, "total": int(len(table)),
            "note": "Ejemplos aleatorios de test; no son toda la evaluación ni solo aciertos.",
            "rows": json.loads(table.to_json(orient="records"))}


def train_regression(config, input_path, dataset_report, output_dir):
    started, started_cpu = time.time(), time.process_time()
    input_path, output_dir = Path(input_path), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    hashes = read_dataset_hashes(dataset_report)
    if sha256_file(input_path) != hashes["dataset"]:
        raise ValueError("La huella de D1 no coincide con su reporte; reconstruir D1")

    ids = pq.read_table(input_path, columns=["row_id", "partition"]).to_pandas()
    positions, sample = select_train_sample(ids["partition"].to_numpy(), config)
    chosen_ids = ids["row_id"].to_numpy()[positions].astype("<i8")
    sample["row_id_sha256"] = hashlib.sha256(chosen_ids.tobytes()).hexdigest()
    del ids
    wanted = pd.Index(chosen_ids)
    train = pd.concat([b[b["row_id"].isin(wanted)] for b in iter_blocks(input_path, ("train",), config.chunk_rows)],
                      ignore_index=True)
    if len(train) != sample["rows_used"]:
        raise ValueError("La muestra de entrenamiento no coincide con la selección")
    features, target = frame_from_dataset(train), train["amount"].to_numpy(dtype=float)
    cuts = amount_cuts(target)

    models, fit_seconds = {}, {}
    for name, builder in candidate_builders(config).items():
        t0 = time.time()
        models[name] = MedianByType.fit(features, target) if builder is None else builder().fit(features, target)
        fit_seconds[name] = round(time.time() - t0, 3)
    metrics = evaluate(input_path, models, cuts, config)
    selected = choose_model(metrics, config)
    metadata = {
        "target": "amount", "input_fields": list(INPUT_FIELDS), "feature_columns": FEATURE_COLUMNS,
        "selected_model": selected,
        "selection_rule": "menor MAE en validation; empate: referencia, Ridge alpha=1, Ridge alpha=10, boosting",
        "dataset_sha256": hashes["dataset"], "source_sha256": hashes["source"], "train_sample": sample,
        "amount_band_cuts": cuts,
        "partitions": {"train": "steps 1-323", "validation": "324-378", "test": "379-718", "stress": "719-743"},
        "metrics": metrics,
        "comparison": {n: {p: metrics[n][p]["overall"] for p in EVALUATED} for n in metrics},
        "fit_seconds": fit_seconds,
        "versions": {"python": platform.python_version(), "scikit-learn": sklearn.__version__,
                     "numpy": np.__version__, "pandas": pd.__version__, "joblib": joblib.__version__},
        "limitations": LIMITATIONS, "simulation_data": True,
        "config": {"random_state": config.random_state, "max_train_rows": config.max_train_rows,
                   "ridge_alphas": list(config.ridge_alphas), "boosting": config.boosting},
    }
    model_path = output_dir / "model.joblib"
    joblib.dump({"artifact_version": ARTIFACT_VERSION, "model": models[selected], "selected_model": selected,
                 "feature_columns": FEATURE_COLUMNS, "input_fields": list(INPUT_FIELDS), "metadata": metadata},
                model_path)
    model_id = sha256_file(model_path)

    predictions_path = output_dir / "predictions.parquet"
    rows = export_predictions(input_path, models[selected], model_id, hashes, predictions_path, config)
    (output_dir / "examples.json").write_text(json.dumps(
        build_examples(predictions_path, model_id, config.examples_rows, config.random_state),
        ensure_ascii=False, allow_nan=False), encoding="utf-8")
    query = {"model_id": model_id, "model_sha256": model_id, **{k: v for k, v in metadata.items()
                                                                 if k != "config"},
             "predictions_rows": rows,
             "run": {"seconds": round(time.time() - started, 1),
                     "cpu_seconds": round(time.process_time() - started_cpu, 1),
                     "generated_at": datetime.now(timezone.utc).isoformat()}}
    (output_dir / "metrics.json").write_text(json.dumps(query, ensure_ascii=False, indent=2, allow_nan=False),
                                             encoding="utf-8")
    return query
