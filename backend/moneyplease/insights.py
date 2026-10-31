"""Agregaciones para el dashboard: brechas de la semana, skills, series diarias y por fuente."""
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from moneyplease.db.models import Job, Match, Source
from moneyplease.ingest.normalize import canonical
from moneyplease.profile.schema import Profile
from moneyplease.skill_areas import area_of, find_skill

CR = ZoneInfo("America/Costa_Rica")


def _skill_key(phrase: str) -> str:
    return find_skill(phrase) or canonical(phrase)


def gaps_week(session: Session, profile_id: int, now: datetime, top: int = 8) -> list[tuple[str, int]]:
    rows = session.scalars(select(Match.brechas).where(Match.profile_id == profile_id,
                                                       Match.evaluado_en >= now - timedelta(days=7))).all()
    counts: Counter[str] = Counter()
    originals: dict[str, Counter[str]] = defaultdict(Counter)
    for brechas in rows:
        for phrase in brechas or []:
            key = _skill_key(phrase)
            if key:
                counts[key] += 1
                originals[key][phrase.strip()] += 1
    # Las skills conocidas se muestran por su nombre; las frases libres, con su texto original más frecuente.
    return [(key if find_skill(key) == key else originals[key].most_common(1)[0][0], n)
            for key, n in counts.most_common(top)]


def skills(session: Session, profile: Profile, profile_id: int, limit: int = 60) -> list[dict]:
    mine = {_skill_key(s.name) for s in profile.skills}
    freq: Counter[str] = Counter()
    gaps: set[str] = set()
    for fortalezas, brechas in session.execute(select(Match.fortalezas, Match.brechas)
                                               .where(Match.profile_id == profile_id)).all():
        for phrase in fortalezas or []:
            if found := find_skill(phrase):
                freq[found] += 1
        for phrase in brechas or []:
            if found := find_skill(phrase):
                freq[found] += 1
                gaps.add(found)
    for skill in mine:
        freq.setdefault(skill, 1)
    return [{"skill": s, "area": area_of(s), "frecuencia": n, "tengo": s in mine, "brecha": s in gaps}
            for s, n in freq.most_common(limit)]


def _cr_day(ts: datetime) -> date:
    return ts.astimezone(CR).date()


def daily(session: Session, profile_id: int | None, now: datetime, dias: int = 30) -> list[dict]:
    today = _cr_day(now)
    first = today - timedelta(days=dias - 1)
    start = datetime.combine(first, datetime.min.time(), CR)
    rows = session.execute(select(Job.id, Job.primera_vez_visto).where(Job.primera_vez_visto >= start)).all()
    scores = {}
    if profile_id is not None and rows:
        scores = dict(session.execute(select(Match.job_id, Match.score)
                                      .where(Match.profile_id == profile_id,
                                             Match.job_id.in_([r.id for r in rows]))).all())
    nuevas: Counter[date] = Counter()
    by_day: dict[date, list[int]] = defaultdict(list)
    for job_id, seen in rows:
        day = _cr_day(seen)
        nuevas[day] += 1
        if job_id in scores:
            by_day[day].append(scores[job_id])
    out = []
    for i in range(dias):
        day = first + timedelta(days=i)
        s = by_day.get(day)
        out.append({"fecha": day.isoformat(), "nuevas": nuevas[day],
                    "score_promedio": round(sum(s) / len(s), 1) if s else None})
    return out


def flow(session: Session, now: datetime, semanas: int = 12) -> list[dict]:
    today = _cr_day(now)
    this_monday = today - timedelta(days=today.weekday())
    weeks = [this_monday - timedelta(weeks=i) for i in reversed(range(semanas))]
    start = datetime.combine(weeks[0], datetime.min.time(), CR)
    fuentes = sorted({key.partition(":")[0] for key in session.scalars(select(Source.key))})
    counts: Counter[tuple[date, str]] = Counter()
    for seen, key in session.execute(select(Job.primera_vez_visto, Source.key)
                                     .join(Source, Source.id == Job.source_id)
                                     .where(Job.primera_vez_visto >= start)).all():
        day = _cr_day(seen)
        counts[(day - timedelta(days=day.weekday()), key.partition(":")[0])] += 1
    return [{"semana": w.isoformat(), "fuente": f, "nuevas": counts[(w, f)]} for w in weeks for f in fuentes]
