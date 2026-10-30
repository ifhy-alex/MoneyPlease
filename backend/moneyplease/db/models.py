from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(Text, unique=True)
    nombre: Mapped[str] = mapped_column(Text)
    tipo: Mapped[str] = mapped_column(Text)
    config_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    desactivada_motivo: Mapped[str | None] = mapped_column(Text)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    external_id: Mapped[str | None] = mapped_column(Text)
    titulo: Mapped[str] = mapped_column(Text)
    empresa: Mapped[str] = mapped_column(Text)
    ubicacion: Mapped[str] = mapped_column(Text, default="")
    modalidad: Mapped[str] = mapped_column(Text, default="desconocida")
    provincia: Mapped[str | None] = mapped_column(Text)
    pais: Mapped[str | None] = mapped_column(Text)
    descripcion: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text)
    publicado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estado: Mapped[str] = mapped_column(Text, default="active")
    hash: Mapped[str] = mapped_column(Text, unique=True)
    raw_json: Mapped[dict] = mapped_column(JSONB)
    embedding = mapped_column(Vector(384), nullable=True)
    primera_vez_visto: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ultima_vez_visto: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    corridas_ausente: Mapped[int] = mapped_column(Integer, default=0)


class IngestRun(Base):
    __tablename__ = "ingest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    iniciado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    terminado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ok: Mapped[bool] = mapped_column(Boolean, default=False)
    ofertas_traidas: Mapped[int] = mapped_column(Integer, default=0)
    ofertas_nuevas: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, unique=True)
    cv_texto: Mapped[str] = mapped_column(Text, default="")
    perfil_json: Mapped[dict] = mapped_column(JSONB)
    embedding = mapped_column(Vector(384))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Match(Base):
    __tablename__ = "matches"

    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), primary_key=True)
    score: Mapped[int] = mapped_column(Integer)
    fit: Mapped[str] = mapped_column(Text)
    fortalezas: Mapped[list] = mapped_column(JSONB)
    brechas: Mapped[list] = mapped_column(JSONB)
    resumen: Mapped[str] = mapped_column(Text)
    modelo: Mapped[str] = mapped_column(Text)
    evaluado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MatchRun(Base):
    __tablename__ = "match_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"))
    iniciado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    terminado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    embebidas: Mapped[int] = mapped_column(Integer, default=0)
    candidatas: Mapped[int] = mapped_column(Integer, default=0)
    evaluadas: Mapped[int] = mapped_column(Integer, default=0)
    fallidas: Mapped[int] = mapped_column(Integer, default=0)
    cuota_agotada: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text)


class JobLabel(Base):
    __tablename__ = "job_labels"

    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), primary_key=True)
    etiqueta: Mapped[str] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
