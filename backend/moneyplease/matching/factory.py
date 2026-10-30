from functools import lru_cache

from moneyplease.config import Settings
from moneyplease.matching.embed import E5Embedder
from moneyplease.matching.llm import GeminiProvider


@lru_cache
def build_embedder() -> E5Embedder:
    # Una sola instancia por proceso: el modelo se carga una vez y se reutiliza entre corridas.
    return E5Embedder()


def build_llm(settings: Settings) -> GeminiProvider:
    if not settings.gemini_api_key:
        raise RuntimeError("Falta GEMINI_API_KEY en .env")
    return GeminiProvider(settings.gemini_api_key, settings.gemini_model)
