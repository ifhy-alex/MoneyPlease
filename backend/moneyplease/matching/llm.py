import json
import re
import time
from collections.abc import Callable
from typing import Protocol

import httpx

BASE = "https://generativelanguage.googleapis.com/v1beta/models"
FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")
MAX_RETRY_DELAY = 60.0


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


def _retry_delay(resp: httpx.Response) -> float | None:
    """Segundos que Gemini pide esperar en un 429 por límite por minuto; None si no lo dice (cuota diaria)."""
    try:
        details = resp.json().get("error", {}).get("details", [])
    except ValueError:
        details = []
    for d in details:
        match = re.fullmatch(r"([\d.]+)s", str(d.get("retryDelay", "")))
        if match:
            return float(match.group(1))
    header = resp.headers.get("Retry-After")
    return float(header) if header and header.isdigit() else None


class GeminiProvider:
    def __init__(self, api_key: str, model: str, client: httpx.Client | None = None, *, rpm: int = 10,
                 retries: int = 2, sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic):
        self.api_key = api_key
        self.model = model
        self.client = client or httpx.Client(timeout=60)
        self.interval = 60.0 / rpm  # el nivel gratuito limita requests por minuto
        self.retries = retries
        self.sleep = sleep
        self.clock = clock
        self._last: float | None = None

    def _post(self, body: dict) -> httpx.Response:
        if self._last is not None:
            wait = self.interval - (self.clock() - self._last)
            if wait > 0:
                self.sleep(wait)
        self._last = self.clock()
        return self.client.post(f"{BASE}/{self.model}:generateContent", json=body,
                                headers={"x-goog-api-key": self.api_key})

    def _send(self, body: dict) -> httpx.Response:
        rate_limited_once = False
        attempt = 0
        while True:
            try:
                resp = self._post(body)
            except (httpx.TimeoutException, httpx.TransportError):
                if attempt >= self.retries:
                    raise
                attempt += 1
                self.sleep(2.0 * attempt)
                continue
            if resp.status_code == 429:
                delay = _retry_delay(resp)
                if delay is None or delay > MAX_RETRY_DELAY or rate_limited_once:
                    raise QuotaExceeded(resp.text[:200])
                rate_limited_once = True
                self.sleep(delay)
                continue
            if resp.status_code >= 500 and attempt < self.retries:
                attempt += 1
                self.sleep(2.0 * attempt)
                continue
            resp.raise_for_status()
            return resp

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                 "responseSchema": schema},
        }
        resp = self._send(body)
        try:
            candidates = resp.json().get("candidates") or []
        except ValueError as exc:
            raise LLMError(f"respuesta no es JSON: {resp.text[:200]}") from exc
        if not candidates:
            raise LLMError(f"respuesta sin candidatos: {resp.text[:200]}")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        return parse_json_text("".join(p.get("text", "") for p in parts))
