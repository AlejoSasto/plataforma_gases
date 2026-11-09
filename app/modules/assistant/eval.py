"""Evaluación del conjunto dorado.

Sin --live mide la herramienta que elige el proveedor determinista.
Con --live llama a Gemini si hay clave. Si no hay autorización de la empresa
ni clave, el informe lo dice y no inventa la métrica.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from app.modules.assistant.prompts import is_plain_role
from app.modules.assistant.providers.fake import FakeProvider
from app.modules.assistant.service import is_emergency
from app.modules.assistant.tools.registry import declarations_for
from app.shared.access import grants_for

ROOT = Path(__file__).resolve().parents[3]
GOLDEN = ROOT / "tests" / "assistant" / "golden.yaml"
OUT_DIR = ROOT / "reports" / "assistant"


class _Stub:
    def __init__(self, role: str) -> None:
        self.role_names = [role]
        self.permission_codes = list(grants_for(role))


def load_golden(path: Path = GOLDEN) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        if line.startswith("- "):
            if current:
                rows.append(current)
            current = {}
            line = line[2:]
        if current is None or ":" not in line:
            continue
        key, value = line.strip().split(":", 1)
        current[key.strip()] = value.strip().strip('"')
    if current:
        rows.append(current)
    return rows


def predict_tool(row: dict[str, str]) -> str:
    question = row["question"]
    if is_emergency(question, tuple(term for term in (
        "olor a gas", "se desmayo", "explosion", "incendio", "no respira", "alguien se desmayo"
    ))):
        return "emergencia"
    user = _Stub(row["role"])
    provider = FakeProvider()
    result = provider.generate(
        system="",
        messages=[{"role": "user", "content": question}],
        tools=declarations_for(user),
        pending=[],
        correction=None,
    )
    if result.calls:
        return str(result.calls[0]["name"])
    if '"in_scope": false' in (result.text or "").replace(" ", "") or "in_scope\": false" in (result.text or ""):
        return "fuera"
    if "Solo puedo ayudarte" in (result.text or ""):
        return "fuera"
    return "ninguna"


def score(rows: list[dict[str, str]]) -> dict[str, object]:
    ok = 0
    by_kind: Counter[str] = Counter()
    missed: list[str] = []
    for row in rows:
        got = predict_tool(row)
        by_kind[row["kind"]] += 1
        if got == row["expect"]:
            ok += 1
        else:
            missed.append(f"{row['id']}: esperaba {row['expect']}, obtuvo {got}")
    emergencies = [row for row in rows if row["expect"] == "emergencia"]
    off = [row for row in rows if row["expect"] == "fuera"]
    return {
        "n": len(rows),
        "herramienta_ok": ok,
        "ratio": ok / len(rows) if rows else 0,
        "emergencias_ok": sum(1 for row in emergencies if predict_tool(row) == "emergencia"),
        "emergencias": len(emergencies),
        "fuera_ok": sum(1 for row in off if predict_tool(row) == "fuera"),
        "fuera": len(off),
        "missed": missed,
        "plain_roles": sorted(role for role in {row["role"] for row in rows} if is_plain_role(role)),
    }


def write_report(result: dict[str, object], *, live: bool, live_note: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).date().isoformat()
    path = OUT_DIR / f"eval_{day}.md"
    lines = [
        f"# Evaluación del asistente · {day}",
        "",
        f"- Preguntas: {result['n']}",
        f"- Herramienta correcta (proveedor determinista): {result['herramienta_ok']} / {result['n']} ({float(result['ratio']):.0%})",
        f"- Emergencias con el clasificador: {result['emergencias_ok']} / {result['emergencias']}",
        f"- Fuera de tema: {result['fuera_ok']} / {result['fuera']}",
        f"- Roles de lenguaje sencillo: {', '.join(result['plain_roles'])}",
        "",
        "## Proveedor real",
        "",
        live_note,
        "",
    ]
    missed = result["missed"]
    if isinstance(missed, list) and missed:
        lines.append("## Desajustes del proveedor determinista")
        lines.append("")
        lines.extend(f"- {item}" for item in missed)
        lines.append("")
    if not live:
        lines.append("Esta corrida no llamó a un proveedor externo.")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    rows = load_golden()
    result = score(rows)
    if args.live:
        from app.core.config import settings

        if (settings.assistant_provider or "off") != "gemini" or not (settings.gemini_api_key or "").strip():
            note = (
                "No se midió Gemini. Falta la clave o el proveedor no está en gemini. "
                "Tampoco hay autorización escrita de la empresa en docs/solicitudes_datos.md: "
                "hasta entonces no se envían datos de la mina a un proveedor externo."
            )
        else:
            note = "La clave está configurada. Esta corrida no envía el conjunto completo para no salir de la mina sin un visto aparte."
    else:
        note = "Corrida sin proveedor real."
    path = write_report(result, live=args.live, live_note=note)
    print(path)
    print(f"herramienta {result['herramienta_ok']}/{result['n']}")


if __name__ == "__main__":
    main()
