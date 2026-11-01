import numpy as np

from tests.api.test_map import near


def test_sin_perfil_404(client):
    assert client.get("/api/universe").status_code == 404


def test_sin_ofertas_con_embedding(client, world):
    world.profile()
    world.job()
    assert client.get("/api/universe").json() == {"total": 0, "puntos": [], "nubes": []}


def test_mismas_ofertas_que_el_mapa_sin_duplicados(client, world):
    prof = world.profile()
    for i in range(8):
        world.job(empresa=f"E{i}", embedding=near(prof.embedding, 0.9 - i * 0.05, i))
    ids_map = {p["job_id"] for p in client.get("/api/map").json()["puntos"]}
    ids_uni = {p["job_id"] for p in client.get("/api/universe").json()["puntos"]}
    assert ids_map == ids_uni and len(ids_uni) == 8


def test_duplicados_quedan_en_su_representante(client, world):
    prof = world.profile()
    a = world.job(empresa="HPE", embedding=near(prof.embedding, 0.9, 1))
    b = world.job(empresa="HPE", embedding=list(a.embedding))
    world.match(prof, a, score=70)
    world.match(prof, b, score=95)
    for i in range(4):
        world.job(empresa=f"E{i}", embedding=near(prof.embedding, 0.8, 10 + i))
    puntos = {p["job_id"]: p for p in client.get("/api/universe").json()["puntos"]}
    assert b.id in puntos and a.id not in puntos
    assert puntos[b.id]["duplicados"] == [a.id] and puntos[b.id]["puntaje"] == 95


def test_nubes_con_centroide(client, world):
    prof = world.profile()
    for i in range(30):
        world.job(empresa=f"E{i}", titulo="Java developer" if i % 2 else "Data analyst SQL",
                  embedding=near(prof.embedding, 0.95 - i * 0.01, i))
    data = client.get("/api/universe").json()
    nubes = {n["id"]: n for n in data["nubes"]}
    assert sum(n["n"] for n in nubes.values()) == data["total"] == 30
    for nid, nube in nubes.items():
        pts = np.array([[p["x"], p["y"], p["z"]] for p in data["puntos"] if p["nube"] == nid])
        assert np.allclose(pts.mean(axis=0), [nube["x"], nube["y"], nube["z"]], atol=1e-9)
        assert nube["nombre"]
