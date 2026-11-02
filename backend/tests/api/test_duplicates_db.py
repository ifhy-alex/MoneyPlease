from moneyplease.duplicates import duplicates_of
from tests.api.test_map import near


def test_duplicates_of_encuentra_la_copia_activa_con_embedding(world, session):
    prof = world.profile()
    a = world.job(empresa="HPE", embedding=near(prof.embedding, 0.9, 1))
    b = world.job(empresa="hpe ", embedding=list(a.embedding))
    world.job(empresa="HPE", embedding=list(a.embedding), estado="closed")
    world.job(empresa="HPE", embedding=None)
    world.job(empresa="Abbott", embedding=list(a.embedding))
    assert [j.id for j in duplicates_of(session, a)] == [b.id]
    assert [j.id for j in duplicates_of(session, b)] == [a.id]


def test_sin_embedding_no_tiene_duplicados(world, session):
    world.profile()
    lone = world.job(embedding=None)
    assert duplicates_of(session, lone) == []


def _chain(world, prof):
    # A~B y B~C (0.9925), pero A y C solo a 0.97: igual son un mismo grupo.
    import math
    ang = math.acos(0.9925)
    base = [0.0] * 384

    def vec(t):
        v = list(base)
        v[0], v[1] = math.cos(t), math.sin(t)
        return v
    return [world.job(empresa="HPE", embedding=vec(k * ang)) for k in range(3)]


def test_duplicates_of_sigue_la_cadena(world, session):
    from moneyplease.duplicates import duplicates_of
    prof = world.profile()
    a, b, c = _chain(world, prof)
    assert [j.id for j in duplicates_of(session, a)] == [b.id, c.id]


def test_top_y_feedback_tratan_la_cadena_como_un_grupo(client, world, session):
    from moneyplease.db.models import JobLabel
    prof = world.profile()
    a, b, c = _chain(world, prof)
    for job, score in ((a, 90), (b, 80), (c, 70)):
        world.match(prof, job, score=score)
    ids = [i["job"]["id"] for i in client.get("/api/top").json()]
    assert ids == [a.id]
    client.post(f"/api/jobs/{a.id}/feedback", json={"valor": "no_interesa"})
    session.expire_all()
    assert session.get(JobLabel, c.id).etiqueta == "mala"
