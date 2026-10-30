from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from moneyplease.config import Settings
from moneyplease.db.models import Source
from moneyplease.ingest.connectors.jsearch import DEFAULT_QUERIES

REMOVED = "quitada de companies.yaml"
DISABLED = "desactivada en companies.yaml"
YAML_REASONS = {REMOVED, DISABLED}


def load_companies(path: Path) -> list[dict]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []


def _set_active(src: Source, wanted: bool, reason: str) -> None:
    if not wanted:
        src.activa, src.desactivada_motivo = False, reason
    elif src.desactivada_motivo is None or src.desactivada_motivo in YAML_REASONS:
        # Una fuente desactivada por 404/robots solo vuelve si se desactiva y reactiva en el YAML.
        src.activa, src.desactivada_motivo = True, None


def sync(session: Session, settings: Settings) -> None:
    existing = {s.key: s for s in session.scalars(select(Source))}
    wanted: set[str] = set()
    for c in load_companies(settings.companies_path):
        key = f"{c['ats']}:{c['slug']}"
        wanted.add(key)
        src = existing.get(key)
        if src is None:
            src = Source(key=key, tipo="ats", config_json={}, activa=True)
            session.add(src)
        src.nombre = c["nombre"]
        src.config_json = {**(src.config_json or {}), "slug": c["slug"], "careers_url": c.get("careers_url")}
        _set_active(src, c.get("activa", True), DISABLED)
    for src in existing.values():
        if src.tipo == "ats" and src.key not in wanted:
            _set_active(src, False, REMOVED)
    if "jsearch" not in existing:
        session.add(Source(key="jsearch", nombre="JSearch", tipo="api", activa=True,
                           config_json={"queries": DEFAULT_QUERIES}))
    if "gmail" not in existing:
        session.add(Source(key="gmail", nombre="Alertas de Gmail", tipo="email", activa=True, config_json={}))
    session.commit()
