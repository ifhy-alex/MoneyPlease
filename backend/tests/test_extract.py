from moneyplease.profile.extract import redact

CV = """Juana Pérez Mora
Location: Cartago | Phone: +506 8888-1234 | juana@example.com |
LinkedIn: Juana Perez | GitHub:github.com/juana
PROFESSIONAL PROFILE
Student building APIs. Portfolio: https://juana.dev/portfolio
GTMS | Supervised by: Ana Ruiz ana.ruiz@empresa.com
• Built Spring Boot APIs
"""


def test_redact_removes_name_line():
    assert "Juana" not in redact(CV)


def test_redact_removes_contact_lines():
    out = redact(CV)
    assert "@" not in out and "8888" not in out and "Ana Ruiz" not in out


def test_redact_masks_links():
    out = redact(CV)
    assert "github.com/juana" not in out
    assert "juana.dev" not in out
    assert "[enlace]" in out


def test_redact_keeps_technical_text():
    out = redact(CV)
    assert "Spring Boot" in out and "PROFESSIONAL PROFILE" in out


def test_redact_tolerates_broken_encoding():
    text = "Alexander Jes�s Fallas\nPhone: +506\n8888-1234\nSkills: Java"
    out = redact(text)
    assert "8888-1234" not in out
    assert "Java" in out
