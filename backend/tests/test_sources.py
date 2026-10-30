from sqlalchemy import select

from moneyplease.config import Settings
from moneyplease.db.models import Source
from moneyplease.ingest.sources import sync

YAML = """
- nombre: Uno
  ats: greenhouse
  slug: uno
  careers_url: https://uno.example
  activa: true
- nombre: Dos
  ats: lever
  slug: dos
  careers_url: https://dos.example
  activa: true
"""


def settings(tmp_path, text=YAML):
    p = tmp_path / "companies.yaml"
    p.write_text(text, encoding="utf-8")
    return Settings(_env_file=None, companies_path=p)


def by_key(session):
    session.expire_all()
    return {s.key: s for s in session.scalars(select(Source))}


def test_sync_creates_sources(session, tmp_path):
    sync(session, settings(tmp_path))
    src = by_key(session)
    assert set(src) == {"greenhouse:uno", "lever:dos", "jsearch", "gmail"}
    assert src["greenhouse:uno"].tipo == "ats"
    assert src["greenhouse:uno"].nombre == "Uno"
    assert src["greenhouse:uno"].config_json == {"slug": "uno", "careers_url": "https://uno.example"}
    assert src["jsearch"].config_json["queries"]
    assert src["gmail"].tipo == "email"


def test_sync_keeps_state_config(session, tmp_path):
    s = settings(tmp_path)
    sync(session, s)
    js = by_key(session)["jsearch"]
    js.config_json = {**js.config_json, "query_index": 7}
    session.commit()
    sync(session, s)
    assert by_key(session)["jsearch"].config_json["query_index"] == 7


def test_sync_deactivates_removed_company(session, tmp_path):
    sync(session, settings(tmp_path))
    sync(session, settings(tmp_path, YAML.split("- nombre: Dos")[0]))
    dos = by_key(session)["lever:dos"]
    assert dos.activa is False
    assert dos.desactivada_motivo == "quitada de companies.yaml"


def test_sync_does_not_reactivate_404_source(session, tmp_path):
    s = settings(tmp_path)
    sync(session, s)
    uno = by_key(session)["greenhouse:uno"]
    uno.activa, uno.desactivada_motivo = False, "404 https://..."
    session.commit()
    sync(session, s)
    assert by_key(session)["greenhouse:uno"].activa is False


def test_sync_reactivates_after_yaml_toggle(session, tmp_path):
    s = settings(tmp_path)
    sync(session, s)
    uno = by_key(session)["greenhouse:uno"]
    uno.activa, uno.desactivada_motivo = False, "404 https://..."
    session.commit()
    sync(session, settings(tmp_path, YAML.replace("activa: true", "activa: false", 1)))
    sync(session, settings(tmp_path))
    uno = by_key(session)["greenhouse:uno"]
    assert uno.activa is True and uno.desactivada_motivo is None
