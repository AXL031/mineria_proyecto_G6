"""Verifica GER-03 con artefactos locales, HTTP real y AppTest del panel temporal."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(api_url, output, pages=True):
    report = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "transport": "real_loopback_http",
        "api_url": api_url,
        "human_acceptance": "pending",
        "visual_review": "pending_browser_review",
        "checks": {},
        "versions": {"python": platform.python_version()},
    }

    def check(name, condition):
        report["checks"][name] = bool(condition)
        if not condition:
            raise RuntimeError(f"Falló {name}")

    def get(path, params=None, expected=200):
        result = requests.get(api_url + path, params=params, timeout=30)
        check(f"HTTP {result.request.path_url} = {expected}", result.status_code == expected)
        return result.json()

    try:
        for package in ("numpy", "pandas", "pyarrow", "statsmodels", "fastapi", "streamlit"):
            report["versions"][package] = version(package)
        report["platform"] = platform.platform()
        report["commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
        ).strip()
        report["tree_dirty"] = bool(subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True,
        ).strip())
        report["code_sha256"] = {
            path: sha256(ROOT / path) for path in (
                "scripts/verify_forecast_delivery.py", "api/routers/forecast.py",
                "src/bankshield/services/forecast.py", "dashboard/pages/04_pronosticos.py",
                "configs/forecast.json",
            )
        }
        gold_path = ROOT / "data/gold/forecast/transactions_hourly.parquet"
        gold = pd.read_parquet(gold_path)
        gold_sha = sha256(gold_path)
        report["gold"] = {"sha256": gold_sha, "rows": len(gold)}
        check("Gold: steps consecutivos 1–743", gold["step"].tolist() == list(range(1, 744)))
        check("Gold: 6362620 transacciones", int(gold["transaction_count"].sum()) == 6362620)
        check("Gold: sin nulos", not gold.isna().any().any())
        report["experiments"] = {}
        configuration = json.loads((ROOT / "configs/forecast.json").read_text(encoding="utf-8"))
        for filename in ("forecast_baselines.json", "forecast_holt_winters.json"):
            path = ROOT / "artifacts/reports" / filename
            experiment = json.loads(path.read_text(encoding="utf-8"))
            check(f"{filename}: misma huella Gold", experiment["source"]["sha256"] == gold_sha)
            check(f"{filename}: cuatro ventanas", len(experiment["windows"]) == 4)
            check(f"{filename}: sin stress en evaluación", all(
                window["train"]["end_step"] < window["test"]["start_step"]
                and window["test"]["end_step"] <= 718
                for window in experiment["windows"]
            ))
            check(f"{filename}: ventanas de la configuración", all(
                window["train"]["start_step"] == expected["train_start_step"]
                and window["train"]["end_step"] == expected["train_end_step"]
                and window["test"]["start_step"] == expected["test_start_step"]
                and window["test"]["end_step"] == expected["test_end_step"]
                for window, expected in zip(experiment["windows"], configuration["evaluation"]["backtest_windows"])
            ))
            selected = {}
            for target, models in experiment["aggregates"].items():
                winner = min(models, key=lambda name: models[name]["mae"])
                check(f"{filename}/{target}: Naive gana MAE", winner == "naive")
                selected[target] = {"selected": winner, "metrics": models}
            report["experiments"][filename] = {
                "sha256": sha256(path), "versions": experiment["versions"],
                "generated_at_utc": experiment["generated_at_utc"],
                "comparison": selected,
            }

        check("Integración central: forecast registrado", "forecast" in get("/")["modules"])
        paths = get("/openapi.json")["paths"]
        check("OpenAPI: endpoints temporales", all(
            "/api/forecast/" + endpoint in paths for endpoint in ("projection", "monitoring")
        ))
        report["projections"] = []
        for target in ("transaction_count", "total_amount"):
            for horizon in (1, 24, 72, 168):
                body = get("/api/forecast/projection", {"target": target, "horizon": horizon, "history_steps": 24})
                points = body["forecast"]
                check(f"{target}/{horizon}: modelo y último valor", body["selected_model"] == "naive"
                      and body["last_observed_step"] == 743
                      and body["last_observed_value"] == float(gold[target].iloc[-1]))
                check(f"{target}/{horizon}: pasos y pronóstico", [p["step"] for p in points] == list(range(744, 744 + horizon))
                      and all(p["prediction"] == body["last_observed_value"] for p in points))
                check(f"{target}/{horizon}: límites e historia", len(body["history"]) == 24
                      and all(0 <= p["lower"] <= p["prediction"] <= p["upper"] for p in points)
                      and not body["uncertainty"]["calibrated"] and body["simulation_data"])
                report["projections"].append({
                    "target": target, "horizon": horizon, "first": points[0], "last": points[-1],
                })
        for params in ({"target": "fraud_count"}, {"horizon": 0}, {"horizon": 169},
                       {"horizon": "abc"}, {"history_steps": 23}, {"history_steps": 719}):
            get("/api/forecast/projection", params, expected=422)
        monitoring = get("/api/forecast/monitoring")
        local = json.loads((ROOT / "artifacts/reports/forecast_monitoring.json").read_text(encoding="utf-8"))
        check("Monitoreo: mismo artefacto local", all(monitoring[key] == value for key, value in local.items()
              if key in monitoring))
        check("Monitoreo: ventanas y seis alertas", monitoring["reference"]["start_step"] == 694
              and monitoring["reference"]["end_step"] == 718
              and monitoring["observed"]["start_step"] == 719
              and monitoring["observed"]["end_step"] == 743
              and monitoring["alert_count"] == 6 and monitoring["status"] == "change_detected")
        report["monitoring"] = {"sha256": sha256(ROOT / "artifacts/reports/forecast_monitoring.json"),
                                "status": monitoring["status"], "alert_count": monitoring["alert_count"]}

        # Contraste independiente de los cortes D1 sobre Silver real, sin entrenar modelos.
        counts = np.zeros(4, dtype="int64")
        fraud = np.zeros(4, dtype="int64")
        for batch in pq.ParquetFile(ROOT / "data/silver/transactions/transactions.parquet").iter_batches(
                columns=["step", "isFraud"], batch_size=500000):
            steps = batch.column(0).to_numpy()
            labels = batch.column(1).to_numpy()
            check("Silver: steps dentro de 1–743", bool(((steps >= 1) & (steps <= 743)).all()))
            partition = np.searchsorted([323, 378, 718], steps, side="left")
            counts += np.bincount(partition, minlength=4)
            fraud += np.bincount(partition, weights=labels, minlength=4).astype("int64")
        check("Cortes D1: recuentos Silver", counts.tolist() == [4463587, 980416, 918321, 296])
        check("Cortes D1: fraudes Silver", fraud.tolist() == [3643, 564, 3710, 296])
        report["partition_review"] = {
            "scope": "Silver real; no sustituye la validación del Parquet D1",
            "rows": dict(zip(("train", "validation", "test", "stress"), counts.tolist())),
            "fraud": dict(zip(("train", "validation", "test", "stress"), fraud.tolist())),
            "d1_present": (ROOT / "data/gold/analytics/transactions.parquet").is_file(),
        }
        if pages:
            from streamlit.testing.v1 import AppTest

            previous_url = os.environ.get("BANKSHIELD_API_URL")
            os.environ["BANKSHIELD_API_URL"] = api_url
            try:
                page = AppTest.from_file(str(ROOT / "dashboard/pages/04_pronosticos.py"), default_timeout=60).run()
                check("Página: carga", not page.exception and not page.error)
                for target in ("Cantidad de transacciones", "Monto total"):
                    page.selectbox[0].select(target).run()
                    for horizon in (1, 24, 72):
                        page.slider[0].set_value(horizon).run()
                        page.button[0].click().run()
                        check(f"Página: {target}/{horizon}", not page.exception and not page.error
                              and page.metric[2].value == "naive")
                page.button[1].click().run()
                check("Página: monitoreo real", not page.exception and not page.error
                      and any("6 indicadores" in item.value for item in page.warning))
                report["page_transport"] = "AppTest con HTTP real; no es revisión visual de navegador"
            finally:
                if previous_url is None:
                    os.environ.pop("BANKSHIELD_API_URL", None)
                else:
                    os.environ["BANKSHIELD_API_URL"] = previous_url
        else:
            report["page_transport"] = "skipped"
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        raise
    finally:
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print(f"GER-03: {len(report['checks'])} comprobaciones aprobadas. Evidencia: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/reports/ger-03/verification.json")
    parser.add_argument("--skip-pages", action="store_true")
    args = parser.parse_args()
    verify(args.api_url.rstrip("/"), args.output, not args.skip_pages)
