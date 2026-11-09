"""Catálogo de herramientas: nombre, permiso, esquema y función."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.modules.assistant.tools import (
    avisos,
    confiabilidad,
    datos,
    episodios,
    estado,
    gases,
    graficos,
    informes,
    limites,
    manual,
    modelos,
)
from app.modules.assistant.tools.params import (
    BuscarAvisos,
    BuscarManual,
    Confiabilidad,
    CrearGrafico,
    DetalleAviso,
    Episodios,
    EstadisticasGas,
    GenerarInforme,
    Limites,
    ResultadosModelos,
    SerieGas,
)
from app.modules.users.models import User
from app.shared.access import user_has_permission

ToolFn = Callable[[Session, User, BaseModel, dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    permission: str | None
    model: type[BaseModel]
    fn: ToolFn

    def declaration(self) -> dict[str, Any]:
        schema = self.model.model_json_schema()
        schema.pop("title", None)
        return {
            "name": self.name,
            "description": self.description,
            "parameters": schema,
        }


def _specs() -> list[ToolSpec]:
    return [
        ToolSpec(
            "resumen_estado",
            "Estado por equipo y gas al último dato: nivel, lectura y lo esperado.",
            "status.view",
            type("ResumenEstado", (BaseModel,), {}) if False else _empty(),
            estado.run,
        ),
        ToolSpec("buscar_avisos", "Lista de avisos del periodo, con nivel, equipo y resultado.", "alerts.view", BuscarAvisos, avisos.buscar),
        ToolSpec("detalle_aviso", "Detalle de un aviso: mensaje, lecturas, qué hacer y resultado.", "alerts.view", DetalleAviso, avisos.detalle),
        ToolSpec("serie_gas", "Estadísticas de un gas en un periodo. No devuelve miles de puntos.", "history.view", SerieGas, gases.serie),
        ToolSpec("estadisticas_gas", "Mínimo, máximo, promedio y superaciones agrupadas.", "history.view", EstadisticasGas, gases.estadisticas),
        ToolSpec("episodios", "Episodios reales: inicio, fin, pico y si hubo aviso previo.", "history.view", Episodios, episodios.run),
        ToolSpec("confiabilidad", "Las tres cifras de confiabilidad, con su fuente y tamaño.", "reliability.view", Confiabilidad, confiabilidad.run),
        ToolSpec("limites", "Límites del Decreto 1886, con la métrica y el artículo.", "status.view", Limites, limites.run),
        ToolSpec("cobertura_datos", "Rango real de fechas, equipos, gases y calidad.", "status.view", _empty(), datos.run),
        ToolSpec("resultados_modelos", "Tabla comparativa de la corrida y por qué ganó el método elegido.", "models.train", ResultadosModelos, modelos.run),
        ToolSpec("crear_grafico", "Arma un gráfico con una referencia de este mismo turno.", None, CrearGrafico, graficos.run),
        ToolSpec("generar_informe", "Genera un informe PDF o Excel del periodo pedido.", "reports.export", GenerarInforme, informes.run),
        ToolSpec("buscar_manual", "Busca en el manual de Vigía cómo usar la plataforma.", None, BuscarManual, manual.run),
    ]


def _empty() -> type[BaseModel]:
    class Empty(BaseModel):
        pass

    return Empty


TOOLS: dict[str, ToolSpec] = {spec.name: spec for spec in _specs()}


def specs_for(user: User) -> list[ToolSpec]:
    allowed: list[ToolSpec] = []
    for spec in TOOLS.values():
        if spec.permission is None or user_has_permission(user, spec.permission):
            allowed.append(spec)
    return allowed


def declarations_for(user: User) -> list[dict[str, Any]]:
    return [spec.declaration() for spec in specs_for(user)]
