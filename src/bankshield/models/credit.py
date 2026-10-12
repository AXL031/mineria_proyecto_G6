"""Entrenamiento, calibración, umbral y evaluación del riesgo crediticio."""

import json
import platform
from dataclasses import asdict, dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, confusion_matrix,
                             f1_score, log_loss, precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from bankshield.features.credit import (CATEGORIES, FEATURE_SETS, build_credit_feature_frame,
                                        feature_columns)
from bankshield.ingestion.credit_profile import sha256_file
from bankshield.models.fraud import select_threshold

EPS = 1e-6
MAIN_MODEL = ("hist_gradient_boosting", "application")


@dataclass(frozen=True)
class CreditConfig:
    random_state: int = 42
    validation_fraction: float = 0.15
    test_fraction: float = 0.15
    max_iter: int = 200
    max_leaf_nodes: int = 15
    learning_rate: float = 0.05
    min_samples_leaf: int = 40
    l2_regularization: float = 1.0
    approve_bad_cost: float = 5.0    # conceder crédito a quien incumple (FN)
    reject_good_cost: float = 1.0    # rechazar a quien pagaría (FP)
    calibration_bins: int = 10

    def __post_init__(self):
        if not (0 < self.validation_fraction < 0.5 and 0 < self.test_fraction < 0.5):
            raise ValueError("Las fracciones de validación y prueba deben estar en (0, 0.5)")
        for name in ("max_iter", "max_leaf_nodes", "min_samples_leaf", "calibration_bins"):
            if not isinstance(getattr(self, name), int) or getattr(self, name) < 1:
                raise ValueError(f"{name} debe ser un entero positivo")
        for name in ("learning_rate", "approve_bad_cost", "reject_good_cost"):
            if not np.isfinite(getattr(self, name)) or getattr(self, name) <= 0:
                raise ValueError(f"{name} debe ser positivo y finito")
        if not np.isfinite(self.l2_regularization) or self.l2_regularization < 0:
            raise ValueError("l2_regularization inválida")


def split_silver(silver, config):
    """Partición aleatoria estratificada y determinista; devuelve tres DataFrames."""
    rest, test = train_test_split(silver, test_size=config.test_fraction, random_state=config.random_state,
                                  stratify=silver["loan_status"])
    relative = config.validation_fraction / (1 - config.test_fraction)
    train, validation = train_test_split(rest, test_size=relative, random_state=config.random_state,
                                         stratify=rest["loan_status"])
    return {name: part.sort_values("row_id").reset_index(drop=True)
            for name, part in (("train", train), ("validation", validation), ("test", test))}


def _log1p(values):
    return np.log1p(np.clip(values, 0, None))


def _onehot(feature_set):
    categorical = FEATURE_SETS[feature_set][1]
    return OneHotEncoder(categories=[list(CATEGORIES[name]) for name in categorical],
                         sparse_output=False, handle_unknown="error"), list(categorical)


def make_classifier(kind, feature_set, config):
    numeric = list(FEATURE_SETS[feature_set][0])
    onehot, categorical = _onehot(feature_set)
    if kind == "prior":
        return Pipeline([("model", DummyClassifier(strategy="prior"))])
    if kind == "logistic":
        skewed = [n for n in numeric if n in ("person_income", "loan_amnt")]
        plain = [n for n in numeric if n not in skewed]
        numeric_steps = lambda: [("impute", SimpleImputer(strategy="median", add_indicator=True)),
                                 ("scale", StandardScaler())]
        encoder = ColumnTransformer([
            ("log", Pipeline([("log", FunctionTransformer(_log1p)), *numeric_steps()]), skewed),
            ("plain", Pipeline(numeric_steps()), plain),
            ("cat", onehot, categorical)])
        return Pipeline([("features", encoder),
                         ("model", LogisticRegression(C=1.0, max_iter=1000, random_state=config.random_state))])
    if kind == "hist_gradient_boosting":
        encoder = ColumnTransformer([("cat", onehot, categorical), ("num", "passthrough", numeric)])
        return Pipeline([("features", encoder), ("model", HistGradientBoostingClassifier(
            max_iter=config.max_iter, max_leaf_nodes=config.max_leaf_nodes,
            learning_rate=config.learning_rate, min_samples_leaf=config.min_samples_leaf,
            l2_regularization=config.l2_regularization, random_state=config.random_state,
            early_stopping=False))])
    raise ValueError(f"Modelo desconocido: {kind}")


