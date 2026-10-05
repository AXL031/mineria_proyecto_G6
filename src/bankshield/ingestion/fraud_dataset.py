"""Adaptador Bronze para fraude; sustituible por un lector Silver."""

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from bankshield.features.fraud import build_fraud_feature_frame
from bankshield.ingestion.paysim_profile import FIELDS


@dataclass
class FraudPartition:
    features: pd.DataFrame
    labels: np.ndarray
    steps: np.ndarray


def derive_split_steps(step_counts, train_fraction=0.70, validation_fraction=0.15):
    """Elige límites por recuentos, sin consultar etiquetas ni fraccionar pasos."""
    if not (0 < train_fraction < 1 and 0 < validation_fraction < 1
            and train_fraction + validation_fraction < 1):
        raise ValueError("Fracciones de separación inválidas")
    counts = sorted(step_counts, key=lambda item: item["step"])
    if len(counts) < 3 or len({item["step"] for item in counts}) != len(counts):
        raise ValueError("Se necesitan al menos tres pasos distintos sin duplicar")
    if any(item["rows"] <= 0 for item in counts):
        raise ValueError("Cada paso debe contener registros")
    total = sum(item["rows"] for item in counts)
    cumulative = 0
    cuts = []
    fractions = (train_fraction, train_fraction + validation_fraction)
    for item in counts:
        cumulative += item["rows"]
        while len(cuts) < 2 and cumulative >= fractions[len(cuts)] * total:
            cuts.append(item["step"])
    if cuts[0] >= cuts[1] or cuts[1] >= counts[-1]["step"]:
        raise ValueError("El volumen concentrado en pocos pasos impide tres particiones")
    return tuple(cuts)


def read_fraud_dataset(path: Path, train_end_step: int, validation_end_step: int,
                       chunksize=200_000, account_sample_modulus=100):
    """Lee todas las filas, valida y asigna particiones exclusivamente por step.

    Audita una muestra determinista de cuentas (1/modulus) sin usarlas como
    predictores. Las intersecciones son diagnósticos de muestra, no conteos totales.
    """
    if not (0 <= train_end_step < validation_end_step):
        raise ValueError("Los límites temporales deben ser crecientes")
    if chunksize < 1 or account_sample_modulus < 1:
        raise ValueError("Tamaño de bloque y módulo de muestreo deben ser positivos")
    path = Path(path)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        header = next(csv.reader(handle), [])
    if header and header[0].startswith("version https://git-lfs.github.com"):
        raise ValueError("Se requiere el CSV completo, no una referencia Git LFS")
    if len(header) != len(FIELDS) or set(header) != set(FIELDS):
        raise ValueError("Cabecera PaySim inesperada")
    names = ("train", "validation", "test")
    blocks = {name: [] for name in names}
    accounts = {name: {role: set() for role in ("nameOrig", "nameDest")} for name in names}
    dtypes = {field: "float64" for field in FIELDS if field not in ("type", "nameOrig", "nameDest")}
    dtypes.update({field: "string" for field in ("type", "nameOrig", "nameDest")})
    total = 0
    for raw in pd.read_csv(path, dtype=dtypes, chunksize=chunksize, encoding="utf-8-sig"):
        if raw.isna().any().any():
            raise ValueError("Se encontraron valores ausentes; revisar calidad antes de entrenar")
        if not np.isfinite(raw["step"]).all() or (raw["step"] < 0).any() or (raw["step"] % 1 != 0).any():
            raise ValueError("step debe contener enteros finitos no negativos")
        if not raw["isFraud"].isin([0, 1]).all():
            raise ValueError("isFraud debe ser binario")
        frame = build_fraud_feature_frame(raw)
        frame["_label"] = raw["isFraud"].astype("int8")
        frame["_step"] = raw["step"].astype("int64")
        masks = (raw["step"] <= train_end_step,
                 (raw["step"] > train_end_step) & (raw["step"] <= validation_end_step),
                 raw["step"] > validation_end_step)
        for name, mask in zip(names, masks):
            if not mask.any():
                continue
            blocks[name].append(frame.loc[mask].copy())
            for role in ("nameOrig", "nameDest"):
                ids = raw.loc[mask, role].drop_duplicates()
                hashed = pd.util.hash_pandas_object(ids, index=False)
                accounts[name][role].update(ids[hashed % account_sample_modulus == 0])
        total += len(raw)
        print(f"Lectura de entrenamiento: {total:,} filas", flush=True)
    partitions = {}
    for name in names:
        if not blocks[name]:
            raise ValueError(f"Partición vacía: {name}")
        frame = pd.concat(blocks[name], ignore_index=True)
        blocks[name].clear()
        labels = frame.pop("_label").to_numpy()
        steps = frame.pop("_step").to_numpy()
        if set(np.unique(labels)) != {0, 1}:
            raise ValueError(f"La partición {name} necesita ambas clases para evaluar")
        partitions[name] = FraudPartition(frame, labels, steps)
    overlap = {"method": "deterministic_pandas_hash_sample", "sample_modulus": account_sample_modulus,
               "unique_sampled_accounts": {}, "sampled_intersections": {}}
    for role in ("nameOrig", "nameDest"):
        overlap["unique_sampled_accounts"][role] = {name: len(accounts[name][role]) for name in names}
        overlap["sampled_intersections"][role] = {
            f"{left}_{right}": len(accounts[left][role] & accounts[right][role])
            for left, right in (("train", "validation"), ("train", "test"), ("validation", "test"))
        }
    return partitions, overlap
