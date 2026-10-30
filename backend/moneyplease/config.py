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
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    private_dir: Path = Path("private")
    match_top_k: int = 40
    match_max_evals: int = 50


@lru_cache
def get_settings() -> Settings:
    return Settings()