def logit(scores):
    scores = np.clip(np.asarray(scores, dtype="float64"), EPS, 1 - EPS)
    return np.log(scores / (1 - scores)).reshape(-1, 1)


def fit_calibrator(validation_labels, validation_scores):
    """Calibración sigmoide (Platt) ajustada solo con validación."""
    return LogisticRegression(C=1e6, max_iter=1000).fit(logit(validation_scores), validation_labels)


def apply_calibrator(calibrator, scores):
    return calibrator.predict_proba(logit(scores))[:, 1]


def expected_calibration_error(labels, probabilities, bins=10):
    labels, probabilities = np.asarray(labels), np.asarray(probabilities)
    edges = np.linspace(0, 1, bins + 1)
    index = np.clip(np.digitize(probabilities, edges[1:-1]), 0, bins - 1)
    total = 0.0
    for b in range(bins):
        mask = index == b
        if mask.any():
            total += mask.mean() * abs(probabilities[mask].mean() - labels[mask].mean())
    return float(total)


def calibration_table(labels, probabilities, bins=10):
    """Deciles por cuantiles de probabilidad: media predicha frente a tasa observada."""
    frame = pd.DataFrame({"y": np.asarray(labels), "p": np.asarray(probabilities)})
    frame["bin"] = pd.qcut(frame["p"].rank(method="first"), bins, labels=False)
    grouped = frame.groupby("bin").agg(rows=("y", "size"), mean_predicted=("p", "mean"),
                                       observed_rate=("y", "mean"))
    return [{"bin": int(i), "rows": int(r.rows), "mean_predicted": float(r.mean_predicted),
             "observed_rate": float(r.observed_rate)} for i, r in grouped.iterrows()]


def evaluate_probabilities(labels, probabilities, threshold, config):
    labels = np.asarray(labels)
    probabilities = np.asarray(probabilities, dtype="float64")
    if set(np.unique(labels)) != {0, 1}:
        raise ValueError("La evaluación necesita ambas clases")
    if not np.isfinite(probabilities).all() or ((probabilities < 0) | (probabilities > 1)).any():
        raise ValueError("Probabilidades inválidas")
    predicted = probabilities >= threshold
    tn, fp, fn, tp = confusion_matrix(labels, predicted, labels=[0, 1]).ravel()
    cost = fp * config.reject_good_cost + fn * config.approve_bad_cost
    clipped = np.clip(probabilities, EPS, 1 - EPS)
    return {
        "rows": len(labels), "positives": int(labels.sum()), "prevalence": float(labels.mean()),
        "threshold": float(threshold),
        "roc_auc": float(roc_auc_score(labels, probabilities)),
        "average_precision": float(average_precision_score(labels, probabilities)),
        "brier": float(brier_score_loss(labels, probabilities)),
        "log_loss": float(log_loss(labels, clipped, labels=[0, 1])),
        "ece": expected_calibration_error(labels, probabilities, config.calibration_bins),
        "precision": float(precision_score(labels, predicted, zero_division=0)),
        "recall": float(recall_score(labels, predicted, zero_division=0)),
        "f1": float(f1_score(labels, predicted, zero_division=0)),
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "cost_units": float(cost), "cost_units_per_1000": float(cost / len(labels) * 1000),
    }


def _frame(part, feature_set):
    return build_credit_feature_frame(part, feature_set)


def reference_values(train, feature_set):
    """Valores neutros (mediana/moda de entrenamiento) para atribución por oclusión."""
    numeric, categorical = FEATURE_SETS[feature_set]
    frame = _frame(train, feature_set)
    reference = {name: float(frame[name].median()) for name in numeric}
    reference.update({name: str(frame[name].mode().iloc[0]) for name in categorical})
    return reference


def load_verified_silver(silver_path, quality_path):
    quality = json.loads(Path(quality_path).read_text(encoding="utf-8"))
    checks = quality.get("quality_checks", {})
    if (quality.get("scope") != "complete_file" or not checks
            or any(v is not True for v in checks.values())):
        raise ValueError("Se requiere un reporte Silver completo con controles aprobados")
    if quality.get("output", {}).get("sha256", "").lower() != sha256_file(silver_path).lower():
        raise ValueError("El Parquet cambió respecto al reporte; reconstruir Silver")
    silver = pd.read_parquet(silver_path)
    if len(silver) != quality["counts"]["silver_rows"]:
        raise ValueError("El recuento de filas no coincide con el reporte Silver")
    return silver, quality


