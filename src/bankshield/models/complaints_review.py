"""Revisión de ejemplos del clasificador de reclamos: pares confundidos, errores seguros y etiquetas contradictorias.

Solo lee la partición de prueba para describir errores; no ajusta modelo, umbrales ni hiperparámetros.
"""

import json
from pathlib import Path

import joblib
import numpy as np

from bankshield.models.complaints import (LABEL, TEXT, ComplaintsConfig, select_narratives, split_temporal)
from bankshield.models.credit import load_verified_silver

MANUAL_MARKER = "<!-- OBSERVACIONES -->"
MANUAL_PLACEHOLDER = "\n\n## Observaciones de la revisión\n\n_Pendiente: registrar tras leer los ejemplos._\n"
CONFIDENCE_BUCKETS = ((0.0, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0001))


def _snippet(text, limit):
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def _example(row, limit=350):
    return {"complaint_id": int(row["complaint_id"]), "date_received": row["date_received"].date().isoformat(),
            "true": row[LABEL], "predicted": row["predicted"], "confidence": round(float(row["confidence"]), 4),
            "text": _snippet(row[TEXT], limit)}


def near_duplicate_summary(pipeline, train_texts, test_texts, correct, threshold=0.9, chunk=500):
    """Compara cada texto de prueba con su vecino más parecido en entrenamiento (coseno TF-IDF).

    Los textos casi idénticos (p. ej. el mismo reclamo presentado dos veces con otra censura) no se
    detectan por igualdad exacta y pueden inflar las métricas de prueba.
    """
    tfidf = pipeline.named_steps["tfidf"]
    train_matrix = tfidf.transform(train_texts).T.tocsc()
    test_matrix = tfidf.transform(test_texts)
    best = np.zeros(test_matrix.shape[0])
    for start in range(0, test_matrix.shape[0], chunk):
        similarity = test_matrix[start:start + chunk] @ train_matrix
        best[start:start + chunk] = similarity.max(axis=1).toarray().ravel()
    near = best >= threshold
    correct = np.asarray(correct, dtype=bool)
    return {"threshold": threshold, "near_duplicate_rows": int(near.sum()),
            "share": float(near.mean()),
            "accuracy_near": float(correct[near].mean()) if near.any() else None,
            "accuracy_rest": float(correct[~near].mean()) if (~near).any() else None}


def build_error_review(model_path, silver_path, quality_path, seed=42, pairs=4, per_pair=3,
                       high_confidence=8, contradictions=6, correct_classes=4):
    """Reconstruye la partición de prueba del modelo guardado y extrae ejemplos de revisión."""
    bundle = joblib.load(model_path)
    meta = bundle["metadata"]
    silver, quality = load_verified_silver(silver_path, quality_path)
    if quality["output"]["sha256"].lower() != meta["training_input"]["sha256"].lower():
        raise ValueError("El modelo se entrenó con otro Silver; reconstruir el modelo o el Silver")
    config = ComplaintsConfig(**meta["config"])
    data, _ = select_narratives(silver, config)
    parts, _ = split_temporal(data, config)
    test = parts["test"]
    if len(test) != meta["partitions"]["test"]["rows"]:
        raise ValueError("La partición de prueba reconstruida no coincide con la del modelo")

    classes = np.asarray(bundle["classes"])
    proba = bundle["pipeline"].predict_proba(test[TEXT].to_numpy())
    test = test.assign(predicted=classes[proba.argmax(axis=1)], confidence=proba.max(axis=1))
    test["correct"] = test[LABEL] == test["predicted"]
    errors = test[~test["correct"]]

    buckets = []
    for low, high in CONFIDENCE_BUCKETS:
        part = test[(test["confidence"] >= low) & (test["confidence"] < high)]
        buckets.append({"from": low, "to": min(high, 1.0), "rows": len(part),
                        "accuracy": float(part["correct"].mean()) if len(part) else None})

    counts = errors.groupby([LABEL, "predicted"]).size().sort_values(ascending=False)
    confused = []
    for (true, predicted), n in counts.head(pairs).items():
        group = errors[(errors[LABEL] == true) & (errors["predicted"] == predicted)]
        sample = group.sample(min(per_pair, len(group)), random_state=seed)
        confused.append({"true": true, "predicted": predicted, "errors": int(n),
                         "share_of_true_class": float(n / (test[LABEL] == true).sum()),
                         "examples": [_example(r) for _, r in sample.iterrows()]})

    surest = errors.sort_values(["confidence", "complaint_id"], ascending=[False, True]).head(high_confidence)
    top_classes = test[LABEL].value_counts().head(correct_classes).index
    correct = []
    for product in top_classes:
        group = test[(test[LABEL] == product) & test["correct"]]
        if len(group):
            correct.append(_example(group.sample(1, random_state=seed).iloc[0]))

    grouped = data.groupby(TEXT)[LABEL].agg(["nunique", "size"])
    mixed = grouped[grouped["nunique"] > 1].sort_values("size", ascending=False)
    contradictory = []
    for text, row in mixed.head(contradictions).iterrows():
        labels = data.loc[data[TEXT] == text, LABEL].value_counts()
        contradictory.append({"text": _snippet(text, 250), "reclamos": int(row["size"]),
                              "products": {k: int(v) for k, v in labels.items()}})

    return {
        "schema_version": 1, "seed": seed, "model_input_sha256": meta["training_input"]["sha256"],
        "test_rows": len(test), "errors": len(errors), "accuracy": float(test["correct"].mean()),
        "confidence_buckets": buckets,
        "near_duplicates_vs_train": near_duplicate_summary(
            bundle["pipeline"], parts["train"][TEXT].to_numpy(), test[TEXT].to_numpy(), test["correct"].to_numpy()),
        "confused_pairs": confused,
        "high_confidence_errors": [_example(r) for _, r in surest.iterrows()],
        "correct_examples": correct,
        "contradictory_label_groups": {"groups_total": int(len(mixed)), "examples": contradictory},
    }


