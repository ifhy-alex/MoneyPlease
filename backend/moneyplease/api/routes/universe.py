import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from moneyplease.api.deps import get_session
from moneyplease.api.routes.map import embeddings, visible_jobs
from moneyplease.api.schemas import Nube, UniverseData, UniversePoint
from moneyplease.clusters import cluster_count, cluster_names, clusters
from moneyplease.duplicates import duplicate_groups
from moneyplease.profile import store
from moneyplease.projection import project3d

router = APIRouter()


@router.get("/universe", response_model=UniverseData)
def get_universe(session: Session = Depends(get_session)) -> UniverseData:
    active = store.active(session)
    if active is None:
        raise HTTPException(404, "Todavía no hay perfil guardado")
    rows = visible_jobs(session, active)
    # Las publicaciones casi idénticas se dibujan como una sola estrella (con anillo).
    groups = duplicate_groups([(job.id, job.empresa, job.embedding) for job, *_ in rows],
                              {job.id: score for job, score, *_ in rows if score is not None},
                              {job.id: job.primera_vez_visto for job, *_ in rows})
    hidden = {i for others in groups.values() for i in others}
    rows = [r for r in rows if r[0].id not in hidden]
    if not rows:
        return UniverseData(total=0, puntos=[], nubes=[])
    profile_vec, jobs = embeddings(active, rows)
    coords = project3d(profile_vec, jobs, [r[0].id for r in rows])
    xyz = np.array([c[:3] for c in coords])
    labels = clusters(xyz, cluster_count(len(rows)))
    k = max(labels) + 1
    names = cluster_names([[f"{job.titulo} {job.descripcion or ''}" for (job, *_), lab in zip(rows, labels) if lab == j]
                           for j in range(k)])
    puntos = [UniversePoint(job_id=job.id, titulo=job.titulo, empresa=job.empresa, x=x, y=y, z=z, similitud=s,
                            puntaje=score, fit=fit, etiqueta=etiqueta, nube=lab, duplicados=groups.get(job.id, []))
              for (job, score, etiqueta, fit), (x, y, z, s), lab in zip(rows, coords, labels)]
    nubes = []
    for j in range(k):
        members = xyz[np.array(labels) == j]
        if len(members):
            cx, cy, cz = members.mean(axis=0)
            nubes.append(Nube(id=j, nombre=names[j], x=float(cx), y=float(cy), z=float(cz), n=len(members)))
    return UniverseData(total=len(puntos), puntos=puntos, nubes=nubes)
