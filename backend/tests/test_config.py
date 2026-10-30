from moneyplease.config import Settings


def test_defaults_and_env_override(monkeypatch):
    monkeypatch.setenv("JSEARCH_API_KEY", "k")
    monkeypatch.setenv("GMAIL_LABEL", "X")
    s = Settings(_env_file=None)
    assert s.jsearch_api_key == "k"
    assert s.gmail_label == "X"
    assert s.timezone == "America/Costa_Rica"


def test_no_key_by_default(monkeypatch):
    monkeypatch.delenv("JSEARCH_API_KEY", raising=False)
    assert Settings(_env_file=None).jsearch_api_key is None
