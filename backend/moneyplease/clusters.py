"""Nubes del universo 3D: k-means determinista sobre las coordenadas y un nombre por nube."""
from collections import Counter

import numpy as np

from moneyplease.skill_areas import area_of, display_skill, skills_in

MAX_ITER = 50


def cluster_count(n: int) -> int:
    """Cuántas nubes: una cada ~12 ofertas, entre 2 y 6 (una sola si hay muy pocas)."""
    return 1 if n < 6 else min(max(round(n / 12), 2), 6)


def clusters(coords: np.ndarray, k: int, seed: int = 0) -> list[int]:
    n = len(coords)
    if n == 0:
        return []
    k = max(1, min(k, n))
    rng = np.random.default_rng(seed)
    # k-means++: cada centro nuevo, lejos de los anteriores (con probabilidad ∝ distancia²).
    centers = [coords[rng.integers(n)]]
    while len(centers) < k:
        d2 = np.min([((coords - c) ** 2).sum(axis=1) for c in centers], axis=0)
        total = d2.sum()
        centers.append(coords[rng.choice(n, p=d2 / total)] if total > 0 else coords[rng.integers(n)])
    centers = np.array(centers, dtype=float)
    labels = np.zeros(n, dtype=int)
    for _ in range(MAX_ITER):
        labels_new = ((coords[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2).argmin(axis=1)
        if _ and np.array_equal(labels_new, labels):
            break
        labels = labels_new
        for j in range(k):
            if (labels == j).any():
                centers[j] = coords[labels == j].mean(axis=0)
    return [int(x) for x in labels]


def cluster_names(texts_by_cluster: list[list[str]]) -> list[str]:
    """Las 2 skills más frecuentes de cada nube ("Java · Python"); sin ninguna, "Grupo N"."""
    names = []
    for i, texts in enumerate(texts_by_cluster):
        # Los idiomas (sobre todo el inglés) aparecen en casi todas las ofertas: no sirven para nombrar una nube.
        counts = Counter(skill for text in texts for skill in skills_in(text) if area_of(skill) != "idiomas")
        top = sorted(counts, key=lambda s: (-counts[s], s))[:2]
        names.append(" · ".join(display_skill(s) for s in top) if top else f"Grupo {i + 1}")
    return names
