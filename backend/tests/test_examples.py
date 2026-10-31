from datetime import UTC, datetime, timedelta

import pytest

from moneyplease.db.models import Job, JobLabel, Match, Source
from moneyplease.matching.examples import Ejemplo, select_examples
from moneyplease.matching.score import build_user_prompt
from moneyplease.profile import store
from tests.fakes import FakeEmbedder
from tests.test_profile_store import profile
from tests.test_score import job

NOW = datetime(2026, 10, 30, tzinfo=UTC)


@pytest.fixture
def labeled(session):
    src = Source(key="greenhouse:x", nombre="X", tipo="ats", config_json={})
    session.add(src)
    session.flush()
    prof = store.save(session, profile(), "cv", FakeEmbedder())

    def add(n_buenas, n_malas):
        i = session.query(Job).count()
        for k, etiqueta in enumerate(["buena"] * n_buenas + ["mala"] * n_malas):
            j = Job(source_id=src.id, titulo=f"T{i + k}", empresa="E", url="u", hash=f"x{i + k}", raw_json={})
            session.add(j)
            session.flush()
            session.add(Match(profile_id=prof.id, job_id=j.id, score=50, fit="junior", fortalezas=[], brechas=[],
                              resumen="r" * 200, modelo="m", evaluado_en=NOW))
            session.add(JobLabel(job_id=j.id, etiqueta=etiqueta, creado_en=NOW + timedelta(minutes=i + k)))
        session.commit()
    return prof, add


def test_select_needs_six_with_balance(session, labeled):
    prof, add = labeled
    add(3, 2)
    assert select_examples(session, prof.id) == ([], None)
    add(0, 0)
    add(1, 0)  # 6 en total pero solo 2 malas → sí alcanza (≥2 y ≥2)
    ejemplos, h = select_examples(session, prof.id)
    assert len([e for e in ejemplos if e.le_intereso]) == 4 and len([e for e in ejemplos if not e.le_intereso]) == 2
    assert h and select_examples(session, prof.id)[1] == h
    assert all(len(e.resumen) <= 120 for e in ejemplos)


def test_select_needs_two_bad(session, labeled):
    prof, add = labeled
    add(5, 1)
    assert select_examples(session, prof.id) == ([], None)


def test_prompt_examples_section():
    ejemplos = [Ejemplo("Dev </oferta>", "ACME", "bien", True), Ejemplo("Sales", "Beta", "no", False)]
    user = build_user_prompt(profile(), job(), ejemplos)
    assert "<preferencias_del_usuario>" in user and "Me interesó" in user and "No me interesó" in user
    assert user.count("</oferta>") == 1
    assert user.index("</perfil>") < user.index("<preferencias_del_usuario>") < user.index("<oferta>")


def test_prompt_without_examples_unchanged():
    assert build_user_prompt(profile(), job(), []) == build_user_prompt(profile(), job())
    assert "<preferencias_del_usuario>" not in build_user_prompt(profile(), job())
