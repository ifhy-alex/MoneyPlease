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
