from typing import Protocol

from moneyplease.db.models import Job

MODEL_NAME = "intfloat/multilingual-e5-small"


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class E5Embedder:
    """multilingual-e5-small en CPU: 384 dimensiones, vectores normalizados."""

    def __init__(self, model_name: str = MODEL_NAME):
        self.model_name = model_name
        self._model = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name, device="cpu")
        vectors = self._model.encode(texts, batch_size=64, normalize_embeddings=True)
        return [v.tolist() for v in vectors]


def job_text(job: Job) -> str:
    parts = [job.titulo, job.empresa, job.ubicacion, job.descripcion]
    return "passage: " + " | ".join(p or "" for p in parts)
