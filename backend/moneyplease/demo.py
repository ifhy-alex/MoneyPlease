"""DEMO_MODE: base aparte con datos ficticios y deterministas, para mostrar el dashboard sin datos reales."""
import math
import random
from datetime import datetime, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from moneyplease.db.models import Application, Job, JobLabel, Match, Profile, Source
from moneyplease.ingest.normalize import job_hash
from moneyplease.profile.schema import DEFAULT_PREFERENCES
from moneyplease.profile.schema import Profile as ProfileModel

TABLES = ("applications, job_labels, match_failures, matches, match_runs, profiles, ingest_runs, jobs, sources")
SOURCES = [("greenhouse:orion", "Orion Labs"), ("lever:cafebyte", "Café Byte"), ("workday:volcan", "Volcán Systems"),
           ("jsearch", "JSearch"), ("gmail", "Alertas de Gmail")]
COMPANIES = ["Orion Labs", "Café Byte", "Volcán Systems", "Quetzal Data", "Brisa Cloud", "Tucán Apps",
             "Pura Vida Tech", "Arenal Analytics"]
ROLES = ["Backend Developer", "Frontend Developer", "Data Analyst", "QA Engineer", "Software Developer Intern",
         "Data Engineer", "Full Stack Developer", "Cloud Support Intern", "Mobile Developer", "BI Analyst"]
LEVELS = ["Junior", "Intern", "", "Trainee", "Associate"]
PLACES = [("Heredia, Costa Rica", "Heredia", "CR", "hibrido"), ("San José, Costa Rica", "San José", "CR", "presencial"),
          ("Cartago, Costa Rica", "Cartago", "CR", "hibrido"), ("Costa Rica", None, "CR", "remoto"),
          ("LATAM (Remote)", None, None, "remoto")]
SKILLS = ["Java", "Spring Boot", "React", "TypeScript", "Python", "SQL", "Docker", "AWS", "Kubernetes", "Power BI",
          "Snowflake", "JUnit", "Tailwind CSS", "Azure"]
PROFILE_V1 = {
    "skills": [{"name": "Java", "level": "intermedio"}, {"name": "Spring Boot", "level": "basico"},
               {"name": "React", "level": "intermedio"}, {"name": "SQL", "level": "intermedio"},
               {"name": "Inglés", "level": "intermedio"}],
    "languages": [{"name": "Español", "level": "nativo"}, {"name": "Inglés", "level": "B2"}],
    "experience_months": 3,
    "seniority_target": ["practica", "junior"],
    "roles_target": ["Backend Developer", "Full Stack Developer"],
    "summary": "Estudiante de Ingeniería en Computación con proyectos académicos en Java y React.",
}
ESTADOS = ["guardada", "guardada", "aplicada", "aplicada", "entrevista", "oferta", "rechazada", "rechazada"]


def _vector(rng: random.Random) -> list[float]:
    v = [rng.uniform(-1, 1) for _ in range(384)]
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


