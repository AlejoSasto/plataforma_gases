"""Verificador único (Plan 20 F2).

python scripts/verify.py --plan 19
python scripts/verify.py --fast
python scripts/verify.py --full
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PY = sys.executable
TYPED = [
    "ml_core/validation/scaling.py",
    "ml_core/validation/walk_forward.py",
    "app/shared/access.py",
]
RUFF_PATHS = [
    "scripts/verify.py",
    "tests/conftest.py",
    "tests/factories.py",
    "tests/db_urls.py",
    "tests/ui",
    "tests/e2e",
    "tests/perf",
    "tests/unit/test_isolation_plan20.py",
    "tests/guards/test_features_are_causal.py",
    "tests/guards/test_scalers_fit_on_train_only.py",
    "tests/guards/test_final_test_untouched.py",
    "tests/guards/test_no_legacy_imports.py",
    "app/shared/access.py",
    "ml_core/validation/scaling.py",
]


def _run(cmd: list[str], *, env: dict[str, str] | None = None) -> int:
    print("→", " ".join(cmd))
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.call(cmd, cwd=str(ROOT), env=merged)


def _pytest(args: list[str]) -> int:
    return _run([PY, "-m", "pytest", "-q", "--tb=short", *args])


def stage_format() -> int:
    code = _run([PY, "-m", "ruff", "format", "--check", *RUFF_PATHS])
    if code != 0:
        return code
    return _run([PY, "-m", "ruff", "check", *RUFF_PATHS])


def stage_types() -> int:
    return _run([PY, "-m", "mypy", "--ignore-missing-imports", "--follow-imports=skip", *TYPED])


def stage_migrations() -> int:
    from tests.db_urls import assert_isolated, load_urls

    dev, test = load_urls()
    assert_isolated(dev, test)
    env = {"DATABASE_URL": test}
    _run([PY, "scripts/ensure_test_db.py"], env=env)
    for cmd in (["downgrade", "base"], ["upgrade", "head"], ["upgrade", "head"]):
        code = _run([PY, "-m", "alembic", *cmd], env=env)
        if code != 0:
            return code
    return _run([PY, "-m", "alembic", "check"], env=env)


def stage_unit() -> int:
    return _pytest(["tests/unit"])


def stage_integration() -> int:
    return _pytest(["tests/integration"])


def stage_coverage() -> int:
    return _pytest(
        [
            "tests/unit",
            "tests/guards",
            "tests/ui",
            "--cov=ml_core/forecasting",
            "--cov=ml_core/validation",
            "--cov=app/shared",
            "--cov-config=.coveragerc",
            "--cov-report=term-missing",
        ]
    )


def stage_guards() -> int:
    return _pytest(["tests/guards"])


def stage_language() -> int:
    return _pytest(["tests/ui", "tests/unit/test_ux_language.py"])


def stage_e2e() -> int:
    return _pytest(["tests/e2e", "-m", "e2e or plan20"])


def stage_a11y() -> int:
    return _pytest(["tests/e2e/test_a11y.py"])


def stage_visual() -> int:
    return _pytest(["tests/e2e/test_visual.py"])


def stage_perf() -> int:
    return _pytest(["tests/perf"])


def stage_slow() -> int:
    return _pytest(["-m", "slow"])


def stage_dev_audit() -> int:
    """Solo lectura sobre la base de desarrollo indicada en .env."""
    from sqlalchemy import create_engine, text

    from scripts.archive_legacy_models import is_legacy_production

    env_file = ROOT / ".env"
    url = ""
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("DATABASE_URL="):
                url = line.split("=", 1)[1].strip().strip("'\"")
    if not url:
        print("DETENIDO dev-audit: falta DATABASE_URL en .env")
        return 1
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            legacy = conn.execute(
                text("SELECT algorithm, status FROM model_registry WHERE status = 'production'")
            ).all()
            bad = [row[0] for row in legacy if is_legacy_production(row[0], row[1])]
            missing_article = conn.execute(
                text(
                    "SELECT count(*) FROM normative_thresholds "
                    "WHERE kind = 'normativo' AND (article IS NULL OR article = '')"
                )
            ).scalar()
            demo = conn.execute(
                text("SELECT count(*) FROM users WHERE email LIKE '%@example.com'")
            ).scalar()
    except Exception as exc:  # noqa: BLE001
        print(f"DETENIDO dev-audit: {exc}")
        return 1
    finally:
        engine.dispose()
    if bad or missing_article or demo:
        print(f"FAIL dev-audit legacy={bad} sin_articulo={missing_article} demo_users={demo}")
        return 1
    print("OK dev-audit")
    return 0


STAGES = [
    ("1. formato", stage_format),
    ("2. tipos", stage_types),
    ("3. migraciones", stage_migrations),
    ("4. unitarias", stage_unit),
    ("5. integración", stage_integration),
    ("6. cobertura", stage_coverage),
    ("7. guardias", stage_guards),
    ("8. lenguaje", stage_language),
    ("9. e2e", stage_e2e),
    ("10. accesibilidad", stage_a11y),
    ("11. visual", stage_visual),
    ("12. rendimiento", stage_perf),
    ("13. lento", stage_slow),
]


def _plan_pytest_args(plan: int) -> list[str]:
    if plan == 16:
        return ["-m", "plan16"]
    if plan == 17:
        return ["-m", "plan17"]
    if plan == 18:
        return ["-m", "plan18"]
    if plan == 19:
        return ["-m", "plan19"]
    if plan == 20:
        return ["-m", "plan20 or plan"]
    if plan == 23:
        return ["-m", "plan23"]
    if plan == 24:
        return ["-m", "plan24"]
    if plan == 25:
        return ["-m", "plan25"]
    if plan == 26:
        return ["-m", "plan26 and not live_llm and not e2e"]
    if plan == 15:
        return [
            "-m",
            "plan and not plan16 and not plan17 and not plan18 and not plan19 "
            "and not plan20 and not plan23 and not plan24 and not plan25 and not plan26",
        ]
    return ["-m", f"plan{plan} or plan"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=int, default=None)
    parser.add_argument("--fast", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--dev-audit", action="store_true")
    args = parser.parse_args()

    if args.dev_audit:
        return stage_dev_audit()

    if args.plan:
        code = _pytest(_plan_pytest_args(args.plan))
        if code != 0:
            print("FAIL pytest")
            return code
        print("OK verify")
        return 0

    selected = STAGES
    if args.fast:
        selected = [s for s in STAGES if s[0].startswith(("1.", "4.", "7."))]
    elif not args.full:
        selected = [s for s in STAGES if s[0].startswith(("1.", "4.", "7."))]

    failed: list[str] = []
    for name, fn in selected:
        print(f"\n== {name} ==")
        try:
            code = fn()
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {name}: {exc}")
            failed.append(name)
            continue
        if code != 0:
            print(f"FAIL {name}")
            failed.append(name)
    if failed:
        print("FAIL verify:", ", ".join(failed))
        return 1
    print("OK verify")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
