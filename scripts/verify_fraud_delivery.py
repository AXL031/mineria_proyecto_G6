"""Comprueba el modelo real y la página contra una API HTTP local temporal."""

import argparse
import json
import os
from pathlib import Path
import socket
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import requests
from streamlit.testing.v1 import AppTest
import uvicorn


def verify(model, output):
    previous = {key: os.environ.get(key) for key in ("BANKSHIELD_FRAUD_MODEL", "BANKSHIELD_API_URL")}
    os.environ["BANKSHIELD_FRAUD_MODEL"] = str(Path(model).resolve())
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    url = f"http://127.0.0.1:{sock.getsockname()[1]}"
    os.environ["BANKSHIELD_API_URL"] = url
    server = uvicorn.Server(uvicorn.Config("api.main:app", log_level="error", lifespan="off"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    report = {"model": str(Path(model).resolve()), "transport": "real_loopback_http",
              "checks": {}, "predictions": []}
    try:
        thread.start()
        deadline = time.monotonic() + 15
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError("La API no inició")
            time.sleep(0.05)
        def check(name, condition):
            report["checks"][name] = bool(condition)
            if not condition:
                raise ValueError(f"Falló la comprobación {name}")
        evaluation = requests.get(f"{url}/api/fraud/model", timeout=20)
        check("evaluation_available", evaluation.status_code == 200)
        metadata = evaluation.json()
        report["model_id"] = metadata["model_id"]
        patterns = requests.get(f"{url}/api/fraud/patterns", timeout=20)
        check("patterns_match_model", patterns.status_code == 200 and patterns.json()["model_id"] == report["model_id"])
        page = AppTest.from_file(str(ROOT / "dashboard/pages/01_fraude.py"), default_timeout=30).run()
        check("page_initializes", not page.exception)
        for amount, balance, expected_alert in ((1000.0, 500.0, False), (36942.13, 36942.13, True)):
            transaction = {"type": "TRANSFER", "amount": amount, "oldbalanceOrg": balance}
            response = requests.post(f"{url}/api/fraud/predict", json=transaction, timeout=20)
            check(f"prediction_{expected_alert}", response.status_code == 200 and response.json()["alert"] is expected_alert)
            result = response.json()
            report["predictions"].append({"input": transaction, **result})
            page.number_input[0].set_value(amount)
            page.number_input[1].set_value(balance)
            page.button[0].click().run()
            check(f"page_matches_prediction_{expected_alert}", not page.exception
                  and page.session_state["fraud_prediction"]["result"] == result)
        page.button[1].click().run()
        check("metrics_preserve_prediction", not page.exception and len(page.metric) == 3 and len(page.dataframe) == 1)
        page.button[2].click().run()
        check("page_displays_patterns", not page.exception and len(page.dataframe) == 3)
        invalid = requests.post(f"{url}/api/fraud/predict", json={"type": "TRANSFER", "amount": -1, "oldbalanceOrg": 0}, timeout=20)
        check("invalid_input_rejected", invalid.status_code == 422)
        os.environ["BANKSHIELD_FRAUD_MODEL"] = str(Path(model).with_name("nonexistent-verification-model.joblib"))
        missing = requests.post(f"{url}/api/fraud/predict", json=transaction, timeout=20)
        check("missing_model_returns_503", missing.status_code == 503)
        page.button[0].click().run()
        check("missing_model_clears_page_prediction", not page.exception and len(page.error) == 1 and not page.metric)
        check("health_survives_missing_model", requests.get(url, timeout=20).status_code == 200)
        server.should_exit = True
        thread.join(timeout=10)
        page.button[0].click().run()
        check("offline_api_shows_error", not page.exception and len(page.error) == 1 and not page.metric)
        report["status"] = "passed"
    finally:
        server.should_exit = True
        if thread.is_alive():
            thread.join(timeout=10)
        sock.close()
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=ROOT / "artifacts/models/fraud-silver/model.joblib")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/reports/fraud-delivery-check.json")
    args = parser.parse_args()
    result = verify(args.model, args.output)
    print(f"Entrega verificada: {len(result['checks'])} comprobaciones | {args.output}")


if __name__ == "__main__":
    main()
