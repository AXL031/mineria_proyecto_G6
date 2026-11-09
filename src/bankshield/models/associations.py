"""Apriori acotado: poda en train, selección en validation y evaluación congelada."""

from collections import Counter
from itertools import combinations
from datetime import datetime, timezone
import time
from pathlib import Path

import numpy as np

from bankshield.analytics_contract import digest, provenance, write_json_atomic
from bankshield.features.association_transactions import item_masks, antecedent_mask

PARTITIONS = ("train", "validation", "test", "stress")
LIMITATIONS = [
    "Datos simulados PaySim; las asociaciones no prueban causalidad ni cambian el clasificador.",
    "Selección en validation; test y stress no seleccionan ni reordenan reglas.",
    "Las reglas se solapan: no se suman sus coberturas.",
    "Los patrones de saldo pueden reflejar mecanismos del simulador; no extrapolar a fraude real.",
]


def validate_config(config):
    for name in ("min_support", "min_confidence"):
        value = config[name]
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not 0 < value <= 1:
            raise ValueError(f"{name} debe estar en (0,1]")
    if isinstance(config["min_lift"], bool) or not np.isfinite(config["min_lift"]) or config["min_lift"] < 0:
        raise ValueError("min_lift debe ser finito y no negativo")
    for name in ("min_antecedent_count", "max_rules", "max_antecedent_items", "max_candidates"):
        if isinstance(config[name], bool) or not isinstance(config[name], int) or config[name] < 1:
            raise ValueError(f"{name} debe ser entero positivo")
    if config["max_antecedent_items"] > 3:
        raise ValueError("El protocolo v1 admite hasta tres ítems")


def metrics(n, positives, matches, joint):
    confidence = joint / matches if matches else None
    prevalence = positives / n if n else None
    return {"n": n, "positives": positives, "antecedent_count": matches, "joint_count": joint,
            "antecedent_support": matches / n if n else None, "support": joint / n if n else None,
            "confidence": confidence,
            "lift": confidence / prevalence if confidence is not None and prevalence else None,
            "fraud_coverage": joint / positives if positives else None,
            "undefined_reasons": {key: reason for key, reason, undefined in (
                ("support", "empty_partition", not n), ("antecedent_support", "empty_partition", not n),
                ("confidence", "no_matches", not matches),
                ("lift", "no_matches_or_no_positives", not matches or not positives),
                ("fraud_coverage", "no_positives", not positives)) if undefined}}


def count_candidates(dataset, candidates, partition):
    counts = {candidate: [0, 0] for candidate in candidates}
    n = positives = 0
    for frame in dataset.batches(partition):
        masks = item_masks(frame)
        y = frame.isFraud.to_numpy(dtype=bool)
        n += len(frame)
        positives += int(y.sum())
        for candidate in candidates:
            selected = antecedent_mask(masks, candidate, len(frame))
            counts[candidate][0] += int(selected.sum())
            counts[candidate][1] += int((selected & y).sum())
    return {candidate: metrics(n, positives, *values) for candidate, values in counts.items()}


def qualifies(value, config):
    return (value["support"] is not None and value["support"] >= config["min_support"]
            and value["antecedent_count"] >= config["min_antecedent_count"]
            and value["confidence"] is not None and value["confidence"] >= config["min_confidence"]
            and value["lift"] is not None and value["lift"] >= config["min_lift"])


def join_candidates(previous, size):
    previous = set(previous)
    candidates = set()
    ordered = sorted(previous)
    for i, left in enumerate(ordered):
        for right in ordered[i + 1:]:
            candidate = tuple(sorted(set(left) | set(right)))
            if len(candidate) != size or len({item.split("=", 1)[0] for item in candidate}) != size:
                continue
            if all(tuple(subset) in previous for subset in combinations(candidate, size - 1)):
                candidates.add(candidate)
    return sorted(candidates)


def report_identity(report):
    return digest({key: report[key] for key in ("schema_version", "method", "dataset", "config", "rules", "evaluation")})


