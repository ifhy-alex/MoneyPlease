from datetime import UTC, datetime

import httpx

from moneyplease.ingest.base import ConnectorResult, Maintenance, RawJob, SourceGone
from moneyplease.ingest.http import PoliteClient

PAGE = 20
COUNTRY = "costa rica"
REMOTE_TYPES = {"remote": "remote", "hybrid": "hybrid", "on-site": "onsite", "onsite": "onsite",
                "on site": "onsite"}


def _country_facet(facets: list[dict]) -> tuple[str, list[str]] | None:
    """Busca el valor "Costa Rica" en los facets de ubicación; el nombre del facet cambia por empresa."""
    for facet in facets:
        groups = [v for v in facet.get("values", []) if "values" in v] or [facet]
        for group in groups:
            ids = [v["id"] for v in group.get("values", [])
                   if "id" in v and COUNTRY in str(v.get("descriptor", "")).lower()]
            if ids:
                return group["facetParameter"], ids
    return None


def _published(start: str | None) -> datetime | None:
    if not start:
        return None
    try:
        return datetime.fromisoformat(start[:10]).replace(tzinfo=UTC)
    except ValueError:
        return None


def _is_maintenance(resp: httpx.Response) -> bool:
    """Solo la página de mantenimiento de Workday: una oferta puede tener "maintenance" en su URL."""
    urls = [str(resp.url), resp.headers.get("location", "")]
    urls += [str(r.url) for r in resp.history] + [r.headers.get("location", "") for r in resp.history]
    return any("community.workday.com" in u or "/maintenance-page" in u for u in urls)


def _json(request) -> dict:
    """JSON de la respuesta; si Workday redirige a su página de mantenimiento, lo dice claramente."""
    try:
        resp = request()
    except httpx.HTTPStatusError as exc:
        if _is_maintenance(exc.response):
            raise Maintenance("Workday en mantenimiento") from exc
        raise
    if _is_maintenance(resp):
        raise Maintenance("Workday en mantenimiento")
    return resp.json()


class WorkdayConnector:
    """Sitio público de empleo de Workday, filtrado a las ofertas en Costa Rica."""

    is_complete_listing = True

    def __init__(self, tenant: str, wd: str, site: str, company: str, client: PoliteClient):
        self.tenant, self.site, self.company, self.client = tenant, site, company, client
        self.host = f"https://{tenant}.{wd}.myworkdayjobs.com"
        self.api = f"{self.host}/wday/cxs/{tenant}/{site}"
        self.key = f"workday:{tenant}"

    def _jobs(self, facets: dict, offset: int, limit: int) -> dict:
        body = {"appliedFacets": facets, "limit": limit, "offset": offset, "searchText": ""}
        return _json(lambda: self.client.post(f"{self.api}/jobs", json=body, headers={"Accept": "application/json"},
                                              check_robots=False))

    def fetch(self) -> ConnectorResult:
        # El API no lo publican como tal: si robots.txt prohíbe el sitio de empleo, no se lee.
        for url in (f"{self.host}/{self.site}/", f"{self.api}/jobs"):
            if not self.client.allowed(url):
                raise SourceGone(f"robots.txt prohíbe {url}")
        found = _country_facet(self._jobs({}, 0, 1).get("facets", []))
        if found is None:
            return ConnectorResult([])
        facet, ids = found
        postings, offset, total = [], 0, None
        while total is None or offset < total:
            page = self._jobs({facet: ids}, offset, PAGE)
            total = page.get("total", 0) if total is None else total
            batch = page.get("jobPostings", [])
            if not batch:
                break
            postings += batch
            offset += PAGE
        return ConnectorResult([self._job(p) for p in postings])

    def _job(self, posting: dict) -> RawJob:
        detail = _json(lambda: self.client.get(f"{self.api}{posting['externalPath']}",
                                               headers={"Accept": "application/json"}, check_robots=False))
        info = detail.get("jobPostingInfo", {})
        location = info.get("location") or posting.get("locationsText") or ""
        remote = REMOTE_TYPES.get(str(info.get("remoteType") or "").strip().lower())
        return RawJob(
            external_id=info.get("jobReqId") or posting["externalPath"],
            title=info.get("title") or posting.get("title", ""),
            company=self.company,
            # La ubicación de Workday viene como "CRI - Heredia" o "Lagunilla de Heredia": el país se agrega
            # para que el normalizador reconozca la oferta como de Costa Rica.
            location=f"{location}, Costa Rica" if COUNTRY not in location.lower() else location,
            description=info.get("jobDescription") or "",
            url=info.get("externalUrl") or f"{self.host}/{self.site}{posting['externalPath']}",
            published_at=_published(info.get("startDate")),
            raw={"posting": posting, "detail": info},
            workplace_hint=remote,
        )