def seed(session_factory: sessionmaker, now: datetime, rng_seed: int = 42) -> dict[str, int]:
    rng = random.Random(rng_seed)
    with session_factory() as s:
        s.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
        sources = []
        for key, name in SOURCES:
            src = Source(key=key, nombre=name, tipo="ats" if ":" in key else "api", config_json={}, activa=True)
            s.add(src)
            sources.append(src)
        s.flush()

        jobs = []
        for i in range(60):
            role, level = ROLES[i % len(ROLES)], LEVELS[rng.randrange(len(LEVELS))]
            company = COMPANIES[rng.randrange(len(COMPANIES))]
            ubicacion, provincia, pais, modalidad = PLACES[rng.randrange(len(PLACES))]
            title = f"{level} {role}".strip() + (f" {i // len(ROLES) + 1}" if i >= len(ROLES) else "")
            seen = now - timedelta(days=(i * 84) // 60, hours=rng.randrange(12))
            skills = rng.sample(SKILLS, 3)
            job = Job(source_id=sources[i % 3 if i % 7 else 3].id, external_id=f"demo-{i}", titulo=title,
                      empresa=company, ubicacion=ubicacion, modalidad=modalidad, provincia=provincia, pais=pais,
                      descripcion=f"Buscamos {role} con {', '.join(skills)}. Trabajo {modalidad} en {ubicacion}.",
                      url=f"https://example.com/demo/{i}", publicado_en=seen, estado="active",
                      hash=job_hash(company, title, ubicacion), raw_json={"demo": True},
                      embedding=_vector(rng), primera_vez_visto=seen, ultima_vez_visto=now)
            s.add(job)
            jobs.append((job, skills))
        s.flush()

        v1 = ProfileModel.model_validate({**PROFILE_V1, "preferences": DEFAULT_PREFERENCES.model_dump()})
        v2_data = {**PROFILE_V1, "skills": PROFILE_V1["skills"] + [{"name": "Docker", "level": "basico"},
                                                                    {"name": "Python", "level": "intermedio"}],
                   "experience_months": 5}
        v2 = ProfileModel.model_validate({**v2_data, "preferences": DEFAULT_PREFERENCES.model_dump()})
        profiles = []
        for version, model in ((1, v1), (2, v2)):
            row = Profile(version=version, cv_texto="", perfil_json=model.model_dump(), embedding=_vector(rng),
                          creado_en=now - timedelta(days=30 * (2 - version)))
            s.add(row)
            profiles.append(row)
        s.flush()
        active = profiles[-1]

        mine = {sk["name"] for sk in v2_data["skills"]}
        evaluated = []
        for job, skills in jobs[:48]:
            score = rng.randint(20, 95)
            fit = "no_aplica" if score < 35 else ("practica" if "Intern" in job.titulo or "Trainee" in job.titulo
                                                   else "junior")
            s.add(Match(profile_id=active.id, job_id=job.id, score=score, fit=fit,
                        fortalezas=[f"Experiencia con {sk}" for sk in skills if sk in mine][:3] or ["Inglés B2"],
                        brechas=[f"Pide {sk}" for sk in skills if sk not in mine][:3],
                        resumen=f"Encaje {'alto' if score >= 70 else 'parcial'} para {job.titulo}.",
                        modelo="demo", evaluado_en=job.primera_vez_visto + timedelta(hours=2)))
            evaluated.append(job)
        for i, job in enumerate(evaluated[:12]):
            s.add(JobLabel(job_id=job.id, etiqueta="buena" if i % 2 == 0 else "mala",
                           creado_en=now - timedelta(days=12 - i)))
        for i, estado in enumerate(ESTADOS):
            job = evaluated[12 + i]
            desde = now - timedelta(days=14 if estado == "aplicada" and i == 2 else 2 + i)
            s.add(Application(job_id=job.id, estado=estado, notas="", siguiente_paso="",
                              fecha_aplicacion=desde.date() if estado != "guardada" else None,
                              estado_desde=desde, creado_en=desde, actualizado_en=desde))
        s.commit()
        counts = {t: s.scalar(text(f"SELECT count(*) FROM {t}"))
                  for t in ("sources", "jobs", "profiles", "matches", "job_labels", "applications")}
    return counts


def check_demo_url(demo_url: str, real_url: str) -> None:
    """seed vacía la base entera: nunca debe apuntar a la base real."""
    demo, real = make_url(demo_url), make_url(real_url)
    same = (demo.host, demo.port, demo.database) == (real.host, real.port, real.database)
    if same or not (demo.database or "").endswith("_demo"):
        raise ValueError(f"DEMO_DATABASE_URL debe apuntar a una base distinta cuyo nombre termine en _demo "
                         f"(recibido: {demo.database!r})")


def ensure_database(url: str) -> None:
    """Crea la base demo si no existe y le aplica las migraciones."""
    from alembic import command
    from alembic.config import Config

    target = make_url(url)
    admin = create_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": target.database})
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{target.database}"'))
    admin.dispose()
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