def train_credit(silver_path, quality_path, config, output_dir, markdown_path=None):
    """Congela modelo, calibración y umbral con train/validación antes de abrir prueba."""
    silver, quality = load_verified_silver(silver_path, quality_path)
    parts = split_silver(silver, config)
    ids = [set(p["row_id"]) for p in parts.values()]
    if len(ids[0] | ids[1] | ids[2]) != len(silver) or (ids[0] & ids[1]) or (ids[0] & ids[2]) or (ids[1] & ids[2]):
        raise ValueError("Las particiones no son disjuntas y completas")
    candidates = [("prior", "application"), ("logistic", "application"),
                  ("hist_gradient_boosting", "application"), ("hist_gradient_boosting", "with_pricing")]
    models, raw_valid, raw_test = {}, {}, {}
    for kind, feature_set in candidates:
        key = f"{kind}:{feature_set}"
        model = make_classifier(kind, feature_set, config)
        model.fit(_frame(parts["train"], feature_set), parts["train"]["loan_status"])
        models[key] = model
        raw_valid[key] = model.predict_proba(_frame(parts["validation"], feature_set))[:, 1]
    main_key = ":".join(MAIN_MODEL)
    y_valid = parts["validation"]["loan_status"].to_numpy()
    calibrator = fit_calibrator(y_valid, raw_valid[main_key])
    calibrated_valid = apply_calibrator(calibrator, raw_valid[main_key])
    chosen = select_threshold(y_valid, calibrated_valid, config.reject_good_cost, config.approve_bad_cost)
    validation = {key: evaluate_probabilities(y_valid, scores, 0.5, config) for key, scores in raw_valid.items()}
    validation[main_key + ":calibrated"] = evaluate_probabilities(y_valid, calibrated_valid, chosen["threshold"], config)
    # --- Congelado: a partir de aquí solo se lee la prueba ---
    y_test = parts["test"]["loan_status"].to_numpy()
    for kind, feature_set in candidates:
        key = f"{kind}:{feature_set}"
        raw_test[key] = models[key].predict_proba(_frame(parts["test"], feature_set))[:, 1]
    calibrated_test = apply_calibrator(calibrator, raw_test[main_key])
    test = {key: evaluate_probabilities(y_test, scores, 0.5, config) for key, scores in raw_test.items()}
    test[main_key + ":calibrated"] = evaluate_probabilities(y_test, calibrated_test, chosen["threshold"], config)
    test_tables = {"main_uncalibrated": calibration_table(y_test, raw_test[main_key], config.calibration_bins),
                   "main_calibrated": calibration_table(y_test, calibrated_test, config.calibration_bins)}
    versions = {"python": platform.python_version(), "numpy": np.__version__,
                "pandas": pd.__version__, "scikit_learn": sklearn.__version__, "joblib": joblib.__version__}
    code = {str(p.relative_to(Path(__file__).parents[2])): sha256_file(p)
            for p in (Path(__file__), Path(__file__).parents[1] / "features/credit.py")}
    report = {
        "schema_version": 1, "config": asdict(config), "versions": versions, "code_sha256": code,
        "source": quality["source"], "training_input": quality["output"],
        "split_protocol": "random_stratified_70_15_15_after_dedup_fixed_seed",
        "main_model": {"kind": MAIN_MODEL[0], "feature_set": MAIN_MODEL[1],
                       "features": feature_columns(MAIN_MODEL[1]),
                       "rationale": "elegido antes de ver validación o prueba: la tasa y el grado los fija "
                                    "el prestamista tras evaluar el riesgo"},
        "partitions": {name: {"rows": len(p), "positives": int(p["loan_status"].sum()),
                              "prevalence": float(p["loan_status"].mean())} for name, p in parts.items()},
        "threshold_selection": {**chosen, "applied_to": "calibrated_probability",
                                "costs_are": "academic_assumptions"},
        "validation": validation, "test": test, "test_calibration_tables": test_tables,
        "limitations": ["label_semantics_unconfirmed", "no_temporal_or_customer_split",
                        "random_split_may_overestimate_generalization", "academic_error_costs",
                        "age_is_a_predictor_review_before_any_real_use",
                        "calibrator_and_threshold_share_validation_set",
                        "probability_of_default_does_not_define_optimal_credit_limit"],
    }
    bundle = {"artifact_version": 1, "pipeline": models[main_key], "calibrator": calibrator,
              "threshold": chosen["threshold"], "feature_set": MAIN_MODEL[1],
              "feature_columns": feature_columns(MAIN_MODEL[1]),
              "reference": reference_values(parts["train"], MAIN_MODEL[1]), "metadata": report}
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, output_dir / "model.joblib", compress=3)
    (output_dir / "metrics.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    if markdown_path:
        write_training_markdown(report, Path(markdown_path))
    return report


def write_training_markdown(report, path):
    cfg, thr = report["config"], report["threshold_selection"]
    lines = ["# Resultados del modelo de riesgo crediticio — Sevan", "",
             "Generado por `scripts/train_credit.py`. Clase positiva = impago **asumido** "
             "(ver [perfil](perfil-credito.md)).", "",
             f"Entrada Silver SHA-256: `{report['training_input']['sha256']}`.", "",
             "## Partición", "",
             "Aleatoria estratificada 70/15/15 con semilla fija, sobre filas sin duplicados exactos "
             "(no hay fecha ni cliente). No se aplicó balanceo de clases.", "",
             "| Partición | Filas | Positivos | Prevalencia |", "| --- | ---: | ---: | ---: |"]
    for name, p in report["partitions"].items():
        lines.append(f"| {name} | {p['rows']:,} | {p['positives']:,} | {p['prevalence']:.2%} |")
    lines += ["", "## Método", "",
              "- **Línea base trivial:** prevalencia de entrenamiento (`prior`).",
              "- **Línea base lineal:** regresión logística con imputación, escalado y logaritmo de ingreso/monto.",
              "- **Modelo principal:** `HistGradientBoostingClassifier` solo con variables de la solicitud "
              "(sin `loan_grade` ni `loan_int_rate`). Se fijó antes de ver validación o prueba.",
              "- **Comparación:** el mismo modelo con grado y tasa, para cuantificar cuánto aporta el riesgo "
              "ya evaluado por el prestamista; no se recomienda para decidir.",
              "- **Calibración:** sigmoide (Platt) ajustada en validación sobre el score del modelo principal.",
              f"- **Umbral:** {thr['threshold']:.4f} sobre la probabilidad calibrada; minimiza "
              f"FP×{cfg['reject_good_cost']:g} + FN×{cfg['approve_bad_cost']:g} en validación. "
              "Los costes son supuestos académicos.", "",
              "## Resultados en prueba", "",
              "Los modelos sin sufijo `calibrated` usan umbral 0.5 y sirven solo para comparar discriminación "
              "y calibración; el modelo calibrado usa el umbral elegido en validación.", "",
              "| Modelo | ROC-AUC | AP | Brier | ECE | Precisión | Recall | FP | FN |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for key, r in report["test"].items():
        c = r["confusion"]
        lines.append(f"| `{key}` | {r['roc_auc']:.4f} | {r['average_precision']:.4f} | {r['brier']:.4f} | "
                     f"{r['ece']:.4f} | {r['precision']:.3f} | {r['recall']:.3f} | {c['fp']} | {c['fn']} |")
    lines += ["", "## Calibración en prueba (modelo principal)", "",
              "| Decil | Filas | Predicha sin calibrar | Predicha calibrada | Observada |",
              "| ---: | ---: | ---: | ---: | ---: |"]
    raw, cal = report["test_calibration_tables"]["main_uncalibrated"], report["test_calibration_tables"]["main_calibrated"]
    for a, b in zip(raw, cal):
        lines.append(f"| {a['bin'] + 1} | {a['rows']} | {a['mean_predicted']:.3f} | "
                     f"{b['mean_predicted']:.3f} | {b['observed_rate']:.3f} |")
    lines += ["", "La sigmoide es monótona, así que ambos conjuntos de deciles contienen las mismas filas y "
              "comparten la tasa observada.", "",
              "## Límites", ""]
    lines += [f"- `{item}`" for item in report["limitations"]]
    lines += ["", "La probabilidad de impago **no** determina un monto o límite óptimo: faltan pérdida dada el "
              "impago, margen, plazo, costo de fondeo y respuesta de la demanda. El servicio no recomienda montos.", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
