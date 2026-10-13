"""Clasificación de reclamos por producto a partir de la narrativa: partición, modelos y evaluación."""

import json
import platform
from dataclasses import asdict, dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer

from bankshield.features.text_cleaning import MARKER_TOKENS
from bankshield.ingestion.credit_profile import sha256_file
from bankshield.models.credit import load_verified_silver

LABEL = "product"
TEXT = "narrative_clean"
STOP_WORDS = sorted(ENGLISH_STOP_WORDS | set(MARKER_TOKENS))
BASELINE_KEYS = ("prior", "naive_bayes")
MAIN_KEY = "logistic_tfidf"


@dataclass(frozen=True)
class ComplaintsConfig:
    random_state: int = 42
    train_fraction: float = 0.70
    validation_fraction: float = 0.15
    min_words: int = 5
    ngram_max: int = 2
    min_df: int = 5
    max_df: float = 0.9
    max_features: int = 100000
    c_candidates: tuple = (1.0, 5.0, 20.0)
    max_iter: int = 300
    nb_alpha: float = 0.1
    top_terms: int = 10

    def __post_init__(self):
        if not (0 < self.train_fraction < 1 and 0 < self.validation_fraction < 1
                and self.train_fraction + self.validation_fraction < 1):
            raise ValueError("Las fracciones de entrenamiento y validación deben dejar una parte para prueba")
        for name in ("min_words", "ngram_max", "min_df", "max_features", "max_iter", "top_terms"):
            if not isinstance(getattr(self, name), int) or getattr(self, name) < 1:
                raise ValueError(f"{name} debe ser un entero positivo")
        if not 0 < self.max_df <= 1:
            raise ValueError("max_df debe estar en (0, 1]")
        if not np.isfinite(self.nb_alpha) or self.nb_alpha <= 0:
            raise ValueError("nb_alpha debe ser positivo y finito")
        candidates = tuple(self.c_candidates)
        if not candidates or any((not np.isfinite(c)) or c <= 0 for c in candidates):
            raise ValueError("c_candidates debe contener valores positivos y finitos")
        object.__setattr__(self, "c_candidates", candidates)


def select_narratives(silver, config):
    """Filtra reclamos con narrativa suficiente; devuelve (datos, conteos de exclusión)."""
    has_text = silver["has_narrative"].astype(bool)
    long_enough = silver["clean_word_count"] >= config.min_words
    selected = silver[has_text & long_enough].copy()
    exclusions = {"silver_rows": len(silver), "without_narrative": int((~has_text).sum()),
                  "too_short": int((has_text & ~long_enough).sum()), "selected": len(selected)}
    return selected, exclusions


def split_temporal(data, config):
    """Partición cronológica por fecha de primera aparición del texto.

    Un texto idéntico en varios reclamos se asigna completo a la partición de su fecha más antigua,
    de modo que no aparezca a la vez en entrenamiento y prueba. Los cortes caen en límites de fecha.
    """
    data = data.copy()
    data["assigned_date"] = data.groupby(TEXT)["date_received"].transform("min")
    cumulative = (data.groupby("assigned_date").size().sort_index().cumsum() / len(data))
    dates, values = cumulative.index, cumulative.to_numpy()
    cut_train = dates[int(np.searchsorted(values, config.train_fraction))]
    cut_valid = dates[int(np.searchsorted(values, config.train_fraction + config.validation_fraction))]
    assigned = data["assigned_date"]
    masks = {"train": assigned <= cut_train,
             "validation": (assigned > cut_train) & (assigned <= cut_valid),
             "test": assigned > cut_valid}
    parts = {name: data[mask].sort_values(["date_received", "complaint_id"]).reset_index(drop=True)
             for name, mask in masks.items()}
    if any(part.empty for part in parts.values()):
        raise ValueError("Alguna partición quedó vacía; revisar fracciones o cobertura temporal")
    if parts["train"][LABEL].nunique() < 2:
        raise ValueError("El entrenamiento necesita al menos dos productos")
    return parts, {"train_until": cut_train.date().isoformat(), "validation_until": cut_valid.date().isoformat()}


def _zeros(texts):
    return np.zeros((len(texts), 1))


