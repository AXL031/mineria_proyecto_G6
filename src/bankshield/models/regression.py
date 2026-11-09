"""Regresión de monto, selección en validación y evaluación completa por bloques."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

from bankshield.analytics_contract import atomic_model, provenance, write_json_atomic
from bankshield.features.regression import FEATURES, build_regression_features
from bankshield.ingestion.paysim_profile import TRANSACTION_TYPES
from bankshield.transforms.silver_transactions import file_sha256

MODEL_ORDER = ("median_by_type", "ridge_alpha_1", "ridge_alpha_10", "hist_gradient_boosting")
LIMITATIONS = [
    "Estimación académica sobre PaySim; no constituye una alerta de fraude ni un límite de crédito.",
    "Los montos no tienen moneda verificada; step es una hora simulada.",
    "El modelo se selecciona por MAE de validation, sin reajustar con validation o test.",
    "Stress 719-743 se informa aparte; no selecciona modelos ni umbrales.",
    "Los saldos de PaySim pueden reflejar limitaciones del simulador; no extrapolar a una entidad real.",
]


class MedianByType(RegressorMixin, BaseEstimator):
    def fit(self, X, y):
        frame = pd.DataFrame({"type": X["type"].to_numpy(), "amount": np.asarray(y)})
        self.global_median_ = float(frame.amount.median())
        self.medians_ = frame.groupby("type").amount.median().to_dict()
        return self

    def predict(self, X):
        return X.type.map(self.medians_).fillna(self.global_median_).to_numpy(dtype=float)


def candidates():
    models = {"median_by_type": MedianByType()}
    for name, regressor in (("ridge_alpha_1", Ridge(alpha=1)), ("ridge_alpha_10", Ridge(alpha=10)),
                            ("hist_gradient_boosting", HistGradientBoostingRegressor(
                                max_iter=100, max_leaf_nodes=15, learning_rate=0.1,
                                min_samples_leaf=20, random_state=42))):
        transform = ColumnTransformer([
            ("type", OneHotEncoder(categories=[sorted(TRANSACTION_TYPES)], handle_unknown="error", sparse_output=False), ["type"]),
            ("numeric", StandardScaler(), list(FEATURES[1:])),
        ])
        models[name] = TransformedTargetRegressor(
            regressor=Pipeline([("features", transform), ("regressor", regressor)]),
            func=np.log1p, inverse_func=np.expm1, check_inverse=False)
    return models


def predict(model, X):
    with np.errstate(over="ignore", invalid="ignore"):
        result = np.maximum(np.asarray(model.predict(X), dtype=float), 0)
    if not np.isfinite(result).all():
        raise ValueError("El modelo produjo un monto no finito")
    return result


def sample_train(dataset, max_rows, seed):
    """Reservorio uniforme por prioridades iid; mismo resultado entre tamaños de bloque."""
    if max_rows is not None and (isinstance(max_rows, bool) or not isinstance(max_rows, int) or max_rows < 1):
        raise ValueError("max_train_rows debe ser entero positivo o null")
    rng = np.random.default_rng(seed)
    selected = None
    keys = np.empty(0)
    available = 0
    for frame in dataset.batches("train"):
        available += len(frame)
        frame = frame[["row_id", "type", "oldbalanceOrg", "amount"]].copy()
        priority = rng.random(len(frame))
        selected = frame if selected is None else pd.concat([selected, frame], ignore_index=True)
        keys = np.concatenate([keys, priority])
        if max_rows is not None and len(selected) > max_rows:
            index = np.argpartition(keys, max_rows - 1)[:max_rows]
            selected = selected.iloc[index].reset_index(drop=True)
            keys = keys[index]
    if selected is None or not len(selected):
        raise ValueError("No hay entrenamiento en D1")
    selected = selected.sort_values("row_id").reset_index(drop=True)
    return selected, {"algorithm": "uniform_reservoir_iid_priorities", "seed": seed,
                      "rows_available": available, "rows_used": len(selected),
                      "row_ids_sha256": hashlib.sha256(selected.row_id.to_numpy(dtype="<i8").tobytes()).hexdigest()}


class MetricAccumulator:
    def __init__(self):
        self.n = 0
        self.actual_mean = self.actual_m2 = 0.0
        self.absolute_error = self.squared_error = self.bias = 0.0

    def add(self, actual, prediction):
        actual, prediction = np.asarray(actual, dtype=float), np.asarray(prediction, dtype=float)
        if not len(actual):
            return
        if not np.isfinite(actual).all() or not np.isfinite(prediction).all():
            raise ValueError("Métricas requieren valores finitos")
        difference = prediction - actual
        count = len(actual)
        mean = float(actual.mean())
        delta = mean - self.actual_mean
        self.actual_m2 += float(np.square(actual - mean).sum()) + delta * delta * self.n * count / (self.n + count)
        self.actual_mean += delta * count / (self.n + count)
        self.n += count
        self.absolute_error += float(np.abs(difference).sum())
        self.squared_error += float(np.square(difference).sum())
        self.bias += float(difference.sum())

    def result(self):
        reason = "insufficient_rows" if self.n < 2 else "constant_target" if self.actual_m2 == 0 else None
        return {"n": self.n, "mae": self.absolute_error / self.n if self.n else None,
                "rmse": float(np.sqrt(self.squared_error / self.n)) if self.n else None,
                "r2": 1 - self.squared_error / self.actual_m2 if reason is None else None,
                "r2_undefined_reason": reason, "mean_bias": self.bias / self.n if self.n else None}


def evaluate(dataset, models, partition, amount_edges):
    accumulators = {name: {"overall": MetricAccumulator(), "by_type": {}, "by_amount_bin": {}}
                    for name in models}
    for frame in dataset.batches(partition):
        X = build_regression_features(frame)
        actual = frame.amount.to_numpy()
        target_bins = np.searchsorted(amount_edges, actual, side="left")
        for name, model in models.items():
            predicted = predict(model, X)
            accumulators[name]["overall"].add(actual, predicted)
            for field, values in (("by_type", frame.type.to_numpy()), ("by_amount_bin", target_bins)):
                for value in np.unique(values):
                    index = values == value
                    accumulators[name][field].setdefault(str(value), MetricAccumulator()).add(actual[index], predicted[index])
    return {name: {"overall": metrics["overall"].result(), **{
        field: {value: accumulator.result() for value, accumulator in metrics[field].items()}
        for field in ("by_type", "by_amount_bin")}} for name, metrics in accumulators.items()}


def select_model(validation):
    best = MODEL_ORDER[0]
    for name in MODEL_ORDER[1:]:
        if validation[name]["overall"]["mae"] < validation[best]["overall"]["mae"] - 1e-9:
            best = name
    return best


def export_predictions(dataset, model, model_id, path, examples_limit, seed):
    schema = pa.schema([("row_id", pa.int64()), ("step", pa.int64()), ("partition", pa.string()),
                        ("type", pa.string()), ("actual", pa.float64()), ("prediction", pa.float64()),
                        ("model_id", pa.string()), ("source_sha256", pa.string()), ("dataset_sha256", pa.string())])
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    writer = pq.ParquetWriter(temporary, schema, compression="snappy")
    rng = np.random.default_rng(seed)
    examples = pd.DataFrame()
    keys = np.empty(0)
    counts = {name: 0 for name in ("validation", "test", "stress")}
    try:
        for frame in dataset.batches():
            frame = frame.loc[frame.partition.ne("train")]
            if frame.empty:
                continue
            exported = frame[["row_id", "step", "partition", "type"]].copy()
            exported["actual"] = frame.amount.to_numpy()
            exported["prediction"] = predict(model, build_regression_features(frame))
            exported["model_id"] = model_id
            exported["source_sha256"] = dataset.source_sha256
            exported["dataset_sha256"] = dataset.dataset_sha256
            writer.write_table(pa.Table.from_pandas(exported, schema=schema, preserve_index=False))
            for name, count in exported.partition.value_counts().items():
                counts[name] += int(count)
            test = exported.loc[exported.partition.eq("test")]
            keys = np.concatenate([keys, rng.random(len(test))])
            examples = pd.concat([examples, test], ignore_index=True)
            if len(examples) > examples_limit:
                index = np.argpartition(keys, examples_limit - 1)[:examples_limit]
                examples, keys = examples.iloc[index].reset_index(drop=True), keys[index]
        writer.close()
        temporary.replace(path)
    finally:
        writer.close()
        temporary.unlink(missing_ok=True)
    return examples.sort_values("row_id").to_dict(orient="records"), counts


def train(dataset, config, output):
    started = time.perf_counter()
    if config.get("seed") != 42 or not 1 <= config.get("examples_limit", 200) <= 200:
        raise ValueError("Protocolo v1 requiere seed=42 y examples_limit entre 1 y 200")
    sampled, sampling = sample_train(dataset, config["max_train_rows"], config["seed"])
    X, y = build_regression_features(sampled), sampled.amount.to_numpy()
    models = candidates()
    # El análisis de errores usa los cortes ajustados con TODO train por D1.
    amount_edges = dataset.bins["columns"]["amount"]["interior_edges"]
    with threadpool_limits(limits=2):
        for name, model in models.items():
            print(f"Ajustando {name}: {len(sampled):,} filas", flush=True)
            model.fit(X, y)
        evaluation = {"validation": evaluate(dataset, models, "validation", amount_edges)}
        selected = select_model(evaluation["validation"])
        print(f"Seleccionado por MAE validation: {selected}", flush=True)
        for name in ("test", "stress"):
            evaluation[name] = evaluate(dataset, models, name, amount_edges)
        report = {"schema_version": 1, "target": "amount", "simulation_data": True,
                  "generated_at_utc": datetime.now(timezone.utc).isoformat(), "selected_model": selected,
                  "feature_columns": list(FEATURES), "public_inputs": ["type", "oldbalanceOrg"],
                  "dataset": dataset.identity(), "sampling": sampling,
                  "selection": {"partition": "validation", "metric": "mae", "tie_tolerance": 1e-9,
                                "tie_order": list(MODEL_ORDER), "refit_validation": False},
                  "candidate_parameters": {"ridge_alpha": [1, 10], "target_transform": "log1p/expm1",
                      "prediction_clip_min": 0, "hist_gradient_boosting": {"max_iter": 100,
                          "max_leaf_nodes": 15, "learning_rate": 0.1, "min_samples_leaf": 20, "random_state": 42}},
                  "error_amount_edges_train": amount_edges, "evaluation": evaluation,
                  "limitations": LIMITATIONS,
                  **provenance([Path(__file__), Path(__file__).parents[1] / "analytics_contract.py",
                                Path(__file__).parents[1] / "features/regression.py"])}
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)
        model_path = output / "model.joblib"
        atomic_model(model_path, {"schema_version": 1, "model": models[selected], "metadata": report})
        report["model_id"] = file_sha256(model_path).lower()
        examples, counts = export_predictions(dataset, models[selected], report["model_id"],
                                              output / "predictions.parquet", config["examples_limit"], config["seed"])
    report["export"] = {"rows_by_partition": counts, "examples_count": len(examples),
                        "examples_method": "uniform_test_reservoir_seed_42",
                        "predictions_sha256": file_sha256(output / "predictions.parquet").lower()}
    report["duration_seconds"] = time.perf_counter() - started
    write_json_atomic(output / "examples.json", {"schema_version": 1, "model_id": report["model_id"],
                                               "sampling": report["export"]["examples_method"], "rows": examples})
    report["export"]["examples_sha256"] = file_sha256(output / "examples.json").lower()
    # Publicar métricas al final: un modelo nuevo con metadatos anteriores no es servible.
    write_json_atomic(output / "metrics.json", report)
    return report


def render_markdown(report):
    lines = ["# Resultados de regresión numérica del monto transaccional", "",
             f"Modelo seleccionado: **{report['selected_model']}**, por MAE de validation.",
             f"Modelo SHA-256: `{report['model_id']}`.",
             f"D1 SHA-256: `{report['dataset']['dataset_sha256']}`.",
             f"Corrida UTC: {report['generated_at_utc']}; duración: {report['duration_seconds']:.2f} s.",
             f"Train: {report['sampling']['rows_used']:,} de {report['sampling']['rows_available']:,} filas; semilla 42.",
             "", "| Partición | Candidato | n | MAE | RMSE | R² | Sesgo medio |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for part, models in report["evaluation"].items():
        for name, values in models.items():
            m = values["overall"]
            r2 = "N/D" if m["r2"] is None else f"{m['r2']:.6f}"
            lines.append(f"| {part} | {name} | {m['n']} | {m['mae']:.4f} | {m['rmse']:.4f} | {r2} | {m['mean_bias']:.4f} |")
    lines += ["", "Stress se informa separado de test. Ningún candidato se reajustó después de validation.",
              "", "## Errores del modelo seleccionado por tipo y tramo de monto", "",
              "Cortes de monto ajustados solo con train: " + str(report["error_amount_edges_train"]), "",
              "| Partición | Agrupación | Grupo | n | MAE | RMSE |", "| --- | --- | --- | ---: | ---: | ---: |"]
    for part, models in report["evaluation"].items():
        for grouping in ("by_type", "by_amount_bin"):
            for group, m in models[report["selected_model"]][grouping].items():
                lines.append(f"| {part} | {grouping} | {group} | {m['n']} | {m['mae']:.4f} | {m['rmse']:.4f} |")
    lines += ["", "## Procedencia", "", "```json", json.dumps({key: report[key] for key in (
        "sampling", "selection", "export", "versions", "git", "code_sha256")}, indent=2), "```", "",
              "## Limitaciones", "", *["- " + value for value in LIMITATIONS], ""]
    return "\n".join(lines)
