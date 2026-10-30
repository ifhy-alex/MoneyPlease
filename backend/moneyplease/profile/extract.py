import re
from pathlib import Path

EMAIL = re.compile(r"\S+@\S+\.\w+")
PHONE = re.compile(r"\+?\d[\d\s\-()]{7,}\d")
YEAR_RANGE = re.compile(r"(19|20)\d{2}\s*-\s*(19|20)\d{2}")
URL = re.compile(r"https?://\S+|www\.\S+|(?:github|linkedin)\.com/\S*", re.IGNORECASE)
HANDLE_LINE = re.compile(r"^\s*(linkedin|github)\s*:.*$", re.IGNORECASE)


def pdf_text(path: Path) -> str:
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _has_phone(line: str) -> bool:
    return any(not YEAR_RANGE.fullmatch(m.group().strip()) for m in PHONE.finditer(line))


def _mask_handles(line: str) -> str:
    # "LinkedIn: Nombre | GitHub:github.com/x" → cada handle queda como [enlace]
    return " | ".join(f"{part.split(':', 1)[0].strip()}: [enlace]" if ":" in part else part
                      for part in line.split("|"))


def redact(text: str) -> str:
    """Quita nombre, correos, teléfonos y enlaces antes de enviar el CV a un servicio externo."""
    lines = text.splitlines()
    first = next((i for i, line in enumerate(lines) if line.strip()), None)
    out = []
    for i, line in enumerate(lines):
        if i == first or EMAIL.search(line) or _has_phone(line):
            continue
        if HANDLE_LINE.match(line):
            line = _mask_handles(line)
        out.append(URL.sub("[enlace]", line))
    return "\n".join(out)
