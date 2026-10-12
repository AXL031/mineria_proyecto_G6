"""Evalúa reglas descriptivas predefinidas en las particiones del modelo Silver."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pyarrow.parquet as pq

from bankshield.features.fraud_patterns import RULES, rule_masks, summarize_rules
from bankshield.ingestion.paysim_profile import _sha256
from bankshield.services.fraud import FraudScorer


def analyze(input_path, model_path, output_path, markdown_path=None):
    scorer = FraudScorer(model_path)
    training = scorer.metadata.get("training_input", {})
    if training.get("format") != "silver" or training.get("sha256", "").lower() != _sha256(input_path).lower():
        raise ValueError("Se requiere el Silver exacto registrado en este modelo")
    config = scorer.metadata["config"]
    totals = {name: {"rows": 0, "fraud": 0, "counts": {key: [0, 0] for key in RULES}}
              for name in ("train", "validation", "test")}
    for batch in pq.ParquetFile(input_path).iter_batches(
            batch_size=100_000, columns=["step", "type", "amount", "oldbalanceOrg", "isFraud"]):
        frame = batch.to_pandas()
        steps = frame["step"]
        masks = {"train": steps <= config["train_end_step"],
                 "validation": (steps > config["train_end_step"]) & (steps <= config["validation_end_step"]),
                 "test": steps > config["validation_end_step"]}
        if not frame["isFraud"].isin([0, 1]).all():
            raise ValueError("Etiqueta no binaria")
        for name, mask in masks.items():
            part = frame.loc[mask]
            if part.empty:
                continue
            labels = part["isFraud"].to_numpy(dtype=bool)
            total = totals[name]
            total["rows"] += len(part)
            total["fraud"] += int(labels.sum())
            for key, selected in rule_masks(part).items():
                total["counts"][key][0] += int(selected.sum())
                total["counts"][key][1] += int(np.sum(selected & labels))
    for name, total in totals.items():
        expected = scorer.metadata["partitions"][name]
        if total["rows"] != expected["rows"] or total["fraud"] != expected["fraud"]:
            raise ValueError("Recuentos distintos de las particiones embebidas")
    report = {"schema_version": 1, "model_id": scorer.model_id, "training_input": training,
              "simulation_data": True, "method": "fixed_antecedents_descriptive_association",
              "rules_selected_using_test": False,
              "partitions": {name: summarize_rules(**total) for name, total in totals.items()},
              "limitations": ["retrospective_associations_not_causal", "not_model_attributions",
                              "not_a_calibrated_prediction", "rules_not_selected_or_tuned_on_test",
                              "exact_balance_equality_in_synthetic_data", "overlapping_rules_not_additive"]}
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    if markdown_path:
        lines = ["# Patrones descriptivos de fraude — Cueva", "",
                 "Reglas predefinidas sobre tipo, monto y saldo anterior. No modifican el modelo ni su umbral.",
                 "No se eligieron reglas por sus resultados en prueba. Son asociaciones retrospectivas, no causas ni atribuciones.",
                 "", f"Modelo SHA-256: `{scorer.model_id}`.",
                 f"Silver SHA-256: `{training['sha256']}`.", "",
                 "Soporte = operaciones que cumplen la regla / operaciones de la partición; confianza = fraudes entre las coincidencias; lift = confianza / prevalencia; cobertura = fraudes coincidentes / fraudes de la partición.",
                 "Las reglas se solapan: sus conteos y coberturas no se suman. Sin coincidencias, confianza/lift se muestran como N/D."]
        for name, partition in report["partitions"].items():
            lines += ["", f"## {name}", "", f"Filas: {partition['rows']:,}; fraudes: {partition['fraud']:,}; prevalencia: {partition['prevalence']:.6%}.",
                      "", "| Regla | Coincidencias | Fraudes | Soporte | Confianza | Lift | Cobertura |",
                      "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
            for row in partition["rules"]:
                confidence = f"{row['confidence']:.4%}" if row["confidence"] is not None else "N/D"
                lift = f"{row['lift']:.2f}" if row["lift"] is not None else "N/D"
                coverage = f"{row['fraud_coverage']:.4%}" if row["fraud_coverage"] is not None else "N/D"
                lines.append(f"| {row['description']} | {row['matches']:,} | {row['fraud_matches']:,} | {row['support']:.4%} | {confidence} | {lift} | {coverage} |")
        lines += ["", "## Límites", "", "PaySim es una simulación. La igualdad exacta de saldos no debe extrapolarse a otros sistemas o monedas. Las reglas no sustituyen el clasificador y no garantizan fraude en una operación individual. Revisar reglas nuevas con entrenamiento/validación y una evaluación nueva independiente."]
        Path(markdown_path).parent.mkdir(parents=True, exist_ok=True)
        Path(markdown_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/silver/transactions/transactions.parquet")
    parser.add_argument("--model", type=Path, default=ROOT / "artifacts/models/fraud-silver/model.joblib")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/models/fraud-silver/patterns.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "docs/fraude/patrones-descriptivos.md")
    args = parser.parse_args()
    try:
        report = analyze(args.input, args.model, args.output, args.markdown)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(f"Patrones de {sum(p['rows'] for p in report['partitions'].values()):,} filas: {args.output}")


if __name__ == "__main__":
    main()
