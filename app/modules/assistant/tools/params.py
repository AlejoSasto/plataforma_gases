"""Parámetros tipados de las herramientas. El modelo no puede enviar SQL ni nombres de tabla."""

from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator

BOGOTA = ZoneInfo("America/Bogota")

Nivel = Literal["vigilar", "actuar", "evacuar", "normal"]
Origen = Literal["en_vivo", "historico"]
EstadoAviso = Literal["abierta", "reconocida", "resuelta"]
Agregacion = Literal["6min", "hora", "dia"]
Metrica = Literal["valor", "twa_8h", "stel_15min"]
Agrupar = Literal["dia", "semana", "mes", "equipo", "turno"]
TipoGrafico = Literal["serie", "estadistica", "avisos_por_periodo", "confiabilidad"]
TipoInforme = Literal["avisos_periodo", "resumen_gerencia", "confiabilidad", "comportamiento_gas"]
FormatoInforme = Literal["pdf", "xlsx"]


def _parse_day(value: str, *, end: bool) -> datetime:
    text = value.strip()
    try:
        day = datetime.strptime(text[:10], "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("La fecha debe ir como AAAA-MM-DD") from exc
    clock = time(23, 59, 59) if end else time(0, 0, 0)
    return datetime.combine(day.date(), clock, tzinfo=BOGOTA).astimezone(timezone.utc)


class Periodo(BaseModel):
    desde: str | None = None
    hasta: str | None = None

    def inicio(self) -> datetime | None:
        if not self.desde:
            return None
        return _parse_day(self.desde, end=False)

    def fin(self) -> datetime | None:
        if not self.hasta:
            return None
        return _parse_day(self.hasta, end=True)


class BuscarAvisos(Periodo):
    gas: str | None = None
    nivel: str | None = None
    equipo: str | None = None
    origen: Origen | None = None
    estado: EstadoAviso | None = None
    limite: int = Field(default=20, ge=1, le=50)


class DetalleAviso(BaseModel):
    id: int = Field(ge=1)


class SerieGas(Periodo):
    gas: str
    equipo: str | None = None
    agregacion: Agregacion = "hora"
    metrica: Metrica = "valor"


class EstadisticasGas(Periodo):
    gas: str
    agrupar_por: Agrupar = "dia"


class Episodios(Periodo):
    gas: str
    nivel: str | None = None


class Confiabilidad(Periodo):
    gas: str | None = None


class Limites(BaseModel):
    gas: str | None = None


class ResultadosModelos(BaseModel):
    run: int | None = None
    gas: str
    horizonte: int | None = None


class CrearGrafico(BaseModel):
    tipo: TipoGrafico
    ref: str = Field(min_length=2, max_length=64)
    titulo: str = Field(min_length=1, max_length=120)


class GenerarInforme(Periodo):
    tipo: TipoInforme
    gas: str | None = None
    equipo: str | None = None
    formato: FormatoInforme = "pdf"

    @field_validator("desde", "hasta")
    @classmethod
    def required_period(cls, value: str | None) -> str | None:
        return value


class BuscarManual(BaseModel):
    pregunta: str = Field(min_length=2, max_length=300)
