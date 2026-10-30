# TODO(usuario): reemplazar los .eml por alertas reales anonimizadas cuando lleguen las primeras;
# estos parsers son la parte que más probablemente se rompa.
import email
from email import policy
from pathlib import Path

from moneyplease.ingest.connectors.email_parsers import parse_alert, parse_indeed, parse_linkedin

FIX = Path(__file__).parent / "fixtures"


def html_of(name: str) -> str:
    msg = email.message_from_bytes((FIX / name).read_bytes(), policy=policy.default)
    return msg.get_body(("html",)).get_content()


def test_parse_linkedin_fixture():
    jobs = parse_linkedin(html_of("linkedin_alert.eml"))
    assert [j.title for j in jobs] == ["Desarrollador Junior", "Data Engineer Intern", "Backend Developer (Remote)"]
    assert jobs[0].company == "Empresa Uno"
    assert jobs[0].location == "Heredia, Heredia, Costa Rica"
    assert jobs[0].external_id == "4100000001"
    assert jobs[0].url == "https://www.linkedin.com/jobs/view/4100000001/"
    assert all("trackingId" not in j.url for j in jobs)


def test_parse_indeed_fixture():
    jobs = parse_indeed(html_of("indeed_alert.eml"))
    assert [j.title for j in jobs] == ["Practicante de Desarrollo de Software", "Analista de Datos Junior"]
    assert jobs[0].company == "Empresa Cuatro"
    assert jobs[0].location == "Cartago, Cartago"
    assert jobs[1].url == "https://cr.indeed.com/viewjob?jk=9f8e7d6c5b4a3f2e"


def test_parse_alert_dispatches_by_sender():
    assert len(parse_alert("LinkedIn <jobalerts-noreply@linkedin.com>", html_of("linkedin_alert.eml"))) == 3
    assert len(parse_alert("alert@indeed.com", html_of("indeed_alert.eml"))) == 2


def test_parse_unknown_sender_empty():
    assert parse_alert("x@y.com", html_of("linkedin_alert.eml")) == []


def test_parse_garbage_html_empty():
    assert parse_alert("jobalerts-noreply@linkedin.com", "<html>") == []
    assert parse_alert("alert@indeed.com", "") == []
