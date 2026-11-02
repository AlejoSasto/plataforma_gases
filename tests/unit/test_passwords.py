"""Política de contraseñas Plan 19."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.passwords import COMMON_FILE, common_passwords, validate_password


@pytest.mark.plan19
def test_common_passwords_file_has_10k() -> None:
    assert COMMON_FILE.exists()
    n = sum(1 for line in COMMON_FILE.read_text(encoding="utf-8").splitlines() if line.strip())
    assert n >= 10_000
    assert len(common_passwords()) >= 10_000


@pytest.mark.plan19
def test_rejects_short_common_and_name() -> None:
    assert validate_password("corta") is not None
    assert validate_password("password1234") is not None
    assert validate_password("AnaMaria2026!", email="ana@example.com", full_name="Ana Maria") is not None
    assert validate_password("unaClaveLargaSegura!") is None
