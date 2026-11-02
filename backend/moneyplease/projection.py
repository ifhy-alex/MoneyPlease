"""Proyección 2D de ofertas alrededor del perfil para el mapa semántico.

El radio es la similitud real con el perfil (0 = la más parecida, 1 = la menos); el ángulo sale de un PCA
sobre lo que cada oferta tiene de distinto al perfil, así que las ofertas parecidas entre sí quedan juntas.
"""
import numpy as np

# En 3D la oferta más parecida no va en el origen: ahí la taparía la estrella del perfil.
MIN_RADIUS_3D = 0.08


def _radius(sims: np.ndarray) -> np.ndarray:
    spread = sims.max() - sims.min()
    return (sims.max() - sims) / spread if spread > 1e-12 else np.full(len(sims), 0.5)


def _components(jobs: np.ndarray, profile: np.ndarray, sims: np.ndarray, k: int) -> np.ndarray:
    """Coordenadas de cada oferta en las k primeras componentes de lo que la distingue del perfil."""
    residual = jobs - np.outer(sims, profile)
    residual -= residual.mean(axis=0)
    _, _, vt = np.linalg.svd(residual, full_matrices=False)
    comps = vt[:k]
    # El signo de un componente del SVD es arbitrario: se fija para que el mapa no se voltee entre corridas.
    signs = np.sign(comps[np.arange(len(comps)), np.abs(comps).argmax(axis=1)])
    coords = residual @ (comps * signs[:, None]).T
    if coords.shape[1] < k:
        coords = np.hstack([coords, np.zeros((len(coords), k - coords.shape[1]))])
    return coords


def project(profile: np.ndarray, jobs: np.ndarray, ids: list[int]) -> list[tuple[float, float, float]]:
    n = len(ids)
    if n == 0:
        return []
    sims = jobs @ profile
    radius = _radius(sims)
    if n < 3:
        rank = {job_id: i for i, job_id in enumerate(sorted(ids))}
        theta = np.array([2 * np.pi * rank[job_id] / n for job_id in ids])
    else:
        coords = _components(jobs, profile, sims, 2)
        theta = np.arctan2(coords[:, 1], coords[:, 0])
    return [(float(r * np.cos(t)), float(r * np.sin(t)), float(s)) for r, t, s in zip(radius, theta, sims)]


def project3d(profile: np.ndarray, jobs: np.ndarray, ids: list[int]) -> list[tuple[float, float, float, float]]:
    """Como `project`, pero en 3D: el radio es la similitud y la dirección sale de 3 componentes."""
    n = len(ids)
    if n == 0:
        return []
    sims = jobs @ profile
    radius = MIN_RADIUS_3D + (1 - MIN_RADIUS_3D) * _radius(sims)
    if n < 4:
        # Espiral de Fibonacci sobre la esfera, por orden de id: direcciones bien repartidas y estables.
        rank = {job_id: i for i, job_id in enumerate(sorted(ids))}
        dirs = []
        for job_id in ids:
            i = rank[job_id]
            y = 1 - 2 * (i + 0.5) / n
            rho = np.sqrt(1 - y * y)
            theta = i * np.pi * (3 - np.sqrt(5))
            dirs.append((rho * np.cos(theta), y, rho * np.sin(theta)))
        dirs = np.array(dirs)
    else:
        coords = _components(jobs, profile, sims, 3)
        norms = np.linalg.norm(coords, axis=1, keepdims=True)
        dirs = np.where(norms > 1e-9, coords / np.where(norms > 1e-9, norms, 1), np.array([1.0, 0, 0]))
    return [(float(r * d[0]), float(r * d[1]), float(r * d[2]), float(s)) for r, d, s in zip(radius, dirs, sims)]
