"""Segmentación de cuentas de destino reincidentes.

Compara una línea base exploratoria (cortes por cuantiles de actividad) con un
método principal de agrupamiento (KMeans sobre variables estandarizadas). La
evaluación usa silueta sobre una muestra y estabilidad por remuestreo (ARI),
porque las cuentas reincidentes son pocas y el agrupamiento debe ser estable.

El agrupamiento es independiente de la etiqueta: ``CLUSTER_COLUMNS`` no incluye
``fraud_rate_received`` ni ningún derivado de ``isFraud``. La etiqueta se usa
solo para perfilar los segmentos una vez formados.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from bankshield.features.segments import BEHAVIOR_COLUMNS
from bankshield.ingestion.paysim_profile import TRANSACTION_TYPES

CLUSTER_COLUMNS = (
    "n_received",
    "mean_received_amount",
    "cv_received_amount",
    "amount_concentration",
    "activity_density",
    *(f"share_{name.lower()}" for name in TRANSACTION_TYPES),
)
HEAVY_TAILED = (
    "n_received",
    "n_sent",
    "total_received",
    "total_sent",
    "mean_received_amount",
    "std_received_amount",
    "max_received_amount",
    "distinct_senders",
    "active_steps",
    "activity_density",
)


def _signed_log1p(values: np.ndarray) -> np.ndarray:
    return np.sign(values) * np.log1p(np.abs(values))


def prepare_matrix(
    features: pd.DataFrame, columns=CLUSTER_COLUMNS
) -> np.ndarray:
    """Escala las variables: log para colas pesadas y estandarización final."""
    missing = sorted(set(columns) - set(features.columns))
    if missing:
        raise ValueError(f"Faltan variables de segmentación: {missing}")
    if features.empty:
        raise ValueError("No hay cuentas reincidentes para segmentar")

    matrix = pd.DataFrame(index=features.index)
    for name in columns:
        values = pd.to_numeric(features[name], errors="raise").to_numpy(dtype="float64")
        if name in HEAVY_TAILED:
            values = np.log1p(np.clip(values, 0.0, None))
        elif name == "net_flow":
            values = _signed_log1p(values)
        matrix[name] = values
    return StandardScaler().fit_transform(matrix.to_numpy(dtype="float64"))


def baseline_segments(features: pd.DataFrame, n_segments: int, column: str = "n_received") -> np.ndarray:
    """Línea base: cortes por cuantiles de la actividad de recepción."""
    if not 1 <= n_segments <= len(features):
        raise ValueError("n_segments fuera de rango para la línea base")
    ranked = features[column].rank(method="first")
    labels = pd.qcut(ranked, n_segments, labels=False).to_numpy(dtype="int64")
    return labels


def fit_kmeans(matrix: np.ndarray, k: int, seed: int) -> MiniBatchKMeans:
    model = MiniBatchKMeans(
        n_clusters=k, random_state=seed, n_init=10, batch_size=4096
    )
    model.fit(matrix)
    return model


def _silhouette_on_sample(matrix: np.ndarray, labels: np.ndarray, seed: int, sample_size: int) -> float:
    n = len(matrix)
    if n <= sample_size:
        return float(silhouette_score(matrix, labels))
    rng = np.random.default_rng(seed)
    index = rng.choice(n, size=sample_size, replace=False)
    if len(np.unique(labels[index])) < 2:
        return float("nan")
    return float(silhouette_score(matrix[index], labels[index]))


def choose_k(
    matrix: np.ndarray, k_range, seed: int, sample_size: int = 10_000
) -> tuple[int, dict[int, float]]:
    """Elige k por silueta sobre una muestra (evita O(n²) en todo el conjunto)."""
    scores: dict[int, float] = {}
    for k in k_range:
        if k >= len(matrix):
            continue
        labels = fit_kmeans(matrix, k, seed).labels_
        scores[int(k)] = _silhouette_on_sample(matrix, labels, seed, sample_size)
    if not scores:
        raise ValueError("Ningún k válido para evaluar")
    best_k = max(scores, key=lambda key: (scores[key], -key))
    return best_k, scores


def evaluate_stability(
    matrix: np.ndarray, k: int, seed: int, n_iterations: int = 3, fraction: float = 0.5
) -> list[float]:
    """ARI entre el agrupamiento completo y remuestras; cerca de 1 es estable."""
    full = fit_kmeans(matrix, k, seed).labels_
    rng = np.random.default_rng(seed + 1)
    scores: list[float] = []
    n = len(matrix)
    size = max(k, int(n * fraction))
    for _ in range(n_iterations):
        index = rng.choice(n, size=min(size, n), replace=False)
        subsample_labels = fit_kmeans(matrix[index], k, seed).labels_
        scores.append(float(adjusted_rand_score(full[index], subsample_labels)))
    return scores


def profile_segments(features: pd.DataFrame, labels: np.ndarray) -> pd.DataFrame:
    """Perfil medio por segmento con el tamaño de cada grupo."""
    frame = features.copy()
    frame["segment"] = labels
    grouped = frame.groupby("segment", sort=True, observed=True)
    profile = grouped[list(BEHAVIOR_COLUMNS)].mean()
    profile.insert(0, "size", grouped.size())
    return profile.reset_index()


def segment_accounts(
    features: pd.DataFrame,
    k_range=range(2, 8),
    seed: int = 42,
    sample_size: int = 10_000,
    stability_iterations: int = 3,
    stability_fraction: float = 0.5,
) -> dict:
    """Ejecuta la segmentación y devuelve etiquetas, métricas y perfiles."""
    matrix = prepare_matrix(features)
    chosen_k, scores = choose_k(matrix, k_range, seed, sample_size)
    labels = fit_kmeans(matrix, chosen_k, seed).labels_
    stability = evaluate_stability(
        matrix, chosen_k, seed, stability_iterations, stability_fraction
    )
    baseline_labels = baseline_segments(features, chosen_k)

    baseline = features.assign(segment=baseline_labels).groupby(
        "segment", sort=True, observed=True
    ).agg(
        size=("n_received", "size"),
        mean_n_received=("n_received", "mean"),
        mean_total_received=("total_received", "mean"),
    )

    return {
        "chosen_k": chosen_k,
        "silhouette_by_k": scores,
        "silhouette": scores[chosen_k],
        "stability_ari": stability,
        "mean_stability_ari": float(np.mean(stability)),
        "labels": labels,
        "profiles": profile_segments(features, labels),
        "baseline_profiles": baseline.reset_index(),
        "total_accounts": int(len(features)),
    }
