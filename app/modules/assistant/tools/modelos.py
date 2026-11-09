"""Resultados técnicos de las corridas. Solo analista y administración."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.assistant.tools.params import ResultadosModelos
from app.modules.ml_training import service as ml
from app.modules.users.models import User


def run(db: Session, user: User, params: ResultadosModelos, ctx: dict[str, Any]) -> dict[str, Any]:
    del user, ctx
    summary = ml.benchmark_for_assistant(
        db,
        run_id=params.run,
        gas=params.gas,
        horizonte=params.horizonte,
    )
    if summary.get("error"):
        return summary
    summary["data_until"] = summary.get("creada")
    summary["historic"] = True
    summary["clamped"] = False
    return summary
