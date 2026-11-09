"""Contratos del asistente. El modelo no define estos esquemas: los valida el servidor."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class InMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class AskBody(BaseModel):
    messages: list[InMessage] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def last_is_user(self) -> "AskBody":
        if self.messages[-1].role != "user":
            raise ValueError("El último mensaje debe ser del usuario")
        return self


class FeedbackBody(BaseModel):
    util: bool
    comentario: str | None = Field(default=None, max_length=500)

    @field_validator("comentario")
    @classmethod
    def strip_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None


class Source(BaseModel):
    tool: str
    params: dict[str, Any]
    rows: int
