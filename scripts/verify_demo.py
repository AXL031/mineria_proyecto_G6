"""Verifica perfiles current/full con artefactos reales, HTTP y páginas."""

import argparse
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone

import requests
import math

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from bankshield.analytics_contract import provenance
NARRATIVE = "My credit report contains an account that does not belong to me. I disputed the incorrect information with the credit bureau but it has not been removed."
CREDIT = {"person_age": 30, "person_income": 55000.0, "person_home_ownership": "RENT",
          "person_emp_length": 4.0, "loan_intent": "PERSONAL", "loan_amnt": 10000.0,
          "cb_person_default_on_file": "N", "cb_person_cred_hist_length": 5}


def verify(url, output, pages=True, profile="full", include_model_monitoring=False):
    report = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "api_url": url,
              "schema_version": 1, "profile": profile,
              "transport": "real_loopback_http", "checks": {}, "examples": {},
              "optional": {"model_performance_monitoring": "required" if include_model_monitoring else "skipped_optional"},
              **provenance([Path(__file__), ROOT / "api/main.py"])}
    def check(name, condition):
        report["checks"][name] = bool(condition)
        if not condition:
            raise RuntimeError(f"Falló {name}")
    def request(path, payload=None, status=200):
        result = (requests.get(url + path, timeout=120) if payload is None else
                  requests.post(url + path, json=payload, timeout=60))
        check(f"{path} status={status}" + (" POST" if payload is not None else ""), result.status_code == status)
        return result.json()
    try:
        health = request("/")
        expected_modules = {"fraud", "credit", "graphs", "forecast", "segments", "complaints"}
        if profile == "full":
            expected_modules.add("regression")
        check("expected_modules", expected_modules.issubset(health["modules"]))
        if profile == "full":
            check("expected_capabilities", {"association_mining", "graph_comparison", "numeric_regression"}.issubset(health.get("capabilities", [])))
            regression = request("/api/regression/model")
            amount = request("/api/regression/predict", {"type": "TRANSFER", "oldbalanceOrg": 500.0})
            check("regression_finite_nonnegative", math.isfinite(amount["prediction"]) and amount["prediction"] >= 0)
            check("regression_model_identity", amount["model_id"] == regression["model_id"])
            examples = request("/api/regression/examples?limit=20&offset=0")
            check("regression_example_identity", examples["model_id"] == regression["model_id"] and all(row["model_id"] == regression["model_id"] for row in examples["rows"]))
            check("regression_nonempty_test_examples", bool(examples["rows"]))
            request("/api/regression/predict", {"type": "TRANSFER", "oldbalanceOrg": -1.0}, 422)
            request("/api/regression/predict", {"type": "TRANSFER", "oldbalanceOrg": 500.0, "amount": 10.0}, 422)
            request("/api/regression/examples?limit=0", status=422)
            report["examples"]["regression"] = amount
            associations = request("/api/fraud/associations?partition=test&limit=20&offset=0")
            validation = request("/api/fraud/associations?partition=validation&limit=20&offset=0")
            check("associations_same_analysis", associations["analysis_id"] == validation["analysis_id"])
            check("associations_validation_selection", associations["selection_partition"] == "validation")
            request("/api/fraud/associations?partition=invalid", status=422)
            request("/api/fraud/associations?offset=100000")
            report["examples"]["association_analysis_id"] = associations["analysis_id"]
            graph_comparison = request("/api/graphs/evaluation?limit=10000")
            check("graph_same_budget", all(item["network_indicators"]["selected_accounts"] == item["volume_reference"]["selected_accounts"] == item["k"] for item in graph_comparison["comparisons"]))
            check("graph_bounded_universe", graph_comparison["universe_size"] >= max(item["k"] for item in graph_comparison["comparisons"]))
            request("/api/graphs/evaluation?limit=11000", status=503)
            report["examples"]["graph_analysis_id"] = graph_comparison["analysis_id"]
        if include_model_monitoring:
            runs = request("/api/monitoring/runs")
            check("model_monitoring_has_real_run", bool(runs["runs"]))
            request("/api/monitoring/runs/" + runs["runs"][0]["run_id"])
        fraud_model = request("/api/fraud/model")
        request("/api/fraud/patterns")
        fraud_inputs = [{"type": "TRANSFER", "amount": 1000.0, "oldbalanceOrg": 500.0},
                        {"type": "TRANSFER", "amount": 36942.13, "oldbalanceOrg": 36942.13}]
        report["examples"]["fraud"] = []
        for i, payload in enumerate(fraud_inputs):
            result = request("/api/fraud/predict", payload)
            check(f"fraud_expected_alert_{i}", result["alert"] is bool(i))
            check(f"fraud_model_identity_{i}", result["model_id"] == fraud_model["model_id"])
            report["examples"]["fraud"].append({"input": payload, "result": result})
        request("/api/fraud/predict", {**fraud_inputs[0], "amount": -1.0}, 422)
        request("/api/credit/model")
        report["examples"]["credit"] = {"input": CREDIT, "result": request("/api/credit/predict", CREDIT)}
        request("/api/graphs/summary?limit=10000")
        ranked = request("/api/graphs/top?limit=10000&top_n=3")
        account = ranked["results"][0]["account"]
        report["examples"]["graph_account"] = account
        request(f"/api/graphs/account/{account}?limit=10000")
        subgraph = request(f"/api/graphs/subgraph/{account}?limit=10000&depth=1")
        check("bounded_subgraph", len(subgraph["data"]["nodes"]) <= 500)
        request("/api/graphs/patterns/suspicious?limit=10000")
        for target in ("transaction_count", "total_amount"):
            forecast = request(f"/api/forecast/projection?target={target}&horizon=24")
            check(f"forecast_24_{target}", len(forecast["forecast"]) == 24)
        monitoring = request("/api/forecast/monitoring")
        report["examples"]["monitoring"] = {"status": monitoring["status"], "alert_count": monitoring["alert_count"]}
        segments = request("/api/segments/summary")
        check("segments_complete_accounts", segments["total_accounts"] == 146629)
        segment = int(segments["profiles"][0]["segment"])
        accounts = request(f"/api/segments/{segment}/accounts?limit=5")
        segment_account = accounts["accounts"][0]["account"]
        request(f"/api/segments/{segment}/account/{segment_account}")
        report["examples"]["segments"] = {"segment": segment, "account": segment_account}
        request("/api/segments/9999/accounts", status=404)
        model = request("/api/complaints/model")
        summary = request("/api/complaints/summary")
        check("complaints_complete_rows", summary["total_complaints"] == 555957)
        check("complaints_narrative_coverage", summary["with_narrative"] == 66806)
        result = request("/api/complaints/predict", {"narrative": NARRATIVE})
        check("complaints_model_identity", result["model_id"] == model["model_id"])
        report["examples"]["complaints"] = {"input": NARRATIVE, "result": result}
        request("/api/complaints/examples")
        request("/api/complaints/predict", {"narrative": "short text here"}, 422)
        if pages:
            from streamlit.testing.v1 import AppTest
            os.environ["BANKSHIELD_API_URL"] = url
            os.environ["BANKSHIELD_GRAPH_SAMPLE"] = "10000"
            page_names = ["01_fraude.py", "02_credito.py", "03_redes.py", "04_pronosticos.py", "05_reclamos.py", "06_segmentos.py"]
            if profile == "full":
                page_names.append("07_regresion.py")
            home = AppTest.from_file(str(ROOT / "dashboard/app.py"), default_timeout=120).run()
            check("homepage_initializes", not home.exception)
            for page_name in page_names:
                page = AppTest.from_file(str(ROOT / "dashboard/pages" / page_name), default_timeout=120).run()
                check(f"page_{page_name}_initializes", not page.exception and not page.error)
                def click(label):
                    next(button for button in page.button if button.label == label).click().run()
                if page_name == "01_fraude.py":
                    for label in ("Evaluar transacción", "Consultar métricas y versión", "Consultar patrones históricos"):
                        click(label)
                    if profile == "full":
                        click("Consultar asociaciones descubiertas")
                elif page_name == "02_credito.py":
                    click("Evaluar solicitud")
                    click("Consultar métricas y versión")
                elif page_name == "04_pronosticos.py":
                    click("Generar proyección")
                    click("Consultar monitoreo")
                elif page_name == "05_reclamos.py":
                    for label in ("Clasificar reclamo", "Consultar tendencias", "Consultar evaluación", "Consultar ejemplos de prueba"):
                        click(label)
                elif page_name == "07_regresion.py":
                    for label in ("Estimar monto", "Consultar evaluación", "Consultar ejemplos"):
                        click(label)
                check(f"page_{page_name}_interactions", not page.exception and not page.error)
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        raise
    finally:
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print(f"Demo verificada: {len(report['checks'])} comprobaciones. Evidencia: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/reports/demo/delivery-check.json")
    parser.add_argument("--skip-pages", action="store_true")
    parser.add_argument("--profile", choices=("current", "full"), default="full")
    parser.add_argument("--include-model-monitoring", action="store_true", help="Exigir la ampliación P2 de historial de desempeño")
    args = parser.parse_args()
    verify(args.api_url.rstrip("/"), args.output, not args.skip_pages, args.profile, args.include_model_monitoring)
