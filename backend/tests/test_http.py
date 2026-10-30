import httpx
import pytest
import respx

from moneyplease.ingest.base import SourceGone
from moneyplease.ingest.http import PoliteClient


@pytest.fixture
def waits():
    return []


@pytest.fixture
def client(waits):
    return PoliteClient(sleep=waits.append)


def no_robots(mock, host="https://a.com"):
    mock.get(f"{host}/robots.txt").respond(404)


@respx.mock
def test_sets_user_agent(client):
    no_robots(respx)
    route = respx.get("https://a.com/x").respond(200)
    client.get("https://a.com/x")
    assert route.calls[0].request.headers["User-Agent"].startswith("MoneyPlease/0.1")


@respx.mock
def test_rate_limit_same_domain(client, waits):
    no_robots(respx)
    no_robots(respx, "https://b.com")
    respx.get("https://a.com/x").respond(200)
    respx.get("https://b.com/x").respond(200)
    client.get("https://a.com/x")
    client.get("https://b.com/x")
    assert waits == []
    client.get("https://a.com/x")
    assert len(waits) == 1 and waits[0] > 0


@respx.mock
def test_retries_5xx_then_ok(waits):
    client = PoliteClient(sleep=waits.append, min_interval=0)
    respx.get("https://a.com/x").mock(side_effect=[httpx.Response(503), httpx.Response(503), httpx.Response(200)])
    assert client.get("https://a.com/x", check_robots=False).status_code == 200
    assert waits == [1, 2]


@respx.mock
def test_gives_up_after_retries(waits):
    client = PoliteClient(sleep=waits.append, min_interval=0)
    route = respx.get("https://a.com/x").respond(500)
    with pytest.raises(httpx.HTTPStatusError):
        client.get("https://a.com/x", check_robots=False)
    assert route.call_count == 4


@respx.mock
def test_404_raises_source_gone(client):
    respx.get("https://a.com/x").respond(404)
    with pytest.raises(SourceGone):
        client.get("https://a.com/x", check_robots=False)


@respx.mock
def test_429_not_retried(client):
    route = respx.get("https://a.com/x").respond(429)
    with pytest.raises(httpx.HTTPStatusError):
        client.get("https://a.com/x", check_robots=False)
    assert route.call_count == 1


@respx.mock
def test_robots_disallow(client):
    respx.get("https://a.com/robots.txt").respond(200, text="User-agent: *\nDisallow: /jobs\n")
    respx.get("https://a.com/ok").respond(200)
    with pytest.raises(SourceGone):
        client.get("https://a.com/jobs/1")
    assert client.get("https://a.com/ok").status_code == 200


@respx.mock
def test_robots_404_allows(client):
    no_robots(respx)
    respx.get("https://a.com/jobs/1").respond(200)
    assert client.get("https://a.com/jobs/1").status_code == 200
