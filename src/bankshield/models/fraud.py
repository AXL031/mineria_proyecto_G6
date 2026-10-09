"""Entrenamiento temporal, selección de umbral y evaluación de fraude."""

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
from sklearn.metrics import (auc, average_precision_score, confusion_matrix,
                             precision_recall_curve, precision_score, recall_score, f1_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from threadpoolctl import threadpool_limits

from bankshield.features.fraud import MODEL_FEATURES
from bankshield.ingestion.fraud_dataset import derive_split_steps, read_fraud_dataset
from bankshield.ingestion.paysim_profile import TRANSACTION_TYPES, _sha256


@dataclass(frozen=True)
class FraudConfig:
    train_end_step: int = 323
    validation_end_step: int = 378
    chunksize: int = 200_000
    random_state: int = 42
    max_iter: int = 80
    max_leaf_nodes: int = 15
    learning_rate: float = 0.1
    min_samples_leaf: int = 20
    l2_regularization: float = 1.0
    false_positive_cost: float = 1.0
    false_negative_cost: float = 20.0
    threads: int = 4

    def __post_init__(self):
        if not (0 <= self.train_end_step < self.validation_end_step):
            raise ValueError("Límites temporales inválidos")
        for name in ("chunksize", "max_iter", "max_leaf_nodes", "min_samples_leaf", "threads"):
            if not isinstance(getattr(self, name), int) or getattr(self, name) < 1:
                raise ValueError(f"{name} debe ser un entero positivo")
        for name in ("learning_rate", "false_positive_cost", "false_negative_cost"):
            value = getattr(self, name)
            if not np.isfinite(value) or value <= 0:
                raise ValueError(f"{name} debe ser positivo y finito")
        if not np.isfinite(self.l2_regularization) or self.l2_regularization < 0:
            raise ValueError("l2_regularization inválida")


def _validate_scores(labels, scores):
    labels = np.asarray(labels)
    scores = np.asarray(scores, dtype="float64")
    if labels.ndim != 1 or scores.ndim != 1 or len(labels) != len(scores) or not len(labels):
        raise ValueError("Etiquetas y puntuaciones deben ser vectores no vacíos de igual longitud")
    if not np.isin(labels, [0, 1]).all() or not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
        raise ValueError("Se requieren etiquetas binarias y puntuaciones entre cero y uno")
    return labels, scores


def select_threshold(labels, scores, false_positive_cost=1.0, false_negative_cost=20.0):
    """Minimiza FP*C_FP + FN*C_FN en validación, incluyendo no emitir alertas.

    Con empates elige el umbral mayor. Nunca debe recibir etiquetas de prueba.
    """
    labels, scores = _validate_scores(labels, scores)
    if not all(np.isfinite(c) and c > 0 for c in (false_positive_cost, false_negative_cost)):
        raise ValueError("Los costes deben ser positivos y finitos")
    if set(np.unique(labels)) != {0, 1}:
        raise ValueError("La selección de umbral necesita ambas clases")
    order = np.argsort(-scores, kind="stable")
    ranked = scores[order]
    group_ends = np.r_[np.flatnonzero(ranked[:-1] != ranked[1:]), len(ranked) - 1]
    tp = np.cumsum(labels[order], dtype="int64")[group_ends]
    fp = group_ends + 1 - tp
    fn = labels.sum() - tp
    thresholds = np.r_[np.nextafter(ranked[0], np.inf), ranked[group_ends]]
    costs = np.r_[labels.sum() * false_negative_cost,
                  fp * false_positive_cost + fn * false_negative_cost]
    index = int(np.flatnonzero(costs == costs.min())[0])
    return {"threshold": float(thresholds[index]), "validation_cost_units": float(costs[index]),
            "false_positive_cost": false_positive_cost, "false_negative_cost": false_negative_cost,
            "rule": "alert_when_score_greater_than_or_equal_to_threshold",
            "tie_break": "highest_threshold"}


def evaluate_scores(labels, scores, threshold, config):
    labels, scores = _validate_scores(labels, scores)
    if set(np.unique(labels)) != {0, 1}:
        raise ValueError("La evaluación necesita ambas clases")
    predicted = scores >= threshold
    tn, fp, fn, tp = confusion_matrix(labels, predicted, labels=[0, 1]).ravel()
    precision, recall, _ = precision_recall_curve(labels, scores)
    cost = fp * config.false_positive_cost + fn * config.false_negative_cost
    return {
        "rows": len(labels), "fraud": int(labels.sum()), "prevalence": float(labels.mean()),
        "threshold": float(threshold), "average_precision": float(average_precision_score(labels, scores)),
        "pr_auc_trapezoid": float(auc(recall[::-1], precision[::-1])),
        "precision": float(precision_score(labels, predicted, zero_division=0)),
        "recall": float(recall_score(labels, predicted, zero_division=0)),
        "f1": float(f1_score(labels, predicted, zero_division=0)),
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "cost_units": float(cost), "cost_units_per_1000": float(cost / len(labels) * 1000),
    }


def make_classifier(config):
    numeric = [name for name in MODEL_FEATURES if name != "type"]
    encoder = ColumnTransformer([
        ("type", OneHotEncoder(categories=[sorted(TRANSACTION_TYPES)], sparse_output=False,
                               handle_unknown="error"), ["type"]),
        ("numeric", "passthrough", numeric),
    ])
    model = HistGradientBoostingClassifier(
        max_iter=config.max_iter, max_leaf_nodes=config.max_leaf_nodes,
        learning_rate=config.learning_rate, min_samples_leaf=config.min_samples_leaf,
        l2_regularization=config.l2_regularization, random_state=config.random_state,
        early_stopping=False,
    )
    return Pipeline([("features", encoder), ("classifier", model)])


def train_fraud(input_path, config, profile_path, output_dir, markdown_path=None,
                input_format="csv", silver_quality_path=None):
    """Verifica la fuente y congela el modelo/umbral antes de evaluar prueba."""
    input_path, output_dir = Path(input_path), Path(output_dir)
    profile = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    source_hash = _sha256(input_path)
    if profile.get("scope") != "complete_file" or profile.get("invalid_rows") != 0:
        raise ValueError("Se requiere un perfil completo sin registros inválidos")
    silver_quality = None
    if input_format == "csv":
        if profile["source"]["sha256"].lower() != source_hash.lower():
            raise ValueError("El CSV cambió respecto al perfil; volver a perfilar")
    elif input_format == "silver":
        if silver_quality_path is None:
            raise ValueError("Se requiere el reporte de calidad Silver")
        silver_quality = json.loads(Path(silver_quality_path).read_text(encoding="utf-8"))
        counts = silver_quality.get("counts", {})
        checks = silver_quality.get("quality_checks", {})
        required_checks = {"expected_header", "source_sha256_matches", "no_rejected_rows",
                           "no_exact_duplicate_rows", "steps_are_contiguous"}
        if (silver_quality.get("scope") != "complete_file"
                or counts.get("rejected_rows") != 0
                or counts.get("bronze_rows") != profile["rows"]
                or counts.get("silver_rows") != profile["rows"]
                or not required_checks.issubset(checks)
                or any(value is not True for value in checks.values())):
            raise ValueError("Se requiere Silver completo, sin rechazos y con controles aprobados")
        if silver_quality.get("source", {}).get("sha256", "").lower() != profile["source"]["sha256"].lower():
            raise ValueError("La fuente Bronze de Silver no coincide con el perfil de fraude")
        if silver_quality.get("output", {}).get("sha256", "").lower() != source_hash.lower():
            raise ValueError("El Parquet cambió o no tiene huella en el reporte; reconstruir Silver")
    else:
        raise ValueError("Formato de fraude desconocido")
    print("Fuente verificada. Leyendo particiones...", flush=True)
    partitions, overlap = read_fraud_dataset(
        input_path, config.train_end_step, config.validation_end_step, config.chunksize,
        input_format=input_format)
    if sum(len(part.labels) for part in partitions.values()) != profile["rows"]:
        raise ValueError("Los recuentos de entrenamiento no coinciden con el perfil")
    train, validation, test = (partitions[name] for name in ("train", "validation", "test"))
    baseline = DummyClassifier(strategy="prior")
    classifier = make_classifier(config)
    with threadpool_limits(limits=config.threads):
        baseline.fit(train.features, train.labels)
        print(f"Entrenando {len(train.labels):,} filas, {config.max_iter} iteraciones...", flush=True)
        classifier.fit(train.features, train.labels)
        print("Eligiendo el umbral exclusivamente en validación...", flush=True)
        validation_scores = classifier.predict_proba(validation.features)[:, 1]
        chosen = select_threshold(validation.labels, validation_scores,
                                  config.false_positive_cost, config.false_negative_cost)
        validations = {
            "baseline_prior": evaluate_scores(validation.labels, baseline.predict_proba(validation.features)[:, 1], 0.5, config),
            "classifier_default": evaluate_scores(validation.labels, validation_scores, 0.5, config),
            "classifier_selected": evaluate_scores(validation.labels, validation_scores, chosen["threshold"], config),
        }
        print("Modelo y umbral congelados. Evaluando prueba...", flush=True)
        test_scores = classifier.predict_proba(test.features)[:, 1]
        tests = {
            "baseline_prior": evaluate_scores(test.labels, baseline.predict_proba(test.features)[:, 1], 0.5, config),
            "classifier_default": evaluate_scores(test.labels, test_scores, 0.5, config),
            "classifier_selected": evaluate_scores(test.labels, test_scores, chosen["threshold"], config),
        }
    versions = {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                "scikit_learn": sklearn.__version__, "joblib": joblib.__version__}
    code_files = [Path(__file__), Path(__file__).parents[1] / "features/fraud.py",
                  Path(__file__).parents[1] / "ingestion/fraud_dataset.py"]
    code_hashes = {str(path.relative_to(Path(__file__).parents[2])): _sha256(path) for path in code_files}
    try:
        default_cuts = derive_split_steps(profile["by_step"])
    except ValueError:
        default_cuts = None
    report = {
        "schema_version": 1, "source": profile["source"], "config": asdict(config),
        "training_input": {"format": input_format, "file": input_path.name,
                           "sha256": source_hash},
        "versions": versions, "code_sha256": code_hashes,
        "split_protocol": "chronological_whole_steps_fixed_in_config",
        "matches_70_15_15_row_cuts": (config.train_end_step, config.validation_end_step) == default_cuts,
        "partitions": {name: {"rows": len(part.labels), "fraud": int(part.labels.sum()),
                               "prevalence": float(part.labels.mean()),
                               "min_step": int(part.steps.min()), "max_step": int(part.steps.max())}
                       for name, part in partitions.items()},
        "account_overlap_sample": overlap, "threshold_selection": chosen,
        "validation": validations, "test": tests,
        "limitations": ["synthetic_source", "uncalibrated_model_scores", "academic_error_costs",
                        "account_overlap_audit_is_sampled"] +
                        (["exact_duplicates_not_audited_by_training", "bronze_training_input"]
                         if silver_quality is None else ["silver_contract_peer_review_pending"]),
    }
    if silver_quality is not None:
        report["silver_quality"] = {"report_sha256": _sha256(Path(silver_quality_path)),
                                   "quality_checks": silver_quality["quality_checks"],
                                   "duplicates": silver_quality.get("duplicates")}
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"artifact_version": 1, "pipeline": classifier, "threshold": chosen["threshold"],
                 "feature_columns": list(MODEL_FEATURES), "metadata": report},
                output_dir / "model.joblib", compress=3)
    (output_dir / "metrics.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    if markdown_path:
        write_training_markdown(report, Path(markdown_path))
    print(f"Modelo y métricas: {output_dir}", flush=True)
    return report


def write_training_markdown(report, path):
    lines = ["# Entrenamiento inicial de fraude — Cueva", "",
             "Resultados de una ejecución completa, reproducible desde `scripts/train_fraud.py`.", "",
             f"Fuente Bronze SHA-256: `{report['source']['sha256']}`.", "",
             f"Entrada de entrenamiento: `{report['training_input']['format']}`; "
             f"SHA-256: `{report['training_input']['sha256']}`.", "",
             "## Separación temporal", "",
             ("Los cortes coinciden con el volumen acumulado objetivo 70/15/15, sin fraccionar pasos ni elegirlos por etiquetas. "
              if report["matches_70_15_15_row_cuts"] else "Los cortes son límites personalizados fijados en la configuración. ")
             + "No se aplicó submuestreo, sobremuestreo ni balanceo de clases.", "",
             "| Partición | Pasos | Filas | Fraudes | Prevalencia |", "| --- | --- | ---: | ---: | ---: |"]
    for name, part in report["partitions"].items():
        lines.append(f"| {name} | {part['min_step']}–{part['max_step']} | {part['rows']:,} | {part['fraud']:,} | {part['prevalence']:.6%} |")
    threshold = report["threshold_selection"]
    lines += ["", "## Método y umbral", "",
              "Línea base: puntuación constante igual a la prevalencia de entrenamiento (`DummyClassifier`). "
              "Clasificador: `HistGradientBoostingClassifier`, con codificación de tipo ajustada en entrenamiento. "
              "Se desactivó la parada temprana aleatoria; los hiperparámetros están fijados en `configs/fraud.json`.", "",
              f"Umbral elegido en validación: **{threshold['threshold']:.8f}**. "
              f"Coste supuesto: FP={threshold['false_positive_cost']}, FN={threshold['false_negative_cost']}. "
              "Se minimiza FP×C_FP + FN×C_FN, incluyendo la opción de no emitir alertas. "
              "Estos costes son supuestos académicos, no pérdidas monetarias verificadas.", "",
              "## Resultados", "",
              "AP es Average Precision, la métrica principal de resumen de precisión-recall. "
              "El JSON también conserva el área trapezoidal de esa curva como una métrica distinta.", "",
              "| Partición | Método | Umbral | AP | Precisión | Recall | F1 | FP | FN | TP | TN |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for split in ("validation", "test"):
        for name, result in report[split].items():
            c = result["confusion"]
            lines.append(f"| {split} | {name} | {result['threshold']:.8f} | {result['average_precision']:.6f} | {result['precision']:.6f} | {result['recall']:.6f} | {result['f1']:.6f} | {c['fp']} | {c['fn']} | {c['tp']} | {c['tn']} |")
    lines += ["", "## Auditoría y límites", "",
              "Se audita una muestra determinista aproximada del 1 % de cuentas por rol, sin usar "
              "identificadores como predictores. Los conteos de intersección son de la muestra, no totales.", "",
              "| Rol | Train–validación | Train–prueba | Validación–prueba |", "| --- | ---: | ---: | ---: |"]
    for role, overlaps in report["account_overlap_sample"]["sampled_intersections"].items():
        lines.append(f"| {role} | {overlaps['train_validation']} | {overlaps['train_test']} | {overlaps['validation_test']} |")
    lines += ["", "Los resultados describen la simulación PaySim. No validan una política bancaria real "
              "ni desempeño para cuentas completamente nuevas. Los scores no están calibrados como probabilidades "
              "de riesgo reales. Los controles Silver se incorporan al reporte cuando se entrena desde Parquet; "
              "la revisión compartida del contrato y una auditoría completa de entidades siguen pendientes. "
              "Las métricas de prueba se obtuvieron después de congelar modelo y umbral; no deben usarse para ajustar esta versión.", "",
              "## Artefactos", "",
              "`artifacts/models/fraud/model.joblib` contiene el pipeline, el umbral, las variables y los metadatos. "
              "`artifacts/models/fraud/metrics.json` conserva configuración, versiones, huellas de código y métricas. "
              "Ambos están excluidos de Git.", "",
              "## Referencias del método", "",
              "- [HistGradientBoostingClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html)",
              "- [Average Precision](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html)"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
