import math

import numpy as np

from moneyplease.projection import project

D = 8


def unit(i: int) -> np.ndarray:
    v = np.zeros(D)
    v[i] = 1.0
    return v


def jobs_with(sims: list[float]) -> np.ndarray:
    # Cada oferta: similitud s con el perfil (eje 0) y el resto en un eje propio.
    return np.array([s * unit(0) + math.sqrt(1 - s * s) * unit(1 + i % (D - 1)) for i, s in enumerate(sims)])


def test_radio_crece_con_la_distancia():
    out = project(unit(0), jobs_with([0.9, 0.7, 0.5, 0.3]), [1, 2, 3, 4])
    radii = [math.hypot(x, y) for x, y, _ in out]
    assert np.allclose(radii, [0, 1 / 3, 2 / 3, 1], atol=1e-6)
    assert np.allclose([s for *_, s in out], [0.9, 0.7, 0.5, 0.3])


def test_similitud_constante_da_radio_medio():
    out = project(unit(0), jobs_with([0.6] * 5), [1, 2, 3, 4, 5])
    assert all(abs(math.hypot(x, y) - 0.5) < 1e-9 for x, y, _ in out)


def test_signo_determinista_sin_importar_el_orden():
    rng = np.random.default_rng(3)
    jobs = rng.normal(size=(12, D))
    jobs /= np.linalg.norm(jobs, axis=1, keepdims=True)
    ids = list(range(100, 112))
    first = dict(zip(ids, project(unit(0), jobs, ids)))
    order = rng.permutation(12)
    second = dict(zip([ids[i] for i in order], project(unit(0), jobs[order], [ids[i] for i in order])))
    for i in ids:
        assert np.allclose(first[i], second[i], atol=1e-9)


def test_menos_de_tres_reparte_por_id():
    out = dict(zip([9, 5], project(unit(0), jobs_with([0.6, 0.6]), [9, 5])))
    assert np.allclose(out[5][:2], (0.5, 0), atol=1e-9)
    assert np.allclose(out[9][:2], (-0.5, 0), atol=1e-9)


def test_vacio():
    assert project(unit(0), np.empty((0, D)), []) == []


def test_3d_radio_con_minimo_para_no_tapar_la_mejor_oferta():
    # Como en 2D, pero la más parecida no queda en el origen (escondida bajo la estrella del perfil).
    from moneyplease.projection import MIN_RADIUS_3D, project3d
    out = project3d(unit(0), jobs_with([0.9, 0.7, 0.5, 0.3]), [1, 2, 3, 4])
    expected = [MIN_RADIUS_3D + (1 - MIN_RADIUS_3D) * r for r in (0, 1 / 3, 2 / 3, 1)]
    assert MIN_RADIUS_3D >= 0.05
    assert np.allclose([math.sqrt(x * x + y * y + z * z) for x, y, z, _ in out], expected, atol=1e-6)


def test_3d_signo_determinista_sin_importar_el_orden():
    from moneyplease.projection import project3d
    rng = np.random.default_rng(5)
    jobs = rng.normal(size=(12, D))
    jobs /= np.linalg.norm(jobs, axis=1, keepdims=True)
    ids = list(range(200, 212))
    first = dict(zip(ids, project3d(unit(0), jobs, ids)))
    order = rng.permutation(12)
    second = dict(zip([ids[i] for i in order], project3d(unit(0), jobs[order], [ids[i] for i in order])))
    for i in ids:
        assert np.allclose(first[i], second[i], atol=1e-9)


def test_3d_menos_de_cuatro_en_espiral():
    from moneyplease.projection import project3d
    out = project3d(unit(0), jobs_with([0.6, 0.6, 0.6]), [7, 3, 5])
    vecs = [np.array(o[:3]) for o in out]
    from moneyplease.projection import MIN_RADIUS_3D
    mid = MIN_RADIUS_3D + (1 - MIN_RADIUS_3D) * 0.5
    assert all(abs(np.linalg.norm(v) - mid) < 1e-9 for v in vecs)
    for a in range(3):
        for b in range(a + 1, 3):
            assert vecs[a] @ vecs[b] / mid ** 2 < 0.99


def test_3d_vacio():
    from moneyplease.projection import project3d
    assert project3d(unit(0), np.empty((0, D)), []) == []
