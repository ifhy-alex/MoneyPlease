from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Protocol


@dataclass
class RawJob:
    external_id: str | None
    title: str
    company: str
    location: str | None
    description: str
    url: str
    published_at: datetime | None
    raw: dict
    remote_hint: bool | None = None
    workplace_hint: str | None = None


@dataclass
class ConnectorResult:
    jobs: list[RawJob]
    config_updates: dict = field(default_factory=dict)


class Connector(Protocol):
    key: str
    is_complete_listing: bool

    def fetch(self) -> ConnectorResult: ...


class SourceGone(Exception):
    """La fuente ya no existe (404) o robots.txt prohíbe leerla."""


class QuotaExhausted(Exception):
    def __init__(self, until: date):
        super().__init__(f"cuota agotada hasta {until.isoformat()}")
        self.until = until


class Maintenance(Exception):
    """La fuente está en mantenimiento: es temporal, se reintenta en la próxima corrida."""
