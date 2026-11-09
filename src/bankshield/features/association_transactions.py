"""Ítems sin etiquetas ni información posterior; bins suministrados por D1."""

import numpy as np

ATTRIBUTES = ("type", "amount_bin", "origin_balance_bin", "exceeds_origin_balance",
              "positive_amount_equals_balance")


def item_masks(frame):
    values = {name: frame[name].astype(str).to_numpy() for name in ATTRIBUTES[:3]}
    values["exceeds_origin_balance"] = np.where(frame.amount > frame.oldbalanceOrg, "true", "false")
    values["positive_amount_equals_balance"] = np.where(
        (frame.amount > 0) & frame.amount.eq(frame.oldbalanceOrg), "true", "false")
    return {f"{name}={value}": array == value for name, array in values.items()
            for value in sorted(set(array))}


def antecedent_mask(masks, candidate, n):
    result = np.ones(n, dtype=bool)
    for item in candidate:
        result &= masks.get(item, np.zeros(n, dtype=bool))
    return result
