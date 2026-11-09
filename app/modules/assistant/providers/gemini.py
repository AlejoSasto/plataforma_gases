"""Function calling de Gemini.

Verificado el 2026-11-08 contra la referencia generateContent:
https://aistudio.google.com/api-reference/generate-content/generate-content
- Recurso: POST /v1beta/models/{model}:generateContent
- Herramientas: tools[].functionDeclarations
- La respuesta trae parts[].functionCall {name, args}
- El servidor devuelve parts[].functionResponse {name, response}
El ejemplo vigente de modelo en esa referencia es gemini-2.5-flash.
La cadena se puede cambiar con ASSISTANT_GEMINI_MODELS; no se asume un único nombre.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings
from app.modules.assistant.providers.base import ProviderError, ProviderResult

log = logging.getLogger("vigia.assistant.gemini")

DEFAULT_MODELS = ("gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash")
_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def model_chain() -> list[str]:
    raw = (settings.assistant_gemini_models or "").strip()
    if not raw:
        return list(DEFAULT_MODELS)
    return [part.strip() for part in raw.split(",") if part.strip()]


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str | None = None, models: list[str] | None = None) -> None:
        self.api_key = api_key if api_key is not None else (settings.gemini_api_key or "")
        self.models = models or model_chain()
        self.model = self.models[0] if self.models else ""

    def generate(
        self,
        *,
        system: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        pending: list[dict[str, Any]],
        correction: str | None,
    ) -> ProviderResult:
        if not self.api_key:
            raise ProviderError("falta la clave")
        contents = _contents(messages, pending, correction)
        body: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {"temperature": 0.1},
        }
        if tools:
            body["tools"] = [
                {
                    "functionDeclarations": [
                        {
                            "name": tool["name"],
                            "description": tool["description"],
                            "parameters": tool["parameters"],
                        }
                        for tool in tools
                    ]
                }
            ]
        last_error: Exception | None = None
        for model in self.models:
            try:
                payload = self._post(model, body)
            except ProviderError as exc:
                last_error = exc
                log.warning("gemini %s no respondió: %s", model, exc)
                continue
            self.model = model
            return _parse(payload, model)
        raise ProviderError(str(last_error) if last_error else "sin modelos")

    def _post(self, model: str, body: dict[str, Any]) -> dict[str, Any]:
        timeout = float(settings.assistant_call_timeout_s or 30)
        try:
            response = httpx.post(
                _URL.format(model=model),
                params={"key": self.api_key},
                json=body,
                timeout=timeout,
            )
        except httpx.HTTPError as exc:
            raise ProviderError("sin conexión con el proveedor") from exc
        if response.status_code >= 500 or response.status_code == 429:
            raise ProviderError(f"proveedor {response.status_code}")
        if response.status_code >= 400:
            raise ProviderError(f"solicitud rechazada {response.status_code}")
        try:
            return response.json()
        except ValueError as exc:
            raise ProviderError("respuesta inválida") from exc


def _contents(
    messages: list[dict[str, str]],
    pending: list[dict[str, Any]],
    correction: str | None,
) -> list[dict[str, Any]]:
    contents: list[dict[str, Any]] = []
    for message in messages:
        role = "user" if message.get("role") == "user" else "model"
        contents.append({"role": role, "parts": [{"text": message.get("content") or ""}]})
    if pending:
        calls = []
        responses = []
        for item in pending:
            calls.append({"functionCall": {"name": item["name"], "args": item.get("args") or {}}})
            responses.append(
                {
                    "functionResponse": {
                        "name": item["name"],
                        "response": item.get("response") or {"error": "sin datos"},
                    }
                }
            )
        contents.append({"role": "model", "parts": calls})
        contents.append({"role": "user", "parts": responses})
    if correction:
        contents.append({"role": "user", "parts": [{"text": correction}]})
    return contents


def _parse(payload: dict[str, Any], model: str) -> ProviderResult:
    candidates = payload.get("candidates") or []
    if not candidates:
        raise ProviderError("respuesta vacía")
    parts = ((candidates[0].get("content") or {}).get("parts")) or []
    calls = []
    texts: list[str] = []
    for part in parts:
        if part.get("functionCall"):
            call = part["functionCall"]
            calls.append({"name": call.get("name"), "args": call.get("args") or {}})
        elif part.get("text"):
            texts.append(part["text"])
    usage = payload.get("usageMetadata") or {}
    tokens = usage.get("totalTokenCount")
    if calls:
        return ProviderResult(calls=calls, model=model, tokens=tokens)
    if not texts:
        raise ProviderError("respuesta sin texto")
    return ProviderResult(text="\n".join(texts), model=model, tokens=tokens)
