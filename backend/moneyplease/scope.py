"""Ámbito de una oferta: en Costa Rica o internacional (remota desde el extranjero).

`pais` dice dónde queda el puesto, pero no alcanza solo: las pasantías de Himalayas dicen "abierto a Costa Rica"
(pais = CR) aunque la empresa sea de afuera, y JSearch y las alertas de correo a veces no traen lugar aunque sus
búsquedas sean siempre en Costa Rica.
"""
from typing import Literal

from sqlalchemy import ColumnElement, and_, or_

from moneyplease.db.models import Job, Source

Ambito = Literal["cr", "internacional"]
INTERNATIONAL_SOURCES = ("himalayas",)  # portales 100% remotos
CR_SEARCH_SOURCES = ("jsearch", "gmail")  # búsquedas acotadas a Costa Rica


def scope_of(fuente: str, pais: str | None) -> Ambito:
    if fuente in INTERNATIONAL_SOURCES:
        return "internacional"
    if pais == "CR" or fuente in CR_SEARCH_SOURCES:
        return "cr"
    return "internacional"


def international() -> ColumnElement[bool]:
    """La misma regla que scope_of, en SQL (la consulta debe unir Source)."""
    return or_(Source.key.in_(INTERNATIONAL_SOURCES),
               and_(Job.pais.is_distinct_from("CR"), Source.key.not_in(CR_SEARCH_SOURCES)))


def where_scope(ambito: Ambito | None) -> ColumnElement[bool] | None:
    if ambito == "internacional":
        return international()
    if ambito == "cr":
        return ~international()
    return None
