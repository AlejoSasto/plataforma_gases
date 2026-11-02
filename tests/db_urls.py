"""Resuelve URL de desarrollo vs pruebas sin importar la app."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DEV = "postgresql+psycopg://postgres:postgres@localhost:5433/proyecto_gases"


def _parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def _canon(url: str) -> str:
    return url.split("?")[0].rstrip("/").lower()


def load_urls() -> tuple[str, str]:
    file_env = _parse_env(ROOT / ".env")
    env_db = os.environ.get("DATABASE_URL", "")
    env_test = os.environ.get("TEST_DATABASE_URL", "")
    file_db = file_env.get("DATABASE_URL", "")
    file_test = file_env.get("TEST_DATABASE_URL", "")

    if env_db and "proyecto_gases_test" not in env_db:
        dev = env_db
    else:
        dev = file_db or _DEFAULT_DEV

    test = env_test or file_test
    if not test:
        test = dev.rsplit("/", 1)[0] + "/proyecto_gases_test"
    return dev, test


def assert_isolated(dev: str, test: str) -> None:
    if _canon(dev) == _canon(test):
        raise RuntimeError(
            "TEST_DATABASE_URL no puede coincidir con DATABASE_URL. Las pruebas deben usar proyecto_gases_test."
        )
    if "proyecto_gases_test" not in test:
        raise RuntimeError(f"TEST_DATABASE_URL debe apuntar a proyecto_gases_test, no a {test}")