def review_markdown(review):
    lines = ["# Revisión de ejemplos — clasificador de reclamos", "",
             "Generado por `scripts/analyze_complaints_errors.py` sobre la partición de **prueba** del modelo de "
             "[resultados-modelo.md](resultados-modelo.md). Los ejemplos se eligen con semilla "
             f"{review['seed']} y no se usan para ajustar el modelo. Se muestra el texto limpio (en minúsculas, con "
             "marcadores), recortado; las narrativas son públicas y anonimizadas por la CFPB.", "",
             f"Prueba: {review['test_rows']:,} reclamos, {review['errors']:,} errores "
             f"(exactitud {review['accuracy']:.2%}).", "",
             "## Confianza frente a acierto", "",
             "| Confianza del modelo | Reclamos | Exactitud |", "| --- | ---: | ---: |"]
    for b in review["confidence_buckets"]:
        accuracy = "—" if b["accuracy"] is None else f"{b['accuracy']:.2%}"
        lines.append(f"| {b['from']:.1f} – {b['to']:.1f} | {b['rows']:,} | {accuracy} |")
    nd = review["near_duplicates_vs_train"]
    if nd["near_duplicate_rows"]:
        lines += ["", "## Casi-duplicados con el entrenamiento", "",
                  f"{nd['near_duplicate_rows']:,} reclamos de prueba ({nd['share']:.1%}) tienen en entrenamiento un "
                  f"texto con similitud coseno TF-IDF ≥ {nd['threshold']:g}. Exactitud en ese grupo: "
                  f"{nd['accuracy_near']:.2%}; en el resto: {nd['accuracy_rest']:.2%}. La partición solo separa "
                  "textos *idénticos*, así que estos casos pueden favorecer al modelo."]
    lines += ["", "## Pares de productos más confundidos", "",
              "| Producto real | Predicho | Errores | % del producto real |", "| --- | --- | ---: | ---: |"]
    for pair in review["confused_pairs"]:
        lines.append(f"| {pair['true']} | {pair['predicted']} | {pair['errors']:,} | {pair['share_of_true_class']:.1%} |")
    for pair in review["confused_pairs"]:
        lines += ["", f"### Real: {pair['true']} → predicho: {pair['predicted']}", ""]
        for ex in pair["examples"]:
            lines += [f"- #{ex['complaint_id']} ({ex['date_received']}, confianza {ex['confidence']:.2f}): "
                      f"`{ex['text'].replace('`', chr(39))}`"]
    lines += ["", "## Errores con mayor confianza", ""]
    for ex in review["high_confidence_errors"]:
        lines.append(f"- #{ex['complaint_id']} real **{ex['true']}**, predicho **{ex['predicted']}** "
                     f"(confianza {ex['confidence']:.2f}): `{ex['text'].replace('`', chr(39))}`")
    lines += ["", "## Aciertos de referencia", ""]
    for ex in review["correct_examples"]:
        lines.append(f"- #{ex['complaint_id']} **{ex['true']}** (confianza {ex['confidence']:.2f}): "
                     f"`{ex['text'].replace('`', chr(39))}`")
    contradictory = review["contradictory_label_groups"]
    lines += ["", "## Textos idénticos con productos distintos", "",
              f"{contradictory['groups_total']:,} textos aparecen en reclamos con más de un producto: ningún "
              "modelo puede acertar todos. Los de mayor repetición:", ""]
    for ex in contradictory["examples"]:
        products = ", ".join(f"{k} ({v})" for k, v in ex["products"].items())
        lines.append(f"- {ex['reclamos']} reclamos — {products}: `{ex['text'].replace('`', chr(39))}`")
    return "\n".join(lines) + "\n"


def write_review(review, json_path, markdown_path):
    """Escribe el JSON y el Markdown; conserva las observaciones manuales bajo el marcador."""
    json_path, markdown_path = Path(json_path), Path(markdown_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(review, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    manual = MANUAL_PLACEHOLDER
    if markdown_path.exists():
        previous = markdown_path.read_text(encoding="utf-8")
        if MANUAL_MARKER in previous:
            manual = previous.split(MANUAL_MARKER, 1)[1]
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(review_markdown(review) + "\n" + MANUAL_MARKER + manual, encoding="utf-8")
