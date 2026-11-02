"""Publicaciones casi idénticas: la misma empresa publica el mismo puesto dos veces con otra requisición."""
from datetime import datetime

import numpy as np
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from moneyplease.db.models import Job
from moneyplease.ingest.normalize import canonical

MIN_SIMILARITY = 0.99


def duplicate_groups(items: list[tuple[int, str, list[float]]], score: dict[int, int],
                     seen: dict[int, datetime]) -> dict[int, list[int]]:
    """Grupos de 2+ ofertas de la misma empresa con similitud ≥ 0.99: representante → los demás.

    El representante es el de mayor puntaje; si empatan, el visto primero; si siguen, el id menor.
    """
    n = len(items)
    if n < 2:
        return {}
    ids = [i for i, _, _ in items]
    companies = [canonical(c) for _, c, _ in items]
    vecs = np.asarray([v for _, _, v in items], dtype=float)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    sims = vecs @ vecs.T
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a in range(n):
        for b in range(a + 1, n):
            if companies[a] == companies[b] and sims[a, b] >= MIN_SIMILARITY:
                parent[find(a)] = find(b)
    members: dict[int, list[int]] = {}
    for k in range(n):
        members.setdefault(find(k), []).append(ids[k])
    out = {}
    for group in members.values():
        if len(group) < 2:
            continue
        rep = min(group, key=lambda i: (-score.get(i, -1), seen.get(i, datetime.max), i))
        out[rep] = sorted(i for i in group if i != rep)
    return out


def _direct(session: Session, job: Job) -> list[Job]:
    """Ofertas activas de la misma empresa con similitud ≥ 0.99 con esta (solo vecinas directas)."""
    if job.embedding is None:
        return []
    # Igual que en el mapa: sin el índice HNSW, que con filtros devuelve muy pocas filas.
    # Ojo: SET LOCAL dura hasta el final de la transacción, no solo esta consulta. Lo que venga después en la
    # misma petición tampoco usará índices de escaneo; hoy son consultas pequeñas, pero conviene saberlo.
    session.execute(text("SET LOCAL enable_indexscan = off"))
    rows = session.scalars(
        select(Job).where(Job.id != job.id, Job.estado == "active", Job.embedding.is_not(None),
                          Job.embedding.cosine_distance(job.embedding) <= 1 - MIN_SIMILARITY)
        .order_by(Job.id)).all()
    return [r for r in rows if canonical(r.empresa) == canonical(job.empresa)]


def duplicates_of(session: Session, job: Job) -> list[Job]:
    """Todo el grupo de publicaciones casi idénticas de esta oferta (sin ella), siguiendo cadenas A~B~C.

    Es la misma regla que `duplicate_groups` en el universo: así el top, el feedback y el universo coinciden.
    """
    seen = {job.id}
    group: list[Job] = []
    pending = [job]
    while pending:
        for other in _direct(session, pending.pop()):
            if other.id not in seen:
                seen.add(other.id)
                group.append(other)
                pending.append(other)
    return sorted(group, key=lambda j: j.id)
