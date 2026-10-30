import time
from collections.abc import Callable
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from moneyplease.ingest.base import SourceGone

USER_AGENT = "MoneyPlease/0.1 (+https://github.com/ifhy-alex/MoneyPlease)"


class PoliteClient:
    """Cliente httpx con límite por dominio, robots.txt y reintentos."""

    def __init__(self, *, min_interval: float = 1.0, retries: int = 3, backoff: float = 1.0,
                 sleep: Callable[[float], None] = time.sleep, transport: httpx.BaseTransport | None = None):
        self.min_interval = min_interval
        self.retries = retries
        self.backoff = backoff
        self.sleep = sleep
        self._client = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20, transport=transport,
                                    follow_redirects=True)
        self._last: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser | None] = {}

    def _throttle(self, domain: str) -> None:
        last = self._last.get(domain)
        if last is not None:
            wait = self.min_interval - (time.monotonic() - last)
            if wait > 0:
                self.sleep(wait)
        self._last[domain] = time.monotonic()

    def _allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            parser = None
            try:
                resp = self._client.get(f"{origin}/robots.txt")
                if resp.status_code == 200:
                    parser = RobotFileParser()
                    parser.parse(resp.text.splitlines())
            except httpx.HTTPError:
                pass
            self._robots[origin] = parser
        parser = self._robots[origin]
        return parser is None or parser.can_fetch(USER_AGENT, url)

    def get(self, url: str, *, params: dict | None = None, headers: dict | None = None,
            check_robots: bool = True) -> httpx.Response:
        if check_robots and not self._allowed(url):
            raise SourceGone(f"robots.txt prohíbe {url}")
        domain = urlsplit(url).netloc
        for attempt in range(self.retries + 1):
            self._throttle(domain)
            try:
                resp = self._client.get(url, params=params, headers=headers)
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt == self.retries:
                    raise
            else:
                if resp.status_code == 404:
                    raise SourceGone(f"404 {url}")
                if resp.status_code < 500 or attempt == self.retries:
                    resp.raise_for_status()
                    return resp
            self.sleep(self.backoff * 2**attempt)
        raise AssertionError("unreachable")
