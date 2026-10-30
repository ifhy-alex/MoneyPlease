import pytest

from moneyplease.db.models import Job
from moneyplease.matching.embed import E5Embedder, job_text
from tests.fakes import cosine


def test_job_text_handles_nulls():
    job = Job(titulo="Backend Intern", empresa="ACME", ubicacion=None, descripcion=None)
    text = job_text(job)
    assert text.startswith("passage: Backend Intern | ACME")
    assert "None" not in text


@pytest.mark.slow
def test_e5_semantic_order():
    e = E5Embedder()
    perfil, backend, ventas = e.embed([
        "query: desarrollador backend Java Spring Boot",
        "passage: Backend Developer | Java, Spring Boot, microservices, REST APIs",
        "passage: Sales Representative | retail, customer service, store sales",
    ])
    assert len(perfil) == 384
    assert cosine(perfil, backend) > cosine(perfil, ventas)
