import pytest

from moneyplease.db.models import Source
from moneyplease.scope import scope_of


@pytest.mark.parametrize("fuente,pais,ambito", [
    ("workday:hpe", "CR", "cr"),
    ("greenhouse:konradgroup", "CR", "cr"),
    ("greenhouse:gitlab", None, "internacional"),   # remoto abierto desde el extranjero
    ("greenhouse:elastic", "US", "internacional"),
    ("jsearch", None, "cr"),                         # JSearch solo busca con country=cr
    ("gmail", "CR", "cr"),
    ("gmail", None, "cr"),                           # las alertas vienen de búsquedas en Costa Rica
    ("himalayas", "CR", "internacional"),            # "Remoto · abierto a Costa Rica", pero la empresa es de afuera
])
def test_scope_of(fuente, pais, ambito):
    assert scope_of(fuente, pais) == ambito


@pytest.fixture
def mixed(world, session):
    prof = world.profile()
    remote = Source(key="himalayas", nombre="Himalayas", tipo="api", config_json={})
    jsearch = Source(key="jsearch", nombre="JSearch", tipo="api", config_json={})
    session.add_all([remote, jsearch])
    session.commit()
    world.match(prof, world.job(titulo="Heredia Intern"), score=90, fit="practica")
    world.match(prof, world.job(titulo="Remote Intern", source_id=remote.id, ubicacion="Remoto · abierto a Costa Rica",
                                modalidad="remoto", provincia=None), score=85, fit="practica")
    world.match(prof, world.job(titulo="GitLab Remote", pais=None, provincia=None, modalidad="remoto",
                                ubicacion="Remote"), score=70, fit="junior")
    world.match(prof, world.job(titulo="Moody's sin lugar", source_id=jsearch.id, pais=None, provincia=None,
                                ubicacion="", modalidad="remoto"), score=82, fit="practica")
    return prof


def titles(resp):
    return [i["job"]["titulo"] for i in resp.json()["items"]] if "items" in resp.json() \
        else [i["job"]["titulo"] for i in resp.json()]


def test_top_by_scope(client, mixed):
    assert titles(client.get("/api/top?ambito=cr")) == ["Heredia Intern", "Moody's sin lugar"]
    assert titles(client.get("/api/top?ambito=internacional")) == ["Remote Intern", "GitLab Remote"]
    assert len(client.get("/api/top").json()) == 4


def test_top_items_carry_scope(client, mixed):
    scopes = {i["job"]["titulo"]: i["job"]["ambito"] for i in client.get("/api/top").json()}
    assert scopes == {"Heredia Intern": "cr", "Remote Intern": "internacional", "GitLab Remote": "internacional",
                      "Moody's sin lugar": "cr"}


def test_explore_by_scope_and_score(client, mixed):
    assert titles(client.get("/api/jobs?ambito=internacional&min_score=80")) == ["Remote Intern"]
    assert titles(client.get("/api/jobs?ambito=cr&min_score=80")) == ["Heredia Intern", "Moody's sin lugar"]


def test_explore_solo_cr_still_works(client, mixed):
    assert titles(client.get("/api/jobs?solo_cr=true")) == titles(client.get("/api/jobs?ambito=cr"))


def test_scope_invalid_422(client, mixed):
    assert client.get("/api/top?ambito=marte").status_code == 422
