"""Proveedor determinista para la suite. No sale a internet."""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from app.modules.assistant.providers.base import ProviderResult
from app.shared.copy import ASK_OFF_TOPIC, ASK_PROTOCOL, ASK_SAFETY


def _fold(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text.casefold())
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


def _gas(text: str) -> str | None:
    folded = _fold(text)
    if "sulfhidrico" in folded or "h2s" in folded:
        return "H2S"
    if "metano" in folded or "ch4" in folded:
        return "CH4"
    if "dioxido de carbono" in folded or "co2" in folded:
        return "CO2"
    if "monoxido" in folded or re.search(r"\bco\b", folded):
        return "CO"
    if "oxigeno" in folded or "o2" in folded:
        return "O2"
    return None


def _period(text: str) -> tuple[str | None, str | None]:
    match = re.search(r"(20\d{2})-(\d{2})-(\d{2})", text)
    if match:
        return match.group(0), match.group(0)
    months = {
        "enero": 1,
        "febrero": 2,
        "marzo": 3,
        "abril": 4,
        "mayo": 5,
        "junio": 6,
        "julio": 7,
        "agosto": 8,
        "septiembre": 9,
        "octubre": 10,
        "noviembre": 11,
        "diciembre": 12,
    }
    folded = _fold(text)
    for name, number in months.items():
        found = re.search(rf"{name} de (20\d{{2}})", folded)
        if found:
            year = found.group(1)
            last = 30 if number in {4, 6, 9, 11} else (29 if number == 2 else 31)
            return f"{year}-{number:02d}-01", f"{year}-{number:02d}-{last:02d}"
    return None, None


def _intent(text: str) -> str:
    folded = _fold(text)
    if any(word in folded for word in ("contrasena", "password", "clima", "futbol", "receta", "servidor")):
        return "off"
    if "seguro entrar" in folded or "es seguro" in folded:
        return "safety"
    if "grafico" in folded:
        return "chart"
    if "informe" in folded or "pdf" in folded:
        return "report"
    if any(word in folded for word in ("como cierro", "como uso", "manual", "ayuda", "contrasena olvid")):
        return "manual"
    if "limite" in folded or "decreto" in folded:
        return "limits"
    if "confiab" in folded or "confiable" in folded:
        return "reliability"
    if "episodio" in folded:
        return "episodes"
    if "modelo" in folded or "gano" in folded:
        return "models"
    if "estadistic" in folded or "promedio" in folded:
        return "stats"
    if "cobertura" in folded or "calidad de los datos" in folded:
        return "coverage"
    if "estado" in folded:
        return "status"
    if "aviso" in folded or "alerta" in folded:
        return "alerts"
    if _gas(text) or "lectura" in folded or "comportamiento" in folded:
        return "series"
    return "off"


