"""Asociaciones descriptivas fijas; no cambian el clasificador ni su umbral."""

from bankshield.features.fraud import build_fraud_feature_frame

RULES = {
    "transfer": "Tipo TRANSFER",
    "cash_out": "Tipo CASH_OUT",
    "positive_amount_equals_balance": "Monto positivo igual al saldo anterior",
    "amount_exceeds_balance": "Monto supera el saldo anterior",
    "transfer_equals_balance": "TRANSFER con monto positivo igual al saldo anterior",
    "cash_out_equals_balance": "CASH_OUT con monto positivo igual al saldo anterior",
}


def rule_masks(frame):
    # Reutiliza el contrato y nunca lee etiquetas/saldos posteriores.
    build_fraud_feature_frame(frame)
    transfer = frame["type"].eq("TRANSFER").to_numpy()
    cash_out = frame["type"].eq("CASH_OUT").to_numpy()
    equal = (frame["amount"].gt(0) & frame["amount"].eq(frame["oldbalanceOrg"])).to_numpy()
    exceeds = frame["amount"].gt(frame["oldbalanceOrg"]).to_numpy()
    return dict(zip(RULES, (transfer, cash_out, equal, exceeds, transfer & equal, cash_out & equal)))


def summarize_rules(rows, fraud, counts):
    prevalence = fraud / rows if rows else 0.0
    return {
        "rows": rows, "fraud": fraud, "prevalence": prevalence,
        "rules": [
            {"id": key, "description": description, "matches": counts[key][0],
             "fraud_matches": counts[key][1],
             "support": counts[key][0] / rows if rows else 0.0,
             "confidence": counts[key][1] / counts[key][0] if counts[key][0] else None,
             "lift": (counts[key][1] / counts[key][0]) / prevalence
                     if counts[key][0] and prevalence else None,
             "fraud_coverage": counts[key][1] / fraud if fraud else None}
            for key, description in RULES.items()
        ],
    }
