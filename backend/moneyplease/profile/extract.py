import re
from pathlib import Path

PHONE = re.compile(r"\+?\d[\d\s\-()]{7,}\d")
YEAR_RANGE = re.compile(r"(19|20)\d{2}\s*-\s*(19|20)\d{2}")
URL = re.compile(r"https?://\S+|www\.\S+|(?:github|linkedin)\.com/\S*", re.IGNORECASE)
HANDLE_LINE = re.compile(r"^\s*(linkedin|github)\s*:.*$", re.IGNORECASE)
CONTACT_LABEL = re.compile(r"\b(correo|e-?mail|phone|tel[eé]fono|tel|celular|m[oó]vil|whatsapp)\b\s*:?",
                           re.IGNORECASE)
CUT_PROFILE_LINK = re.compile(r"(linkedin\.com/in|github\.com)/?\s*$", re.IGNORECASE)
NUMERIC_FRAGMENT = re.compile(r"^[\d\s+()\-.]*\d{3,}[\d\s+()\-.]*$")
CV_HEADER = re.compile(r"^\s*(curr[ií]culum( vitae)?|vitae|resume|r[eé]sum[eé]|hoja de vida|cv)\s*$", re.IGNORECASE)
NAME_TOKEN = re.compile(r"[^\W\d_]{3,}")


def pdf_text(path: Path) -> str:
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _has_phone(line: str) -> bool:
    return any(not YEAR_RANGE.fullmatch(m.group().strip()) for m in PHONE.finditer(line))


def _is_contact(line: str) -> bool:
    return "@" in line or _has_phone(line) or bool(CONTACT_LABEL.search(line))


def _mask_handles(line: str) -> str:
    # "LinkedIn: Nombre | GitHub:github.com/x" → cada handle queda como [enlace]
    return " | ".join(f"{part.split(':', 1)[0].strip()}: [enlace]" if ":" in part else part
                      for part in line.split("|"))


def _name_index(lines: list[str]) -> int | None:
    non_empty = [i for i, line in enumerate(lines) if line.strip()]
    if not non_empty:
        return None
    if CV_HEADER.match(lines[non_empty[0]]) and len(non_empty) > 1:
        return non_empty[1]
    return non_empty[0]


def redact(text: str) -> str:
    """Quita nombre, correos, teléfonos y enlaces antes de enviar el CV a un servicio externo.

    pdfplumber suele partir las líneas de contacto, así que también se eliminan los fragmentos
    numéricos pegados a una línea de contacto y la línea que sigue a un enlace de perfil cortado.
    """
    lines = text.splitlines()
    name_i = _name_index(lines)
    name_tokens = NAME_TOKEN.findall(lines[name_i]) if name_i is not None else []
    removed = [False] * len(lines)
    for i, line in enumerate(lines):
        if i == name_i or _is_contact(line):
            removed[i] = True
        elif i > 0 and CUT_PROFILE_LINK.search(lines[i - 1]):
            removed[i] = True
    for i, line in enumerate(lines):
        near_removed = (i > 0 and removed[i - 1]) or (i + 1 < len(lines) and removed[i + 1])
        if not removed[i] and near_removed and NUMERIC_FRAGMENT.match(line) and not YEAR_RANGE.search(line):
            removed[i] = True
    out = []
    for i, line in enumerate(lines):
        if removed[i]:
            continue
        if HANDLE_LINE.match(line):
            line = _mask_handles(line)
        line = URL.sub("[enlace]", line)
        for token in name_tokens:
            line = re.sub(rf"\b{re.escape(token)}\b", "[nombre]", line, flags=re.IGNORECASE)
        out.append(line)
    return "\n".join(out)
