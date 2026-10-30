import hashlib
import math


class FakeLLMProvider:
    """Devuelve (o lanza) las respuestas en orden y registra cada llamada."""

    def __init__(self, responses, model="fake"):
        self.responses = list(responses)
        self.model = model
        self.calls: list[tuple[str, str, dict]] = []

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        self.calls.append((system, user, schema))
        out = self.responses.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


def _word_vector(word: str, dim: int) -> list[float]:
    digest = hashlib.sha256(word.encode()).digest()
    return [((digest[i % len(digest)] + i) % 251) / 125.0 - 1.0 for i in range(dim)]


class FakeEmbedder:
    """Vectores deterministas: suma de vectores por palabra, normalizada (textos con palabras comunes quedan cerca)."""

    def __init__(self, dim: int = 384):
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            acc = [0.0] * self.dim
            for word in text.lower().split():
                for i, v in enumerate(_word_vector(word, self.dim)):
                    acc[i] += v
            norm = math.sqrt(sum(v * v for v in acc)) or 1.0
            out.append([v / norm for v in acc])
        return out


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
