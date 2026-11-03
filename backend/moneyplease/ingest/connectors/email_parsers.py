"""Parsers del HTML de las alertas de empleo por correo (LinkedIn, Indeed)."""
import re
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup

from moneyplease.ingest.base import RawJob

LINKEDIN_ID = re.compile(r"/jobs/view/(\d+)")


def _next_strings(tag, n: int) -> list[str]:
    out = []
    for s in tag.find_all_next(string=True):
        if tag in s.parents:
            continue
        s = s.strip()
        if s:
            out.append(s)
            if len(out) == n:
                break
    return out


def _job(external_id: str, title: str, company: str, location: str | None, url: str) -> RawJob:
    return RawJob(external_id=external_id, title=title, company=company, location=location,
                  description="", url=url, published_at=None, raw={"external_id": external_id, "url": url})


def parse_linkedin(html: str) -> list[RawJob]:
    soup = BeautifulSoup(html or "", "html.parser")
    jobs, seen = [], set()
    for a in soup.find_all("a", href=True):
        m = LINKEDIN_ID.search(a["href"])
        # Las alertas actuales meten la tarjeta entera en el enlace: el título va en el elemento "font-bold"
        # (un <div> o un <a> anidado) y "Empresa · Lugar" en un <p> de la misma tarjeta.
        # Si no, el enlace es solo el título.
        heading = a.find(class_="font-bold")
        title = (heading or a).get_text(" ", strip=True)
        if not m or not title or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        company, location = "", None
        inside = [s.strip() for s in a.find_all(string=True) if s.strip()] if heading else []
        for s in inside or _next_strings(a, 4):
            if "·" in s:
                company, _, location = (p.strip() for p in s.partition("·"))
                break
        jobs.append(_job(m.group(1), title, company, location,
                         f"https://www.linkedin.com/jobs/view/{m.group(1)}/"))
    return jobs


def parse_indeed(html: str) -> list[RawJob]:
    soup = BeautifulSoup(html or "", "html.parser")
    jobs, seen = [], set()
    for a in soup.find_all("a", href=True):
        parts = urlsplit(a["href"])
        jk = parse_qs(parts.query).get("jk", [None])[0]
        title = a.get_text(" ", strip=True)
        if not jk or not title or jk in seen:
            continue
        seen.add(jk)
        following = _next_strings(a, 2)
        company = following[0] if following else ""
        location = following[1] if len(following) > 1 else None
        jobs.append(_job(jk, title, company, location, f"https://{parts.netloc}/viewjob?jk={jk}"))
    return jobs


def parse_alert(sender: str, html: str) -> list[RawJob]:
    sender = sender.lower()
    if "linkedin.com" in sender:
        return parse_linkedin(html)
    if "indeed.com" in sender:
        return parse_indeed(html)
    return []
