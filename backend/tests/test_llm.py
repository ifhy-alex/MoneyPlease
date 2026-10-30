import json

import httpx
import pytest
import respx

from moneyplease.matching.llm import GeminiProvider, LLMError, QuotaExceeded, parse_json_text
from tests.fakes import FakeEmbedder, cosine

URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent"
SCHEMA = {"type": "OBJECT", "properties": {"score": {"type": "INTEGER"}}}


def reply(text):
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def provider():
    return GeminiProvider("KEY", "gemini-3.5-flash-lite")


@respx.mock
def test_request_shape():
    route = respx.post(URL).respond(200, json=reply('{"score": 80}'))
    provider().generate_json("sys", "usr", SCHEMA)
    req = route.calls[0].request
    body = json.loads(req.content)
    assert req.headers["x-goog-api-key"] == "KEY"
    assert body["generationConfig"]["temperature"] == 0
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert body["generationConfig"]["responseSchema"] == SCHEMA
    assert body["systemInstruction"]["parts"][0]["text"] == "sys"
    assert body["contents"][0]["parts"][0]["text"] == "usr"


@respx.mock
def test_parses_json_response():
    respx.post(URL).respond(200, json=reply('{"score": 80}'))
    assert provider().generate_json("s", "u", SCHEMA) == {"score": 80}


def test_parses_fenced_json():
    assert parse_json_text('```json\n{"score": 80}\n```') == {"score": 80}
    assert parse_json_text('Aquí va: {"score": 80} listo') == {"score": 80}


def test_unparseable_raises_llm_error():
    with pytest.raises(LLMError):
        parse_json_text("no hay json aquí")


@respx.mock
def test_empty_candidates_raise_llm_error():
    respx.post(URL).respond(200, json={"candidates": []})
    with pytest.raises(LLMError):
        provider().generate_json("s", "u", SCHEMA)


@respx.mock
def test_429_quota_exceeded():
    respx.post(URL).respond(429)
    with pytest.raises(QuotaExceeded):
        provider().generate_json("s", "u", SCHEMA)


@respx.mock
def test_500_raises_http_error():
    respx.post(URL).respond(500)
    with pytest.raises(httpx.HTTPStatusError):
        provider().generate_json("s", "u", SCHEMA)


def test_fake_embedder_similarity():
    e = FakeEmbedder()
    a, b, c = e.embed(["java spring boot", "spring boot backend", "ventas retail"])
    assert cosine(a, b) > cosine(a, c)
    assert len(a) == 384
