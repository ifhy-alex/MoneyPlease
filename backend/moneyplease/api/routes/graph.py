from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from moneyplease.api.deps import get_session
from moneyplease.api.schemas import GraphEdge, GraphOffer, GraphSkill, SkillsGraph
from moneyplease.eval import top_matches
from moneyplease.profile import store
from moneyplease.profile.schema import Profile
from moneyplease.skill_areas import fold_skill, area_of, skills_in

router = APIRouter()
TOP_OFFERS = 40
MAX_MISSING = 8


def _display(skill: str) -> str:
    return skill.upper() if len(skill) <= 3 or skill.startswith(".") else skill.title()


@router.get("/skills-graph", response_model=SkillsGraph)
def skills_graph(session: Session = Depends(get_session)) -> SkillsGraph:
    active = store.active(session)
    if active is None:
        raise HTTPException(404, "Todavía no hay perfil guardado")
    rows = top_matches(session, active.id, TOP_OFFERS, hide_rejected=True)
    if not rows:
        return SkillsGraph(habilidades=[], ofertas=[], aristas=[])
    perfil = Profile.model_validate(active.perfil_json)
    mine = {fold_skill(s.name): s for s in perfil.skills}
    found = {job.id: skills_in(f"{job.titulo} {job.descripcion or ''}") for _, job in rows}
    degree = Counter(skill for skills in found.values() for skill in skills)
    missing = sorted((s for s in degree if s not in mine), key=lambda s: (-degree[s], s))[:MAX_MISSING]
    names = {key: skill.name for key, skill in mine.items()} | {s: _display(s) for s in missing}
    habilidades = [GraphSkill(nombre=skill.name, nivel=skill.level, area=area_of(skill.name),
                              grado=degree[key], tiene=True) for key, skill in mine.items()]
    habilidades += [GraphSkill(nombre=names[s], nivel=None, area=area_of(s), grado=degree[s], tiene=False)
                    for s in missing]
    aristas = [GraphEdge(habilidad=names[s], job_id=job_id)
               for job_id, skills in found.items() for s in sorted(skills) if s in names]
    ofertas = [GraphOffer(job_id=job.id, titulo=job.titulo, empresa=job.empresa, puntaje=match.score)
               for match, job in rows]
    return SkillsGraph(habilidades=habilidades, ofertas=ofertas, aristas=aristas)
