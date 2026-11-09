"""Consulta de asociaciones preparadas; no descubre reglas durante HTTP."""

from bankshield.analytics_contract import strict_json
from bankshield.models.associations import PARTITIONS, report_identity


def read_associations(path, partition="test", limit=20, offset=0):
    report = strict_json(path)
    if report.get("schema_version") != 1 or report.get("method") != "apriori_bounded":
        raise ValueError("Reporte de asociaciones incompatible")
    if report.get("analysis_id") != report_identity(report) or report.get("selection_partition") != "validation":
        raise ValueError("Identidad de asociaciones incompatible")
    if partition not in PARTITIONS or not 1 <= limit <= 100 or offset < 0:
        raise ValueError("Paginación/partición inválida")
    rules = report["rules"]
    return {"schema_version": 1, "analysis_id": report["analysis_id"], "method": report["method"],
            "partition": partition, "simulation_data": True, "selection_partition": "validation",
            "total_rules": len(rules), "limit": limit, "offset": offset,
            "rules": [{"id": rule["id"], "antecedent": rule["antecedent"], "consequent": rule["consequent"],
                       **rule["partitions"][partition]} for rule in rules[offset:offset + limit]],
            "evaluation": report["evaluation"][partition], "dataset": report["dataset"],
            "diagnostic": report["diagnostic"], "config": report["config"], "limitations": report["limitations"]}
