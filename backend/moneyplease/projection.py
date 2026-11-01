"""Proyección 2D de ofertas alrededor del perfil para el mapa semántico.

El radio es la similitud real con el perfil (0 = la más parecida, 1 = la menos); el ángulo sale de un PCA
sobre lo que cada oferta tiene de distinto al perfil, así que las ofertas parecidas entre sí quedan juntas.
"""
import numpy as np


def project(profile: np.ndarray, jobs: np.ndarray, ids: list[int]) -> list[tuple[float, float, float]]:
    n = len(ids)
    if n == 0:
        return []
    sims = jobs @ profile
    spread = sims.max() - sims.min()
    radius = (sims.max() - sims) / spread if spread > 1e-12 else np.full(n, 0.5)
    if n < 3:
        rank = {job_id: i for i, job_id in enumerate(sorted(ids))}
        theta = np.array([2 * np.pi * rank[job_id] / n for job_id in ids])
    else:
        residual = jobs - np.outer(sims, profile)
        residual -= residual.mean(axis=0)
        _, _, vt = np.linalg.svd(residual, full_matrices=False)
        comps = vt[:2]
        # El signo de un componente del SVD es arbitrario: se fija para que el mapa no se voltee entre corridas.
        signs = np.sign(comps[np.arange(len(comps)), np.abs(comps).argmax(axis=1)])
        comps = comps * signs[:, None]
        coords = residual @ comps.T
        theta = np.arctan2(coords[:, 1] if coords.shape[1] > 1 else np.zeros(n), coords[:, 0])
    return [(float(r * np.cos(t)), float(r * np.sin(t)), float(s)) for r, t, s in zip(radius, theta, sims)]
