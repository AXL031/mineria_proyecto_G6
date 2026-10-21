"""Ensaya los seis módulos con artefactos reales, HTTP local y sus páginas."""

import argparse
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
NARRATIVE = "My credit report contains an account that does not belong to me. I disputed the incorrect information with the credit bureau but it has not been removed."
CREDIT = {"person_age": 30, "person_income": 55000.0, "person_home_ownership": "RENT",
          "person_emp_length": 4.0, "loan_intent": "PERSONAL", "loan_amnt": 10000.0,
          "cb_person_default_on_file": "N", "cb_person_cred_hist_length": 5}


def verify(url, output, pages=True):
    report = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "api_url": url,
              "transport": "real_loopback_http", "checks": {}, "examples": {}}
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
        check("six_modules", set(health["modules"]) == {"fraud", "credit", "graphs", "forecast", "segments", "complaints"})
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
            for page_name in ("01_fraude.py", "02_credito.py", "03_redes.py", "04_pronosticos.py", "05_reclamos.py", "06_segmentos.py"):
                page = AppTest.from_file(str(ROOT / "dashboard/pages" / page_name), default_timeout=120).run()
                check(f"page_{page_name}_initializes", not page.exception and not page.error)
                if page_name == "01_fraude.py":
                    page.button[0].click().run()
                    page.button[1].click().run()
                    page.button[2].click().run()
                elif page_name == "02_credito.py":
                    page.button[0].click().run()
                    page.button[1].click().run()
                elif page_name == "04_pronosticos.py":
                    page.button[0].click().run()
                    page.button[1].click().run()
                elif page_name == "05_reclamos.py":
                    for i in range(4):
                        page.button[i].click().run()
                check(f"page_{page_name}_interactions", not page.exception and not page.error)
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        raise
    finally:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print(f"Demo verificada: {len(report['checks'])} comprobaciones. Evidencia: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/reports/demo/delivery-check.json")
    parser.add_argument("--skip-pages", action="store_true")
    args = parser.parse_args()
    verify(args.api_url.rstrip("/"), args.output, not args.skip_pages)
