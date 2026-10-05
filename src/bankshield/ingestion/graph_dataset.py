"""Ingesta de aristas transaccionales desde el CSV de PaySim para grafos.

Lee el archivo Bronze en bloques y extrae las columnas necesarias para
construir la red de transacciones.  No modifica el archivo original.
"""

import csv
from pathlib import Path

import numpy as np
import pandas as pd

from bankshield.ingestion.paysim_profile import FIELDS, TRANSACTION_TYPES


# Columnas que se conservan para el grafo
EDGE_COLUMNS = ("step", "type", "amount", "nameOrig", "nameDest", "isFraud")


def _validate_header(path: Path) -> None:
    """Verifica cabecera y descarta referencias LFS."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        header = next(csv.reader(handle), [])
    if header and header[0].startswith("version https://git-lfs.github.com"):
        raise ValueError("Se requiere el CSV completo, no una referencia Git LFS")
    if len(header) != len(FIELDS) or set(header) != set(FIELDS):
        raise ValueError(f"Cabecera PaySim inesperada: {header}")


def read_transaction_edges(
    path: Path,
    limit: int | None = None,
    chunksize: int = 200_000,
) -> pd.DataFrame:
    """Lee aristas transaccionales desde Bronze sin modificar el archivo.

    Parameters
    ----------
    path : Path
        Ruta al CSV transaccional en ``data/bronze/transactions/``.
    limit : int or None
        Máximo de filas a leer.  ``None`` lee el archivo completo.
    chunksize : int
        Tamaño de bloque para lectura secuencial.

    Returns
    -------
    pd.DataFrame
        Columnas: step, type, amount, nameOrig, nameDest, isFraud.
    """
    path = Path(path)
    if limit is not None and limit < 1:
        raise ValueError("El límite debe ser un entero positivo")
    if chunksize < 1:
        raise ValueError("El tamaño de bloque debe ser positivo")

    _validate_header(path)

    dtypes = {
        "step": "int64",
        "type": "string",
        "amount": "float64",
        "nameOrig": "string",
        "nameDest": "string",
        "isFraud": "int8",
    }

    blocks: list[pd.DataFrame] = []
    total = 0

    for chunk in pd.read_csv(
        path,
        usecols=list(EDGE_COLUMNS),
        dtype=dtypes,
        chunksize=chunksize,
        encoding="utf-8-sig",
    ):
        # Validaciones básicas
        if chunk.isna().any().any():
            raise ValueError("Se encontraron valores ausentes en columnas de aristas")
        if not chunk["type"].isin(TRANSACTION_TYPES).all():
            raise ValueError("Tipo transaccional desconocido en los datos")
        if (chunk["amount"] < 0).any():
            raise ValueError("Se encontraron montos negativos")
        if not chunk["isFraud"].isin([0, 1]).all():
            raise ValueError("isFraud debe ser binario")

        blocks.append(chunk)
        total += len(chunk)
        print(f"Lectura de aristas: {total:,} filas", flush=True)

        if limit is not None and total >= limit:
            break

    if not blocks:
        raise ValueError("El CSV no contiene registros")

    edges = pd.concat(blocks, ignore_index=True)

    if limit is not None:
        edges = edges.head(limit)

    return edges


def summarize_edges(edges: pd.DataFrame) -> dict:
    """Genera resumen estadístico del conjunto de aristas.

    Útil para documentar la muestra antes de construir el grafo.
    No publica identificadores individuales de cuentas.
    """
    unique_orig = edges["nameOrig"].nunique()
    unique_dest = edges["nameDest"].nunique()
    unique_accounts = len(
        set(edges["nameOrig"].unique()) | set(edges["nameDest"].unique())
    )

    by_type = (
        edges.groupby("type", observed=True)
        .agg(
            transacciones=("amount", "size"),
            monto_total=("amount", "sum"),
            monto_medio=("amount", "mean"),
            fraudes=("isFraud", "sum"),
        )
        .to_dict(orient="index")
    )

    fraud_edges = edges["isFraud"].sum()

    return {
        "total_aristas": len(edges),
        "cuentas_origen_unicas": int(unique_orig),
        "cuentas_destino_unicas": int(unique_dest),
        "cuentas_totales_unicas": int(unique_accounts),
        "pasos_distintos": int(edges["step"].nunique()),
        "rango_pasos": [int(edges["step"].min()), int(edges["step"].max())],
        "monto_total": float(edges["amount"].sum()),
        "monto_medio": float(edges["amount"].mean()),
        "monto_maximo": float(edges["amount"].max()),
        "aristas_fraudulentas": int(fraud_edges),
        "tasa_fraude": float(fraud_edges / len(edges)) if len(edges) > 0 else 0.0,
        "por_tipo": {
            k: {kk: (int(vv) if kk != "monto_medio" else float(vv)) for kk, vv in v.items()}
            for k, v in by_type.items()
        },
    }
