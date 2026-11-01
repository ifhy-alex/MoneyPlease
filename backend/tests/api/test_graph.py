from moneyplease.profile import store
from moneyplease.profile.schema import DEFAULT_PREFERENCES, Profile
from tests.fakes import FakeEmbedder
from tests.test_profile_store import DRAFT


def save_profile(session, *skills):
    perfil = Profile.model_validate({**DRAFT, "preferences": DEFAULT_PREFERENCES.model_dump(),
                                     "skills": [{"name": s, "level": "intermedio", "evidence": "x"} for s in skills]})
    return store.save(session, perfil, "cv", FakeEmbedder())


def test_graph_404_sin_perfil(client):
    assert client.get("/api/skills-graph").status_code == 404


def test_graph_sin_matches_listas_vacias(client, session):
    save_profile(session, "Java")
    assert client.get("/api/skills-graph").json() == {"habilidades": [], "ofertas": [], "aristas": []}


def test_graph_aristas_y_faltantes(client, session, world):
    prof = save_profile(session, "Java", "Python")
    a = world.job(titulo="Backend", descripcion="Java y Docker")
    b = world.job(titulo="Dev", descripcion="Java, Docker y Kubernetes")
    c = world.job(titulo="Ops", descripcion="Kubernetes")
    for job, score in ((a, 90), (b, 70), (c, 50)):
        world.match(prof, job, score=score)
    g = client.get("/api/skills-graph").json()
    skills = {s["nombre"]: s for s in g["habilidades"]}
    assert skills["Java"]["tiene"] and skills["Java"]["grado"] == 2
    assert skills["Python"]["tiene"] and skills["Python"]["grado"] == 0
    assert not skills["Docker"]["tiene"] and skills["Docker"]["grado"] == 2
    assert not skills["Kubernetes"]["tiene"] and skills["Kubernetes"]["grado"] == 2
    edges = {(e["habilidad"], e["job_id"]) for e in g["aristas"]}
    assert ("Java", a.id) in edges and ("Java", b.id) in edges and ("Java", c.id) not in edges
    assert ("Docker", a.id) in edges
    assert {o["job_id"] for o in g["ofertas"]} == {a.id, b.id, c.id}
    assert next(o for o in g["ofertas"] if o["job_id"] == a.id)["puntaje"] == 90


def test_graph_maximo_8_faltantes(client, session, world):
    prof = save_profile(session, "Java")
    missing = ["docker", "kubernetes", "aws", "azure", "terraform", "jenkins", "linux", "react", "angular", "vue"]
    counts = [6, 5, 5, 4, 4, 3, 3, 3, 1, 1]  # 35 ofertas: caben en el top 40; las 2 últimas quedan fuera
    for skill, count in zip(missing, counts):
        for _ in range(count):
            world.match(prof, world.job(descripcion=f"Java y {skill}"), score=60)
    g = client.get("/api/skills-graph").json()
    faltantes = [s for s in g["habilidades"] if not s["tiene"]]
    assert len(faltantes) == 8
    assert {s["nombre"].lower() for s in faltantes} == set(missing[:8])


def test_los_idiomas_del_perfil_cuentan_como_propios(client, session, world):
    perfil = Profile.model_validate({**DRAFT, "preferences": DEFAULT_PREFERENCES.model_dump(),
                                     "skills": [{"name": "Java", "level": "intermedio", "evidence": "x"}],
                                     "languages": [{"name": "Inglés", "level": "B2"}]})
    prof = store.save(session, perfil, "cv", FakeEmbedder())
    world.match(prof, world.job(descripcion="Java and fluent English required"), score=80)
    skills = {s["nombre"]: s for s in client.get("/api/skills-graph").json()["habilidades"]}
    assert "English" not in skills or skills["English"]["tiene"]
    assert skills["Inglés"]["tiene"] and skills["Inglés"]["grado"] == 1
