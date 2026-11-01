import math

import numpy as np

from moneyplease.db.models import JobLabel


def near(p: list[float], s: float, seed: int) -> list[float]:
    """Vector unitario con similitud coseno s respecto de p."""
    p = np.array(p)
    u = np.random.default_rng(seed).normal(size=len(p))
    u -= (u @ p) * p
    u /= np.linalg.norm(u)
    return list(s * p + math.sqrt(1 - s * s) * u)


def test_sin_perfil_404(client):
    resp = client.get("/api/map")
    assert resp.status_code == 404 and resp.json()["detail"] == "Todavía no hay perfil guardado"


def test_perfil_sin_ofertas_con_embedding(client, world):
    world.profile()
    world.job()
    assert client.get("/api/map").json() == {"total": 0, "puntos": []}


def test_excluye_no_interesa_filtros_duros_y_sin_embedding(client, world, session):
    prof = world.profile()
    ok1 = world.job(embedding=near(prof.embedding, 0.9, 1))
    ok2 = world.job(embedding=near(prof.embedding, 0.5, 2))
    hidden = world.job(embedding=near(prof.embedding, 0.8, 3))
    world.job(titulo="Senior Engineer", embedding=near(prof.embedding, 0.8, 4))
    world.job(embedding=None)
    session.add(JobLabel(job_id=hidden.id, etiqueta="mala"))
    session.commit()
    world.match(prof, ok1, score=88)
    puntos = {p["job_id"]: p for p in client.get("/api/map").json()["puntos"]}
    assert set(puntos) == {ok1.id, ok2.id}
    assert puntos[ok1.id]["puntaje"] == 88 and puntos[ok2.id]["puntaje"] is None
    assert puntos[ok1.id]["similitud"] > puntos[ok2.id]["similitud"]


def test_maximo_300_las_mas_cercanas(client, world):
    prof = world.profile()
    jobs = [world.job(embedding=near(prof.embedding, 0.95 - i * 0.002, i)) for i in range(305)]
    data = client.get("/api/map").json()
    ids = {p["job_id"] for p in data["puntos"]}
    assert data["total"] == 300 and len(ids) == 300
    assert jobs[-1].id not in ids and jobs[0].id in ids


def test_coordenadas_en_rango(client, world):
    prof = world.profile()
    for i in range(6):
        world.job(embedding=near(prof.embedding, 0.9 - i * 0.1, i))
    for p in client.get("/api/map").json()["puntos"]:
        assert -1 <= p["x"] <= 1 and -1 <= p["y"] <= 1
        assert math.hypot(p["x"], p["y"]) <= 1 + 1e-9