class FakeProvider:
    name = "fake"
    model = "fake-1"

    def __init__(self, script: list[dict[str, Any]] | None = None) -> None:
        self.script = list(script or [])
        self.calls = 0

    def generate(
        self,
        *,
        system: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        pending: list[dict[str, Any]],
        correction: str | None,
    ) -> ProviderResult:
        del system
        self.calls += 1
        if self.script:
            step = self.script.pop(0)
            if step.get("call"):
                return ProviderResult(calls=[step["call"]], model=self.model, tokens=1)
            return ProviderResult(text=step.get("text"), model=self.model, tokens=1)
        question = ""
        for message in messages:
            if message.get("role") == "user":
                question = message.get("content") or question
        intent = _intent(question)
        names = {tool["name"] for tool in tools}
        if pending and not correction and intent == "chart":
            if not any(item["name"] == "crear_grafico" for item in pending):
                ref = pending[-1]["response"].get("evidence_id") or pending[-1]["response"].get("series_ref")
                tipo = "avisos_por_periodo" if pending[-1]["name"] == "buscar_avisos" else "serie"
                if pending[-1]["name"] == "estadisticas_gas":
                    tipo = "estadistica"
                if pending[-1]["name"] == "confiabilidad":
                    tipo = "confiabilidad"
                if ref and "crear_grafico" in names:
                    return ProviderResult(
                        calls=[{"name": "crear_grafico", "args": {"tipo": tipo, "ref": ref, "titulo": "Consulta"}}],
                        model=self.model,
                        tokens=1,
                    )
        if correction or pending:
            return ProviderResult(text=self._final(question, intent, pending), model=self.model, tokens=1)
        call = self._first_call(question, intent, names)
        if call is None:
            return ProviderResult(text=self._final(question, intent, pending), model=self.model, tokens=1)
        return ProviderResult(calls=[call], model=self.model, tokens=1)

    def _first_call(self, question: str, intent: str, names: set[str]) -> dict[str, Any] | None:
        gas = _gas(question)
        desde, hasta = _period(question)
        if intent == "chart":
            if "aviso" in _fold(question) and "buscar_avisos" in names:
                return {"name": "buscar_avisos", "args": _clean(gas, desde, hasta)}
            if "serie_gas" in names:
                return {"name": "serie_gas", "args": _clean(gas or "CH4", desde, hasta)}
        if intent == "report" and "generar_informe" in names:
            kind = "resumen_gerencia" if "gerencia" in _fold(question) or "confiab" in _fold(question) else "avisos_periodo"
            if "confiab" in _fold(question) and "gerencia" not in _fold(question):
                kind = "confiabilidad"
            if gas and "aviso" not in _fold(question):
                kind = "comportamiento_gas"
            args = _clean(gas, desde, hasta)
            args["tipo"] = kind
            args["formato"] = "pdf"
            if not args.get("desde") or not args.get("hasta"):
                args["desde"] = args.get("desde") or "2024-11-01"
                args["hasta"] = args.get("hasta") or "2024-11-30"
            return {"name": "generar_informe", "args": args}
        mapping = {
            "alerts": "buscar_avisos",
            "series": "serie_gas",
            "stats": "estadisticas_gas",
            "episodes": "episodios",
            "reliability": "confiabilidad",
            "limits": "limites",
            "coverage": "cobertura_datos",
            "status": "resumen_estado",
            "models": "resultados_modelos",
            "manual": "buscar_manual",
            "safety": "resumen_estado",
        }
        name = mapping.get(intent)
        if name is None or name not in names:
            return None
        if name == "buscar_manual":
            return {"name": name, "args": {"pregunta": question[:300]}}
        if name == "resultados_modelos":
            return {"name": name, "args": {"gas": gas or "CH4", "horizonte": 12}}
        if name == "limites":
            return {"name": name, "args": {"gas": gas} if gas else {}}
        if name in {"resumen_estado", "cobertura_datos", "confiabilidad"}:
            return {"name": name, "args": {}}
        args = _clean(gas, desde, hasta)
        if name == "serie_gas":
            args["gas"] = gas or "CH4"
        if name == "estadisticas_gas":
            args["gas"] = gas or "CH4"
        if name == "episodios":
            args["gas"] = gas or "CH4"
        return {"name": name, "args": args}

    def _final(self, question: str, intent: str, pending: list[dict[str, Any]]) -> str:
        if intent == "off" and not pending:
            return json.dumps({"reply": ASK_OFF_TOPIC, "in_scope": False, "include": []}, ensure_ascii=False)
        include: list[str] = []
        parts: list[str] = []
        if intent == "safety":
            parts.append(ASK_SAFETY)
        for item in pending:
            response = item["response"]
            if response.get("evidence_id"):
                include.append(response["evidence_id"])
            if response.get("chart_id"):
                include.append(response["chart_id"])
            if response.get("report_id"):
                include.append(str(response["report_id"]))
            if response.get("error"):
                parts.append(str(response["error"]))
                continue
            parts.append(_phrase(item["name"], response))
        if "que hacer" in _fold(question) or "qué hacer" in question.casefold():
            parts.append(ASK_PROTOCOL)
        if not parts:
            parts.append("No encontré datos para esa consulta.")
        reply = " ".join(part for part in parts if part).strip()
        return json.dumps({"reply": reply, "in_scope": True, "include": include}, ensure_ascii=False)


def _clean(gas: str | None, desde: str | None, hasta: str | None) -> dict[str, Any]:
    args: dict[str, Any] = {}
    if gas:
        args["gas"] = gas
    if desde:
        args["desde"] = desde
    if hasta:
        args["hasta"] = hasta
    return args


def _phrase(name: str, response: dict[str, Any]) -> str:
    if name == "buscar_avisos":
        return (
            f"Encontré {response.get('n', 0)} avisos entre {response.get('desde')} y {response.get('hasta')}. "
            f"{response.get('anticipados', 0)} fueron anticipados."
        )
    if name == "detalle_aviso":
        return (
            f"El aviso {response.get('aviso')} de {response.get('gas')} en {response.get('equipo')} "
            f"está {response.get('estado')}. {response.get('que_hacer') or ''}"
        ).strip()
    if name == "serie_gas":
        if response.get("n") == 0:
            return response.get("nota") or "No hay lecturas en ese periodo."
        return (
            f"En {response.get('gas_label')} hay {response.get('n')} lecturas. "
            f"El mínimo es {response.get('min')}, el máximo {response.get('max')} y el promedio {response.get('avg')}."
        )
    if name == "estadisticas_gas":
        return f"Hay {response.get('n_grupos', 0)} grupos de {response.get('gas_label')}."
    if name == "episodios":
        return f"Encontré {response.get('n', 0)} episodios de {response.get('gas_label')}."
    if name == "confiabilidad":
        return " ".join(
            str(response.get(key) or "")
            for key in ("anticipacion", "minutos", "innecesarios")
        ).strip()
    if name == "limites":
        return f"Hay {response.get('n', 0)} límites cargados."
    if name == "cobertura_datos":
        return f"Los datos van de {response.get('desde')} a {response.get('hasta')}."
    if name == "resumen_estado":
        return f"Revisé {response.get('n', 0)} equipos."
    if name == "resultados_modelos":
        return response.get("por_que") or "No hay una explicación de la corrida."
    if name == "crear_grafico":
        return f"Preparé el gráfico {response.get('titulo')}."
    if name == "generar_informe":
        return "El informe está listo para descargar."
    if name == "buscar_manual":
        fragments = response.get("fragmentos") or []
        if not fragments:
            return "El manual no tiene una sección para eso."
        return fragments[0].get("texto") or fragments[0].get("titulo") or ""
    return ""
