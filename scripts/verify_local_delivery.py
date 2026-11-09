"""Inicia una demo aislada, verifica HTTP/páginas y detiene solo sus procesos."""

import argparse
from contextlib import ExitStack
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import psutil
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_demo import verify


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def stop_owned(process):
    try:
        parent = psutil.Process(process.pid)
        owned = [*parent.children(recursive=True), parent]
    except psutil.NoSuchProcess:
        return
    for child in reversed(owned):
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(owned, timeout=5)
    for child in alive:
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass
    process.wait(timeout=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/reports/cierre-delivery-check.json")
    parser.add_argument("--skip-pages", action="store_true")
    args = parser.parse_args()
    api_port, panel_port = free_port(), free_port()
    while panel_port == api_port:
        panel_port = free_port()
    url = f"http://127.0.0.1:{api_port}"
    environment = {**os.environ, "BANKSHIELD_API_URL": url, "BANKSHIELD_GRAPH_SAMPLE": "10000",
                   "BANKSHIELD_FRAUD_MODEL": str(ROOT / "artifacts/models/fraud-silver/model.joblib"),
                   "OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2", "MKL_NUM_THREADS": "2"}
    for key in ("BANKSHIELD_REGRESSION_MODEL", "BANKSHIELD_ASSOCIATIONS_REPORT", "BANKSHIELD_GRAPH_COMPARISON"):
        environment.pop(key, None)
    children = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        try:
            for name, command, ready_url in (
                ("api", ["-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", str(api_port)], url + "/"),
                ("panel", ["-m", "streamlit", "run", "dashboard/app.py", "--server.address", "127.0.0.1",
                           "--server.port", str(panel_port), "--server.headless", "true", "--browser.gatherUsageStats", "false"],
                 f"http://127.0.0.1:{panel_port}/_stcore/health")):
                log = stack.enter_context(args.output.with_name(f"cierre-{name}.log").open("w", encoding="utf-8"))
                process = subprocess.Popen([sys.executable, *command], cwd=ROOT, env=environment,
                                           stdout=log, stderr=subprocess.STDOUT,
                                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                children.append(process)
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError(f"{name} terminó antes de estar disponible; consultar su log")
                    try:
                        if requests.get(ready_url, timeout=1).status_code == 200:
                            break
                    except requests.RequestException:
                        pass
                    time.sleep(.2)
                else:
                    raise RuntimeError(f"{name} no quedó disponible en 60 segundos")
            print(f"Verificando demo aislada: {url}", flush=True)
            verify(url, args.output, pages=not args.skip_pages, profile="full")
        finally:
            for process in reversed(children):
                stop_owned(process)


if __name__ == "__main__":
    main()
