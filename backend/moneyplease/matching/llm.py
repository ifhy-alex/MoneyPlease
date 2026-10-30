import json
import re
from typing import Protocol

import httpx

BASE = "https://generativelanguage.googleapis.com/v1beta/models"
FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")


class QuotaExceeded(Exception):
    """El proveedor respondió 429: se acabó la cuota por ahora."""


class LLMError(Exception):
    """La respuesta del LLM no se pudo interpretar como JSON."""


class LLMProvider(Protocol):
    model: str

    def generate_json(self, system: str, user: str, schema: dict) -> dict: ...


def parse_json_text(text: str) -> dict:
    candidates = [text, FENCE.sub("", text.strip())]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start:end + 1])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(value, dict):
            return value
    raise LLMError(f"respuesta sin JSON válido: {text[:200]!r}")


class GeminiProvider:
    def __init__(self, api_key: str, model: str, client: httpx.Client | None = None):
        self.api_key = api_key
        self.model = model
        self.client = client or httpx.Client(timeout=60)

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                 "responseSchema": schema},
        }
        resp = self.client.post(f"{BASE}/{self.model}:generateContent", json=body,
                                headers={"x-goog-api-key": self.api_key})
        if resp.status_code == 429:
            raise QuotaExceeded(resp.text[:200])
        resp.raise_for_status()
        candidates = resp.json().get("candidates") or []
        if not candidates:
            raise LLMError(f"respuesta sin candidatos: {resp.text[:200]}")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        return parse_json_text("".join(p.get("text", "") for p in parts))
