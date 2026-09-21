"""Columnas canónicas del dominio de sensores (esquema ETL)."""

from __future__ import annotations

COL_READING = "Leyendo"
DLS_SHEET_NAME = "Resumen"
DLS_HEADER_ROW = 24

EXPECTED_COLUMNS: list[str] = [
    "Descripción",
    "Sensor",
    "Número de Periodo",
    "Gas",
    "Leyendo",
    "Unidad",
    "STEL Máx",
    "TWA máximo",
    "Tiempo de Inicio",
    "Tiempo de finalización",
    "Sitio",
    "Factor de Respuesta",
    "Factor",
    "Alarma",
    "Temperatura",
]

COLUMN_RENAMES: dict[str, str] = {
    "Tiempo de inicio": "Tiempo de Inicio",
    "Tiempo de finalización": "Tiempo de finalización",
    "Tiempo de finalizaci\u00f3n": "Tiempo de finalización",
    "Factor de respuesta": "Factor de Respuesta",
    "STEL M\u00e1x": "STEL Máx",
    "TWA m\u00e1ximo": "TWA máximo",
}
