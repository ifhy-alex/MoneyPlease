import pytest
from pydantic import ValidationError

from moneyplease.profile.schema import DEFAULT_PREFERENCES, Profile

EXAMPLE = {
    "skills": [{"name": "Spring Boot", "level": "intermedio", "evidence": "Gym Management System"}],
    "languages": [{"name": "Inglés", "level": "B2"}],
    "experience_months": 5,
    "seniority_target": ["practica", "junior"],
    "roles_target": ["Backend Developer", "Data Engineer"],
    "summary": "Estudiante de Informática Empresarial.",
    "preferences": DEFAULT_PREFERENCES.model_dump(),
}


def with_change(path, value):
    data = {**EXAMPLE, "preferences": dict(EXAMPLE["preferences"]), "skills": [dict(EXAMPLE["skills"][0])]}
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return data


def test_valid_profile():
    assert Profile.model_validate(EXAMPLE).experience_months == 5


def test_default_preferences_values():
    p = DEFAULT_PREFERENCES
    assert p.modalidad == ["presencial", "hibrido", "remoto"]
    assert p.ubicaciones == ["Cartago", "San José", "Heredia", "Alajuela"]
    assert p.remoto_abierto is True
    assert "senior" in p.excluir_titulo and "5+ years" in p.excluir_palabras


def test_rejects_bad_enum():
    with pytest.raises(ValidationError):
        Profile.model_validate(with_change(["skills", 0, "level"], "experto"))


def test_rejects_english_modalidad():
    with pytest.raises(ValidationError) as exc:
        Profile.model_validate(with_change(["preferences", "modalidad"], ["remote"]))
    locs = [e["loc"] for e in exc.value.errors()]
    assert any(loc[:2] == ("preferences", "modalidad") for loc in locs)


def test_rejects_unknown_provincia():
    with pytest.raises(ValidationError):
        Profile.model_validate(with_change(["preferences", "ubicaciones"], ["Madrid"]))


def test_rejects_negative_experience():
    with pytest.raises(ValidationError):
        Profile.model_validate(with_change(["experience_months"], -1))


def test_llm_view_has_no_preferences():
    view = Profile.model_validate(EXAMPLE).llm_view()
    assert "preferences" not in view
    assert set(view) == {"skills", "languages", "experience_months", "roles_target", "seniority_target", "summary"}


def test_embedding_text_prefix():
    text = Profile.model_validate(EXAMPLE).embedding_text()
    assert text.startswith("query: ") and "Spring Boot" in text and "Backend Developer" in text
