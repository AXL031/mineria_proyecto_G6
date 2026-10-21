"""Ensaya los endpoints de segmentos con los artefactos locales preparados.

Comprueba resumen, paginación, detalle de cuenta, segmento inexistente,
parámetros inválidos y artefacto ausente sobre HTTP en proceso, sin levantar un
servidor externo. Escribe la evidencia en un JSON y devuelve un código distinto
de cero si alguna comprobación falla.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from fastapi.testclient import TestClient

from api.main import app
from bankshield.services import segments as segments_service

ARTIFACT_ENV = (
    "BANKSHIELD_SEGMENTS_PARQUET",
    "BANKSHIELD_SEGMENTS_REPORT",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parquet", type=Path, help="Tabla de cuentas segmentadas")
    parser.add_argument("--report", type=Path, help="Reporte JSON de segmentación")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts" / "reports" / "segments-http-check.json",
        help="Evidencia JSON de la comprobación",
    )
    args = parser.parse_args()

    saved = {key: os.environ.get(key) for key in ARTIFACT_ENV}
    if args.parquet is not None:
        os.environ["BANKSHIELD_SEGMENTS_PARQUET"] = str(args.parquet)
    if args.report is not None:
        os.environ["BANKSHIELD_SEGMENTS_REPORT"] = str(args.report)

    client = TestClient(app)
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "transport": "in_process_testclient",
        "artifacts": {},
        "checks": {},
        "observations": {},
    }
    failures: list[str] = []

    def check(name: str, condition: bool, detail=None) -> None:
        report["checks"][name] = bool(condition)
        if detail is not None:
            report["observations"][name] = detail
        if not condition:
            failures.append(name)

    try:
        frame = segments_service.load_segments()
        summary_source = segments_service.load_report()
        report["artifacts"] = {
            "parquet": str(segments_service.DEFAULT_SEGMENTS_PARQUET),
            "report": str(segments_service.DEFAULT_REPORT_JSON),
            "parquet_rows": int(len(frame)),
            "report_total_accounts": summary_source.get("total_accounts"),
        }

        response = client.get("/api/segments/summary")
        check("summary_status_200", response.status_code == 200, response.status_code)
        summary = response.json() if response.status_code == 200 else {}
        check(
            "summary_total_accounts_matches_artifact",
            summary.get("total_accounts") == len(frame),
            summary.get("total_accounts"),
        )
        check(
            "summary_profiles_complete",
            len(summary.get("profiles", [])) == summary.get("metrics", {}).get("chosen_k"),
            len(summary.get("profiles", [])),
        )
        check(
            "summary_segment_sizes_match_parquet",
            sum(int(profile["size"]) for profile in summary.get("profiles", []))
            == len(frame),
        )

        segments = sorted(int(profile["segment"]) for profile in summary.get("profiles", []))
        segment = segments[0]
        expected_size = int(
            next(
                profile["size"]
                for profile in summary["profiles"]
                if int(profile["segment"]) == segment
            )
        )

        first_page = client.get(f"/api/segments/{segment}/accounts?limit=5&offset=0")
        check("accounts_status_200", first_page.status_code == 200, first_page.status_code)
        first_body = first_page.json() if first_page.status_code == 200 else {}
        check("accounts_limit_respected", first_body.get("count") == min(5, expected_size))
        accounts = first_body.get("accounts", [])
        if accounts:
            check(
                "accounts_sorted_by_activity",
                [row["n_received"] for row in accounts]
                == sorted((row["n_received"] for row in accounts), reverse=True),
            )

        second_page = client.get(f"/api/segments/{segment}/accounts?limit=5&offset=5")
        check("accounts_offset_status_200", second_page.status_code == 200)
        if second_page.status_code == 200 and accounts and expected_size > 5:
            check(
                "accounts_pagination_advances",
                second_page.json()["accounts"][0]["account"] != accounts[0]["account"],
            )

        if accounts:
            account = accounts[0]["account"]
            detail = client.get(f"/api/segments/{segment}/account/{account}")
            check("account_detail_status_200", detail.status_code == 200)
            if detail.status_code == 200:
                body = detail.json()
                check("account_detail_identity", str(body.get("account")) == str(account))
                check("account_detail_segment", int(body.get("segment")) == segment)

        unknown = client.get("/api/segments/999999/accounts")
        check("unknown_segment_404", unknown.status_code == 404, unknown.status_code)

        invalid_limit = client.get(f"/api/segments/{segment}/accounts?limit=0")
        check("invalid_limit_422", invalid_limit.status_code == 422, invalid_limit.status_code)

        invalid_offset = client.get(f"/api/segments/{segment}/accounts?offset=-1")
        check(
            "invalid_offset_422",
            invalid_offset.status_code == 422,
            invalid_offset.status_code,
        )

        unknown_account = client.get(
            f"/api/segments/{segment}/account/ZZZ-CUENTA-INEXISTENTE"
        )
        check("unknown_account_404", unknown_account.status_code == 404)

        os.environ["BANKSHIELD_SEGMENTS_PARQUET"] = str(
            ROOT / "artifacts" / "reports" / "no-existe-segments.parquet"
        )
        missing = client.get(f"/api/segments/{segment}/accounts")
        check("missing_artifact_503", missing.status_code == 503, missing.status_code)
        if missing.status_code == 503:
            check(
                "missing_artifact_mentions_command",
                "segment_transactions.py" in missing.json().get("detail", ""),
            )
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    report["status"] = "passed" if not failures else "failed"
    report["failures"] = failures
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    if failures:
        print(f"Fallaron {len(failures)} comprobaciones: {', '.join(failures)}")
        print(f"Evidencia parcial: {args.output}")
        raise SystemExit(1)
    print(f"Segmentos verificados: {len(report['checks'])} comprobaciones")
    print(f"Evidencia: {args.output}")


if __name__ == "__main__":
    main()
