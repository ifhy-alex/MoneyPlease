from datetime import UTC, datetime

import pytest

from moneyplease.ingest.base import RawJob
from moneyplease.ingest.normalize import detect_modalidad, detect_ubicacion, job_hash, normalize


def raw(title="Dev", location=None, description="", **kw):
    return RawJob(external_id="1", title=title, company="ACME", location=location,
                  description=description, url="https://x", published_at=None, raw={}, **kw)


def test_hash_ignores_accents_case_spacing():
    assert job_hash("ACME", "Práctica Profesional", "San José, CR") == \
        job_hash("acme", "practica  profesional", "san jose cr")


def test_hash_differs_by_location():
    assert job_hash("ACME", "Dev", "Heredia") != job_hash("ACME", "Dev", "Cartago")


@pytest.mark.parametrize("title,location,expected", [
    ("Backend Intern (Remote)", None, "remoto"),
    ("Desarrollador", "Híbrido - Heredia", "hibrido"),
    ("Dev", "Remote / Hybrid", "hibrido"),
    ("Analista", "On-site, Cartago", "presencial"),
    ("Analista", "Cartago", "desconocida"),
])
def test_modalidad_keywords(title, location, expected):
    assert detect_modalidad(raw(title, location)) == expected


def test_modalidad_hints_win():
    assert detect_modalidad(raw("On-site Dev", remote_hint=True)) == "remoto"
    assert detect_modalidad(raw("Dev", workplace_hint="hybrid")) == "hibrido"


@pytest.mark.parametrize("text,expected", [
    ("Escazú, San José", ("San José", "CR")),
    ("Heredia, Costa Rica", ("Heredia", "CR")),
    ("Costa Rica", (None, "CR")),
    ("Belén", ("Heredia", "CR")),
    ("Remote - US", (None, None)),
])
def test_detect_ubicacion(text, expected):
    assert detect_ubicacion(text) == expected


def test_normalize_missing_fields():
    row = normalize(raw(location=None, description=""))
    assert row["ubicacion"] == ""
    assert row["publicado_en"] is None
    assert row["descripcion"] == ""


def test_normalize_strips_html():
    row = normalize(raw(description="<p>Hola</p><ul><li>Python</li></ul>"))
    assert "Hola" in row["descripcion"] and "Python" in row["descripcion"]
    assert "<" not in row["descripcion"]


def test_normalize_naive_date_is_utc():
    j = raw()
    j.published_at = datetime(2026, 1, 1, 12)
    assert normalize(j)["publicado_en"] == datetime(2026, 1, 1, 12, tzinfo=UTC)


@pytest.mark.parametrize("text", [
    "San Jose, CA",
    "Santa Ana, California",
    "Santo Domingo, Dominican Republic",
    "Atenas, Grecia",
    "San Pedro Garza Garcia, Mexico",
])
def test_ambiguous_places_outside_cr(text):
    assert detect_ubicacion(text) == (None, None)


def test_ambiguous_place_with_cr_context():
    assert detect_ubicacion("San Pedro, Costa Rica") == ("San José", "CR")
    assert detect_ubicacion("Santo Domingo, Heredia") == ("Heredia", "CR")


def test_country_hint_fills_unrecognized_place():
    row = normalize(raw(location="Sabana Norte", country_hint="CR"))
    assert (row["pais"], row["provincia"]) == ("CR", None)


def test_country_hint_does_not_override_detected_place():
    assert normalize(raw(location="Heredia, Costa Rica", country_hint="CR"))["provincia"] == "Heredia"
    assert normalize(raw(location="Sabana Norte"))["pais"] is None
