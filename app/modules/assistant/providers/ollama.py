"""Proveedor local opcional (Ollama) para un equipo sin internet."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings
from app.modules.assistant.providers.base import ProviderError, ProviderResult

log = logging.getLogger("vigia.assistant.ollama")


class OllamaProvider:
    name = "ollama"

    def __init__(self) -> None:
        self.model = settings.assistant_ollama_model or "qwen2.5:7b-instruct"
        self.base = (settings.assistant_ollama_url or "http://127.0.0.1:11434").rstrip("/")

    def generate(
        self,
        *,
        system: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        pending: list[dict[str, Any]],
        correction: str | None,
    ) -> ProviderResult:
        chat = [{"role": "system", "content": system}]
        for message in messages:
            chat.append({"role": message.get("role") or "user", "content": message.get("content") or ""})
        for item in pending:
            chat.append(
                {
                    "role": "tool",
                    "content": _compact(item.get("response")),
                }
            )
        if correction:
            chat.append({"role": "user", "content": correction})
        body = {
            "model": self.model,
            "messages": chat,
            "stream": False,
            "tools": [
                {"type": "function", "function": {"name": tool["name"], "description": tool["description"], "parameters": tool["parameters"]}}
                for tool in tools
            ],
        }
        timeout = float(settings.assistant_call_timeout_s or 30)
        try:
            response = httpx.post(f"{self.base}/api/chat", json=body, timeout=timeout)
        except httpx.HTTPError as exc:
            raise ProviderError("sin conexión con el proveedor local") from exc
        if response.status_code >= 400:
            raise ProviderError("el proveedor local rechazó la solicitud")
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError("respuesta local inválida") from exc
        message = payload.get("message") or {}
        calls = []
        for call in message.get("tool_calls") or []:
            fn = call.get("function") or {}
            calls.append({"name": fn.get("name"), "args": fn.get("arguments") or {}})
        if calls:
            return ProviderResult(calls=calls, model=self.model)
        text = message.get("content")
        if not text:
            raise ProviderError("respuesta local vacía")
        return ProviderResult(text=text, model=self.model)


def _compact(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, default=str)[:8000]
