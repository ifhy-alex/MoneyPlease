import numpy as np

from moneyplease.clusters import cluster_count, cluster_names, clusters


def test_clusters_determinista_e_indices_validos():
    pts = np.random.default_rng(1).normal(size=(40, 3))
    a = clusters(pts, 4)
    assert a == clusters(pts, 4)
    assert set(a) <= set(range(4)) and len(a) == 40


def test_clusters_separa_grupos_obvios():
    rng = np.random.default_rng(2)
    pts = np.vstack([rng.normal(size=(10, 3)) * 0.3 + [5, 0, 0], rng.normal(size=(10, 3)) * 0.3 + [-5, 0, 0]])
    out = clusters(pts, 2)
    assert len(set(out[:10])) == 1 and len(set(out[10:])) == 1 and out[0] != out[10]


def test_cluster_count():
    assert [cluster_count(n) for n in (5, 30, 60, 300)] == [1, 2, 5, 6]


def test_cluster_names():
    assert cluster_names([["Java y Spring Boot", "Java y Python"], ["Linux y redes"]]) == ["Java · Python", "Linux · Redes"]
    assert cluster_names([["a"], ["b"], ["sin nada técnico"]])[2] == "Grupo 3"


def test_los_idiomas_no_nombran_nubes():
    # El inglés lo piden casi todas las ofertas: no distingue una nube de otra.
    assert cluster_names([["English y Java", "English y Python", "English"]]) == ["Java · Python"]


def test_el_nombre_premia_lo_que_distingue_a_la_nube():
    a = ["Security Python", "Security Python", "Security"]
    b = ["Security Excel", "Security Excel", "Security"]
    names = cluster_names([a, b])
    assert names[0].startswith("Python") and names[1].startswith("Excel")
