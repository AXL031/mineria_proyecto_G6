"""Segmenta cuentas de destino reincidentes desde el mart transaccional Gold."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd

from bankshield.features.segments import build_account_features
from bankshield.models.segments import segment_accounts

READ_COLUMNS = ("nameDest", "nameOrig", "type", "amount", "step", "isFraud")


def resolve(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def render_markdown(report: dict) -> str:
    metrics = report["metrics"]
    profiles = report["profiles"]
    baseline = report["baseline_profiles"]
    lines = [
        "# Segmentación de cuentas de destino reincidentes",
        "",
        "Reporte generado por `scripts/segment_transactions.py`.",
        "",
        "## Universo y métodos",
        "",
        f"- Cuentas reincidentes (>= {report['min_transactions']} transacciones recibidas): "
        f"**{report['total_accounts']:,}**.",
        f"- Línea base: cortes por cuantiles de actividad (`n_received`).",
        f"- Método principal: KMeans sobre variables estandarizadas; k = "
        f"**{metrics['chosen_k']}** elegido por silueta.",
        "",
        "## Selección de k",
        "",
        "| k | Silueta (muestra) |",
        "| ---: | ---: |",
    ]
    lines += [
        f"| {k} | {score:.4f} |" for k, score in metrics["silhouette_by_k"].items()
    ]
    lines += [
        "",
        f"- Silueta del k elegido: **{metrics['silhouette']:.4f}**.",
        f"- Estabilidad (ARI medio en remuestras): **{metrics['mean_stability_ari']:.4f}** "
        f"({', '.join(f'{value:.3f}' for value in metrics['stability_ari'])}).",
        "",
        "## Perfil de segmentos (KMeans)",
        "",
        "| Segmento | Cuentas | n_received | mean_amount | amount_concentration | "
        "activity_density | share_cash_out | share_cash_in | share_transfer | "
        "fraud_rate |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in profiles.itertuples(index=False):
        lines.append(
            f"| {int(row.segment)} | {int(row.size):,} | {row.n_received:.2f} | "
            f"{row.mean_received_amount:,.0f} | {row.amount_concentration:.3f} | "
            f"{row.activity_density:.2f} | {row.share_cash_out:.3f} | "
            f"{row.share_cash_in:.3f} | {row.share_transfer:.3f} | "
            f"{row.fraud_rate_received:.4f} |"
        )
    lines += [
        "",
        "## Línea base (cuantiles de actividad)",
        "",
        "| Segmento | Cuentas | n_received medio | total_received medio |",
        "| ---: | ---: | ---: | ---: |",
    ]
    for row in baseline.itertuples(index=False):
        lines.append(
            f"| {int(row.segment)} | {int(row.size):,} | {row.mean_n_received:.2f} | "
            f"{row.mean_total_received:,.0f} |"
        )
    lines += [
        "",
        "## Limitaciones",
        "",
        "- Las cuentas que reciben una sola vez (la mayoría del dataset) quedan "
        "fuera de la segmentación; el resultado describe solo cuentas activas.",
        "- PaySim es una simulación; los segmentos no representan clientes reales.",
        "- La silueta se calcula sobre una muestra por costo computacional.",
        "- Las etiquetas de fraude se usan solo para perfilar, no como variable "
        "de agrupamiento.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Segmenta cuentas de destino reincidentes del mart Gold."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "segments.json",
        help="Configuración. Valor predeterminado: configs/segments.json",
    )
    args = parser.parse_args()

    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Error al leer la configuración: {exc}\n")

    input_path = resolve(ROOT, config["input"])
    output_path = resolve(ROOT, config["output"])
    report_json = resolve(ROOT, config["report_json"])
    report_markdown = resolve(ROOT, config["report_markdown"])

    try:
        transactions = pd.read_parquet(input_path, columns=list(READ_COLUMNS))
        features = build_account_features(
            transactions, min_transactions=config.get("min_transactions", 10)
        )
        result = segment_accounts(
            features,
            k_range=range(config.get("k_min", 2), config.get("k_max", 7) + 1),
            seed=config.get("seed", 42),
            sample_size=config.get("silhouette_sample", 10_000),
            stability_iterations=config.get("stability_iterations", 3),
            stability_fraction=config.get("stability_fraction", 0.5),
        )
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")

    labeled = features.assign(segment=result["labels"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    labeled.to_parquet(output_path, index=False)

    report = {
        "schema_version": 1,
        "source": str(input_path.relative_to(ROOT)),
        "min_transactions": config.get("min_transactions", 10),
        "total_accounts": result["total_accounts"],
        "metrics": {
            "chosen_k": result["chosen_k"],
            "silhouette": result["silhouette"],
            "silhouette_by_k": {str(k): v for k, v in result["silhouette_by_k"].items()},
            "mean_stability_ari": result["mean_stability_ari"],
            "stability_ari": result["stability_ari"],
        },
        "profiles": result["profiles"],
        "baseline_profiles": result["baseline_profiles"],
    }

    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(
        json.dumps(
            {
                **report,
                "profiles": result["profiles"].to_dict(orient="records"),
                "baseline_profiles": result["baseline_profiles"].to_dict(orient="records"),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    report_markdown.parent.mkdir(parents=True, exist_ok=True)
    report_markdown.write_text(render_markdown(report), encoding="utf-8")

    print(f"Cuentas reincidentes: {result['total_accounts']:,}")
    print(
        f"k elegido: {result['chosen_k']} | silueta: {result['silhouette']:.4f} | "
        f"estabilidad ARI: {result['mean_stability_ari']:.4f}"
    )
    print(f"Etiquetas: {output_path}")
    print(f"Reporte JSON: {report_json}")
    print(f"Reporte Markdown: {report_markdown}")


if __name__ == "__main__":
    main()