def make_prior():
    return Pipeline([("ignore_text", FunctionTransformer(_zeros)),
                     ("model", DummyClassifier(strategy="prior"))])


def make_counts(config):
    return CountVectorizer(min_df=config.min_df, max_df=config.max_df, max_features=config.max_features,
                           stop_words=STOP_WORDS)


def make_naive_bayes(config):
    return Pipeline([("counts", make_counts(config)), ("model", MultinomialNB(alpha=config.nb_alpha))])


def make_tfidf(config):
    return TfidfVectorizer(ngram_range=(1, config.ngram_max), min_df=config.min_df, max_df=config.max_df,
                           max_features=config.max_features, sublinear_tf=True, stop_words=STOP_WORDS)


def make_logistic(c, config):
    return LogisticRegression(C=c, max_iter=config.max_iter, class_weight="balanced",
                              random_state=config.random_state)


def evaluate_predictions(y_true, probabilities, classes):
    """Exactitud, F1, top-3, métricas por clase y matriz de confusión; las clases sin soporte no promedian."""
    y_true, classes = np.asarray(y_true), np.asarray(classes)
    probabilities = np.asarray(probabilities, dtype="float64")
    if probabilities.shape != (len(y_true), len(classes)) or not np.isfinite(probabilities).all():
        raise ValueError("Probabilidades inválidas")
    predicted = classes[probabilities.argmax(axis=1)]
    labels = sorted(set(classes) | set(y_true))
    present = [c for c in labels if (y_true == c).any()]
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, predicted, labels=present, zero_division=0)
    top3 = classes[np.argsort(-probabilities, axis=1)[:, :3]]
    weights = support / support.sum()
    return {
        "rows": len(y_true),
        "accuracy": float(accuracy_score(y_true, predicted)),
        "macro_f1": float(f1.mean()),
        "weighted_f1": float((f1 * weights).sum()),
        "top3_accuracy": float((top3 == y_true[:, None]).any(axis=1).mean()),
        "per_class": {c: {"precision": float(p), "recall": float(r), "f1": float(f), "support": int(s)}
                      for c, p, r, f, s in zip(present, precision, recall, f1, support)},
        "confusion": {"labels": labels,
                      "matrix": confusion_matrix(y_true, predicted, labels=labels).tolist()},
    }


def top_terms(vectorizer, model, k):
    names = vectorizer.get_feature_names_out()
    return {str(c): [str(names[i]) for i in np.argsort(row)[-k:][::-1]]
            for c, row in zip(model.classes_, model.coef_)}


def _partition_summary(part):
    return {"rows": len(part), "first_date": part["date_received"].min().date().isoformat(),
            "last_date": part["date_received"].max().date().isoformat(),
            "products": {k: int(v) for k, v in part[LABEL].value_counts().items()}}


