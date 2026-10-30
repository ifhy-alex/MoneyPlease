import pytest

from moneyplease.db.models import Job
from moneyplease.matching.filters import location_ok, passes, text_ok, title_ok
from moneyplease.profile.schema import DEFAULT_PREFERENCES as PREFS


@pytest.mark.parametrize("titulo,ok", [
    ("Senior Backend Engineer", False),
    ("Sr. Data Analyst", False),
    ("Head of Data", False),
    ("Solutions Architect", False),
    ("Engineering Manager", False),
    ("Software Engineer", True),
    ("Backend Intern", True),
    ("Leadership Program Intern", True),
])
def test_title_ok(titulo, ok):
    assert title_ok(titulo, PREFS) is ok


@pytest.mark.parametrize("descripcion,ok", [
    ("Requires 5+ years of experience", False),
    ("Buscamos más de 5 años de experiencia", False),
    ("1-2 years of experience", True),
    ("", True),
])
def test_text_ok(descripcion, ok):
    assert text_ok(descripcion, PREFS) is ok


@pytest.mark.parametrize("pais,provincia,modalidad,ubicacion,ok", [
    (None, None, "remoto", "Remote - US", False),
    (None, None, "remoto", "Remote, UK", False),
    (None, None, "remoto", "LATAM (Remote)", True),
    (None, None, "remoto", "Anywhere", True),
    (None, None, "remoto", "Remote", True),
    (None, None, "remoto", "", True),
    (None, None, "hibrido", "London", False),
    (None, None, "desconocida", "Remote", False),
    ("CR", "Heredia", "hibrido", "Heredia, Costa Rica", True),
    ("CR", "Limón", "presencial", "Limón, Costa Rica", False),
    ("CR", "Puntarenas", "remoto", "Puntarenas", True),
    ("CR", None, "desconocida", "Costa Rica", False),
    ("CR", None, "hibrido", "Costa Rica", True),
])
def test_location_ok(pais, provincia, modalidad, ubicacion, ok):
    assert location_ok(pais, provincia, modalidad, ubicacion, PREFS) is ok


def test_remoto_abierto_false_blocks_abroad():
    prefs = PREFS.model_copy(update={"remoto_abierto": False})
    assert location_ok(None, None, "remoto", "Anywhere", prefs) is False


def test_passes_combines_all():
    job = Job(titulo="Backend Intern", descripcion="Java", pais="CR", provincia="Heredia",
              modalidad="hibrido", ubicacion="Heredia")
    assert passes(job, PREFS)
    job.titulo = "Senior Backend Engineer"
    assert not passes(job, PREFS)