def mine(dataset, config):
    validate_config(config)
    started = time.perf_counter()
    items = set()
    for frame in dataset.batches("train"):
        items.update(item_masks(frame))
    candidates = [(item,) for item in sorted(items)]
    total_candidates = 0
    passed_train = {}
    levels = []
    for size in range(1, config["max_antecedent_items"] + 1):
        total_candidates += len(candidates)
        if total_candidates > config["max_candidates"]:
            raise ValueError("Se excedió max_candidates; reduzca ítems/profundidad, sin truncar candidatos")
        if not candidates:
            break
        counted = count_candidates(dataset, candidates, "train")
        frequent = [candidate for candidate in candidates if counted[candidate]["support"] is not None
                    and counted[candidate]["support"] >= config["min_support"]]
        passed_train.update({candidate: value for candidate, value in counted.items() if qualifies(value, config)})
        levels.append({"size": size, "candidates": len(candidates), "frequent_joint": len(frequent)})
        candidates = join_candidates(frequent, size + 1)
    validation = count_candidates(dataset, list(passed_train), "validation")
    selected = sorted((candidate for candidate, value in validation.items() if qualifies(value, config)),
                      key=lambda candidate: (-validation[candidate]["lift"], -validation[candidate]["support"], candidate))[:config["max_rules"]]
    evaluations = {"train": {candidate: passed_train[candidate] for candidate in selected},
                   "validation": {candidate: validation[candidate] for candidate in selected}}
    for name in ("test", "stress"):
        evaluations[name] = count_candidates(dataset, selected, name)
    union = {}
    for name in PARTITIONS:
        n = positives = matches = joint = 0
        for frame in dataset.batches(name):
            masks = item_masks(frame)
            mask = np.zeros(len(frame), dtype=bool)
            for candidate in selected:
                mask |= antecedent_mask(masks, candidate, len(frame))
            y = frame.isFraud.to_numpy(dtype=bool)
            n += len(frame); positives += int(y.sum()); matches += int(mask.sum()); joint += int((mask & y).sum())
        union[name] = metrics(n, positives, matches, joint)
    rules = [{"id": digest({"antecedent": candidate, "consequent": "isFraud=true"}),
              "antecedent": list(candidate), "consequent": "isFraud=true",
              "partitions": {name: evaluations[name][candidate] for name in PARTITIONS}} for candidate in selected]
    report = {"schema_version": 1, "method": "apriori_bounded", "simulation_data": True,
              "selection_partition": "validation", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "dataset": dataset.identity(), "config": {key: config[key] for key in (
                  "min_support", "min_antecedent_count", "min_confidence", "min_lift", "max_rules",
                  "max_antecedent_items", "max_candidates")},
              "rules": rules, "evaluation": union, "search": {"levels": levels,
                  "total_candidates": total_candidates, "qualified_train": len(passed_train), "selected": len(rules)},
              "diagnostic": "Reglas congeladas por validation." if rules else "Ninguna regla cumple los umbrales fijados; no se relajaron.",
              "duration_seconds": time.perf_counter() - started, "limitations": LIMITATIONS,
              **provenance([Path(__file__), Path(__file__).parents[1] / "analytics_contract.py",
                            Path(__file__).parents[1] / "features/association_transactions.py"])}
    report["analysis_id"] = report_identity(report)
    return report


def render_markdown(report):
    lines = ["# Asociaciones descubiertas automáticamente", "",
             f"Análisis `{report['analysis_id']}`; método Apriori acotado; selección en validation.",
             f"Corrida UTC: {report['generated_at_utc']}; duración: {report['duration_seconds']:.2f} s.",
             f"D1 SHA-256: `{report['dataset']['dataset_sha256']}`.",
             f"Candidatos: {report['search']['total_candidates']}; reglas seleccionadas: {len(report['rules'])}.",
             "", report["diagnostic"], "",
             "Soporte = coincidencias conjuntas de antecedente y fraude / filas. Se distingue del soporte del antecedente.", "",
             "| Partición | Filas | Fraudes | Coincidencias de la unión | Fraudes cubiertos | Cobertura |",
             "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for name, value in report["evaluation"].items():
        coverage = "N/D" if value["fraud_coverage"] is None else f"{value['fraud_coverage']:.4%}"
        lines.append(f"| {name} | {value['n']} | {value['positives']} | {value['antecedent_count']} | {value['joint_count']} | {coverage} |")
    lines += ["", "| Regla seleccionada | Confianza validation | Lift validation | Confianza test | Lift test |",
              "| --- | ---: | ---: | ---: | ---: |"]
    def fmt(value):
        return "N/D" if value is None else f"{value:.6f}"
    for rule in report["rules"]:
        v, t = rule["partitions"]["validation"], rule["partitions"]["test"]
        lines.append(f"| {' y '.join(rule['antecedent'])} → fraude | {fmt(v['confidence'])} | {fmt(v['lift'])} | {fmt(t['confidence'])} | {fmt(t['lift'])} |")
    lines += ["", "## Configuración y procedencia", "", "```json", __import__('json').dumps(
        {key: report[key] for key in ("config", "dataset", "versions", "git", "code_sha256")}, indent=2), "```", "",
              "## Limitaciones", "", *["- " + value for value in LIMITATIONS], ""]
    return "\n".join(lines)