def train_complaints(silver_path, quality_path, config, output_dir, markdown_path=None):
    """Entrena referencias y modelo principal con entrenamiento/validación antes de abrir la prueba."""
    silver, quality = load_verified_silver(silver_path, quality_path)
    data, exclusions = select_narratives(silver, config)
    parts, cuts = split_temporal(data, config)
    ids = [set(p["complaint_id"]) for p in parts.values()]
    texts = [set(p[TEXT]) for p in parts.values()]
    if sum(map(len, ids)) != len(data) or len(set.union(*ids)) != len(data):
        raise ValueError("Las particiones no son disjuntas y completas")
    if (texts[0] & texts[1]) or (texts[0] & texts[2]) or (texts[1] & texts[2]):
        raise ValueError("Un mismo texto aparece en dos particiones")
    x = {name: p[TEXT].to_numpy() for name, p in parts.items()}
    y = {name: p[LABEL].to_numpy() for name, p in parts.items()}

    prior = make_prior().fit(x["train"], y["train"])
    bayes = make_naive_bayes(config).fit(x["train"], y["train"])
    tfidf = make_tfidf(config).fit(x["train"])
    matrix = {name: tfidf.transform(x[name]) for name in x}
    logistic = {c: make_logistic(c, config).fit(matrix["train"], y["train"]) for c in config.c_candidates}
    classes = prior.classes_ if hasattr(prior, "classes_") else prior.named_steps["model"].classes_

    validation = {"prior": evaluate_predictions(y["validation"], prior.predict_proba(x["validation"]), classes),
                  "naive_bayes": evaluate_predictions(
                      y["validation"], bayes.predict_proba(x["validation"]), bayes.classes_)}
    selection = []
    for c, model in logistic.items():
        metrics = evaluate_predictions(y["validation"], model.predict_proba(matrix["validation"]), model.classes_)
        validation[f"{MAIN_KEY}:C={c:g}"] = metrics
        selection.append({"C": c, "validation_macro_f1": metrics["macro_f1"],
                          "converged": bool(model.n_iter_.max() < config.max_iter)})
    best = max(selection, key=lambda row: (row["validation_macro_f1"], -row["C"]))
    chosen = logistic[best["C"]]
    # --- Congelado: a partir de aquí solo se lee la prueba ---
    test = {"prior": evaluate_predictions(y["test"], prior.predict_proba(x["test"]), classes),
            "naive_bayes": evaluate_predictions(y["test"], bayes.predict_proba(x["test"]), bayes.classes_),
            MAIN_KEY: evaluate_predictions(y["test"], chosen.predict_proba(matrix["test"]), chosen.classes_)}
    pipeline = Pipeline([("tfidf", tfidf), ("model", chosen)])
    base = Path(__file__)
    report = {
        "schema_version": 1, "config": asdict(config),
        "versions": {"python": platform.python_version(), "numpy": np.__version__,
                     "pandas": pd.__version__, "scikit_learn": sklearn.__version__,
                     "joblib": joblib.__version__},
        "code_sha256": {str(p.relative_to(base.parents[2])): sha256_file(p)
                        for p in (base, base.parents[1] / "features/text_cleaning.py")},
        "source": quality["source"], "training_input": quality["output"],
        "task": {"label": LABEL, "text": TEXT, "classes": [str(c) for c in classes]},
        "split_protocol": "temporal_70_15_15_by_first_appearance_of_text",
        "cuts": cuts, "exclusions": exclusions,
        "partitions": {name: _partition_summary(p) for name, p in parts.items()},
        "main_model": {"kind": "tfidf_logistic_regression", "C": best["C"],
                       "vectorizer_vocabulary": len(tfidf.vocabulary_),
                       "rationale": "referencias fijadas antes de ver validación o prueba; C elegido por "
                                    "macro-F1 en validación"},
        "c_selection": selection, "validation": validation, "test": test,
        "main_beats_references_on_test": bool(
            all(test[MAIN_KEY]["macro_f1"] > test[k]["macro_f1"] for k in BASELINE_KEYS)),
        "top_terms": top_terms(tfidf, chosen, config.top_terms),
        "limitations": ["only_complaints_with_narrative_and_consent", "thirteen_months_of_text",
                        "label_chosen_by_consumer", "contradictory_labels_for_identical_texts",
                        "rare_classes_have_few_examples", "company_names_dominate_top_terms",
                        "may_generalize_worse_to_unseen_companies", "no_hyperparameter_search_beyond_C",
                        "redaction_markers_ignored_by_vectorizer"],
    }
    bundle = {"artifact_version": 1, "pipeline": pipeline, "classes": [str(c) for c in chosen.classes_],
              "metadata": report}
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, output_dir / "model.joblib", compress=3)
    (output_dir / "metrics.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    if markdown_path:
        write_training_markdown(report, Path(markdown_path))
    return report


def write_training_markdown(report, path):
    cfg, ex = report["config"], report["exclusions"]
    lines = ["# Resultados del análisis NLP de reclamos — Angel", "",
             "Generado por `scripts/train_complaints.py`. Tarea: predecir el **producto** del reclamo "
             "(`product`, 11 clases) a partir de `narrative_clean`.", "",
             f"Entrada Silver SHA-256: `{report['training_input']['sha256']}`.", "",
             "## Datos y partición", "",
             f"De {ex['silver_rows']:,} reclamos del Silver se usan {ex['selected']:,}: se excluyen "
             f"{ex['without_narrative']:,} sin narrativa y {ex['too_short']:,} con menos de {cfg['min_words']} palabras.", "",
             f"Partición cronológica 70/15/15 por fecha de primera aparición del texto: entrenamiento hasta "
             f"{report['cuts']['train_until']}, validación hasta {report['cuts']['validation_until']} y prueba "
             "después. Un texto idéntico en varios reclamos se asigna completo a una sola partición, así el "
             "mismo texto no está en entrenamiento y prueba; por eso la última fecha de entrenamiento puede superar el "
             "corte, ya que incluye repeticiones tardías de textos vistos antes. El vectorizador se ajusta solo con "
             "entrenamiento.", "",
             "| Partición | Filas | Primera fecha | Última fecha |", "| --- | ---: | --- | --- |"]
    for name, p in report["partitions"].items():
        lines.append(f"| {name} | {p['rows']:,} | {p['first_date']} | {p['last_date']} |")
    lines += ["", "## Método", "",
              "- **Referencia trivial:** producto más frecuente en entrenamiento.",
              f"- **Línea base:** Naive Bayes multinomial sobre conteos de palabras (alpha {cfg['nb_alpha']:g}).",
              f"- **Método principal:** TF-IDF de 1 a {cfg['ngram_max']} palabras con regresión logística y pesos "
              f"balanceados por clase. C = {report['main_model']['C']:g}, elegido por macro-F1 en validación "
              f"entre {', '.join(f'{c:g}' for c in cfg['c_candidates'])}.",
              "- Las stopwords en inglés y los marcadores `<fecha>`, `<monto>` y `<censurado>` no entran al vocabulario.",
              "- La prueba se evalúa una sola vez, con los modelos ya congelados.", "",
              "## Resultados en prueba", "",
              "| Modelo | Exactitud | Macro-F1 | F1 ponderado | Top-3 |", "| --- | ---: | ---: | ---: | ---: |"]
    for key, r in report["test"].items():
        lines.append(f"| `{key}` | {r['accuracy']:.4f} | {r['macro_f1']:.4f} | {r['weighted_f1']:.4f} | "
                     f"{r['top3_accuracy']:.4f} |")
    verdict = "supera" if report["main_beats_references_on_test"] else "NO supera"
    lines += ["", f"El método principal **{verdict}** a ambas referencias en macro-F1. "
              "La macro-F1 pesa igual a cada producto; la exactitud, en cambio, premia acertar los productos "
              "grandes.", "",
              "### Elección de C (validación)", "", "| C | Macro-F1 validación | Convergió |", "| ---: | ---: | --- |"]
    for row in report["c_selection"]:
        lines.append(f"| {row['C']:g} | {row['validation_macro_f1']:.4f} | {'sí' if row['converged'] else 'no'} |")
    lines += ["", "### Métricas por producto (método principal, prueba)", "",
              "| Producto | Precisión | Recall | F1 | Soporte |", "| --- | ---: | ---: | ---: | ---: |"]
    for product, m in sorted(report["test"][MAIN_KEY]["per_class"].items(), key=lambda kv: -kv[1]["support"]):
        lines.append(f"| {product} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {m['support']:,} |")
    lines += ["", "## Términos con mayor peso por producto", "",
              "| Producto | Términos |", "| --- | --- |"]
    for product, terms in report["top_terms"].items():
        lines.append(f"| {product} | {', '.join(f'`{t}`' for t in terms)} |")
    lines += ["", "Muchos términos son **nombres de empresas** (`equifax`, `ocwen`, `moneygram`...). Están en la propia "
              "narrativa, así que no es fuga de datos, pero parte del acierto consiste en reconocer empresas y el "
              "modelo podría rendir peor con una empresa que no aparece en entrenamiento.", "",
              "## Límites", ""]
    lines += [f"- `{item}`" for item in report["limitations"]]
    lines += ["", "El modelo describe **qué producto sugiere el texto**, no la calidad de la atención ni el resultado "
              "del reclamo. Solo cubre reclamos con narrativa publicada con consentimiento; no representa a todos. "
              "Los ejemplos revisados están en [revision-ejemplos.md](revision-ejemplos.md).", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
