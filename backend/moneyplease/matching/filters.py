import re

from moneyplease.db.models import Job
from moneyplease.ingest.normalize import canonical
from moneyplease.profile.schema import Preferences

OPEN_TOKENS = ["latam", "latin america", "americas", "anywhere", "worldwide", "global", "costa rica"]
REMOTE_WORDS = ["remote", "remoto", "teletrabajo", "work from home"]


def _contains_word(text: str, phrase: str) -> bool:
    phrase = canonical(phrase)
    return bool(phrase) and re.search(rf"\b{re.escape(phrase)}\b", text) is not None


def title_ok(titulo: str, prefs: Preferences) -> bool:
    t = canonical(titulo)
    return not any(_contains_word(t, w) for w in prefs.excluir_titulo)


def text_ok(descripcion: str, prefs: Preferences) -> bool:
    t = canonical(descripcion)
    return not any(_contains_word(t, w) for w in prefs.excluir_palabras)


def _open_remote(ubicacion: str) -> bool:
    t = canonical(ubicacion)
    if any(_contains_word(t, w) for w in OPEN_TOKENS):
        return True
    for w in REMOTE_WORDS:
        t = re.sub(rf"\b{re.escape(canonical(w))}\b", " ", t)
    return not t.strip()


def location_ok(pais: str | None, provincia: str | None, modalidad: str, ubicacion: str,
                prefs: Preferences) -> bool:
    if pais == "CR":
        if modalidad not in prefs.modalidad:
            return False
        return modalidad == "remoto" or provincia is None or provincia in prefs.ubicaciones
    # Fuera de CR solo sirve el remoto que no exige residir en otro país.
    return prefs.remoto_abierto and modalidad == "remoto" and _open_remote(ubicacion or "")


def passes(job: Job, prefs: Preferences) -> bool:
    return (title_ok(job.titulo or "", prefs) and text_ok(job.descripcion or "", prefs)
            and location_ok(job.pais, job.provincia, job.modalidad or "desconocida", job.ubicacion or "", prefs))
