import pytest

from moneyplease.matching.llm import LLMError
from moneyplease.profile import store
from moneyplease.profile.generate import draft_from_text
from moneyplease.profile.schema import DEFAULT_PREFERENCES, Profile
from tests.fakes import FakeEmbedder, FakeLLMProvider
from tests.test_extract import CV

DRAFT = {
    "skills": [{"name": "Spring Boot", "level": "intermedio", "evidence": "Gym Management System"}],
    "languages": [{"name": "Inglés", "level": "B2"}],
    "experience_months": 5,
    "seniority_target": ["practica", "junior"],
    "roles_target": ["Backend Developer"],
    "summary": "Estudiante de Informática Empresarial.",
}


def profile():
    return Profile.model_validate({**DRAFT, "preferences": DEFAULT_PREFERENCES.model_dump()})


def test_draft_adds_default_preferences():
    p = draft_from_text("texto", FakeLLMProvider([DRAFT]))
    assert p.preferences == DEFAULT_PREFERENCES
    assert p.skills[0].name == "Spring Boot"


def test_draft_retries_once_then_fails():
    bad = {**DRAFT, "experience_months": -3}
    fake = FakeLLMProvider([bad, bad])
    with pytest.raises(LLMError):
        draft_from_text("texto", fake)
    assert len(fake.calls) == 2


def test_draft_retry_succeeds():
    fake = FakeLLMProvider([LLMError("x"), DRAFT])
    assert draft_from_text("texto", fake).experience_months == 5


def test_write_yaml_no_overwrite(tmp_path):
    path = tmp_path / "profile.yaml"
    store.write_yaml(profile(), path)
    with pytest.raises(FileExistsError):
        store.write_yaml(profile(), path)
    store.write_yaml(profile(), path, force=True)
    assert store.read_yaml(path) == profile()


def test_yaml_keeps_accents(tmp_path):
    path = tmp_path / "profile.yaml"
    store.write_yaml(profile(), path)
    assert "San José" in path.read_text(encoding="utf-8")


def test_read_yaml_reports_field_path(tmp_path):
    path = tmp_path / "profile.yaml"
    store.write_yaml(profile(), path)
    path.write_text(path.read_text(encoding="utf-8").replace("- remoto", "- remote"), encoding="utf-8")
    with pytest.raises(store.ProfileError) as exc:
        store.read_yaml(path)
    assert "preferences.modalidad" in str(exc.value)


def test_read_yaml_tabs_is_profile_error(tmp_path):
    path = tmp_path / "profile.yaml"
    path.write_text("skills:\n\t- name: Java\n", encoding="utf-8")
    with pytest.raises(store.ProfileError):
        store.read_yaml(path)


def test_save_increments_version(session, session_factory):
    e = FakeEmbedder()
    first = store.save(session, profile(), "cv", e)
    second = store.save(session, profile(), "cv", e)
    assert (first.version, second.version) == (1, 2)
    assert store.active(session).version == 2
    assert len(store.active(session).embedding) == 384


def test_active_none_without_profiles(session):
    assert store.active(session) is None


def test_from_cv_writes_redacted_txt(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "pdf_text", lambda path: CV)
    fake = FakeLLMProvider([DRAFT])
    out = store.from_cv(tmp_path / "cv.pdf", tmp_path, fake, force=False)
    assert out == tmp_path / "profile.yaml" and out.exists()
    cv_txt = (tmp_path / "cv.txt").read_text(encoding="utf-8")
    assert "@" not in cv_txt
    sent = fake.calls[0][1]
    assert "@" not in sent and "Juana" not in sent
