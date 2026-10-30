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


def test_redact_wrapped_email():
    out = redact("Ana Mora\nCorreo: anamora\n@gmail.com\nSkills: Java")
    assert "anamora" not in out.lower() and "@" not in out and "Java" in out


def test_redact_email_split_at_tld():
    out = redact("Ana Mora\nana.mora@gmail.\ncom\nSkills: Java")
    assert "ana.mora" not in out and "Java" in out


def test_redact_wrapped_phone():
    out = redact("Ana Mora\nTel: +506 8888\n1234\nSkills: Java")
    assert "8888" not in out and "1234" not in out and "Java" in out


def test_redact_wrapped_linkedin_handle():
    out = redact("Ana Mora\nPerfil: linkedin.com/in/\nana-mora-rojas\nSkills: Java")
    assert "rojas" not in out.lower() and "Java" in out


def test_redact_curriculum_header_then_name():
    out = redact("CURRICULUM VITAE\nAna Mora Rojas\nSkills: Java")
    assert "Mora" not in out and "Java" in out


def test_redact_name_repeated_elsewhere():
    out = redact("Ana Mora Rojas\nProyecto personal de Mora Rojas en Java")
    assert "Mora" not in out and "Rojas" not in out and "Java" in out


def test_redact_keeps_year_lines():
    assert "2025 - 2026" in redact("Ana Mora\nUCR 2025 - 2026")
