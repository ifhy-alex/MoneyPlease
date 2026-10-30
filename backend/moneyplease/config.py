from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://moneyplease:moneyplease@localhost:5432/moneyplease"
    jsearch_api_key: str | None = None
    gmail_credentials_path: Path = Path("secrets/gmail_credentials.json")
    gmail_token_path: Path = Path("secrets/gmail_token.json")
    gmail_label: str = "Empleo/Alertas"
    companies_path: Path = Path("companies.yaml")
    timezone: str = "America/Costa_Rica"


@lru_cache
def get_settings() -> Settings:
    return Settings()
