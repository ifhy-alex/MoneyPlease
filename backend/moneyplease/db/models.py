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
