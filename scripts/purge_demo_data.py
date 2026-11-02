"""Borra datos demo de la base de desarrollo (Plan 24 F1).

  python scripts/purge_demo_data.py            # ensayo
  python scripts/purge_demo_data.py --confirm  # borra + auditoría data.purge_demo
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from app.core.database import SessionLocal
from app.modules.users import models as _users_models  # noqa: F401 — registra FK users
from scripts.audit_demo_data import audit

KEEP_EMAIL = (os.environ.get("SUPERADMIN_EMAIL") or "").strip().lower()


def _exec_ok(db, sql: str, params: dict) -> None:
    """Ejecuta con SAVEPOINT para no abortar toda la transacción si falla un FK."""
    db.execute(text("SAVEPOINT purge_step"))
    try:
        db.execute(text(sql), params)
        db.execute(text("RELEASE SAVEPOINT purge_step"))
    except Exception:  # noqa: BLE001
        db.execute(text("ROLLBACK TO SAVEPOINT purge_step"))


def _delete_users(db, emails: list[str]) -> int:
    deleted = 0
    for email in emails:
        uid = db.execute(
            text("SELECT id FROM users WHERE lower(email) = lower(:e)"), {"e": email}
        ).scalar()
        if uid is None:
            continue
        params = {"id": uid}
        for stmt in (
            "UPDATE alerts SET acknowledged_by = NULL WHERE acknowledged_by = :id",
            "UPDATE alerts SET resolved_by = NULL WHERE resolved_by = :id",
            "UPDATE training_jobs SET triggered_by = NULL WHERE triggered_by = :id",
            "UPDATE model_registry SET trained_by = NULL WHERE trained_by = :id",
            "UPDATE audit_log SET user_id = NULL WHERE user_id = :id",
            "UPDATE user_invitations SET invited_by = NULL WHERE invited_by = :id",
            "DELETE FROM user_invitations WHERE invited_by = :id",
            "DELETE FROM user_site_scopes WHERE user_id = :id",
            "DELETE FROM user_roles WHERE user_id = :id",
            "DELETE FROM refresh_tokens WHERE user_id = :id",
            "DELETE FROM password_reset_tokens WHERE user_id = :id",
            "DELETE FROM kiosk_devices WHERE created_by = :id",
            "DELETE FROM users WHERE id = :id",
        ):
            _exec_ok(db, stmt, params)
        still = db.execute(text("SELECT id FROM users WHERE id = :id"), params).scalar()
        if still is None:
            deleted += 1
    return deleted


def purge(db, *, confirm: bool) -> dict:
    report = audit(db)
    sensor_ids = [f["id"] for f in report["findings"] if f["kind"] == "sensor"]
    site_ids = [f["id"] for f in report["findings"] if f["kind"] == "site"]
    emails = [f["email"] for f in report["findings"] if f["kind"] == "user"]
    if KEEP_EMAIL:
        emails = [e for e in emails if e.lower() != KEEP_EMAIL]

    summary: dict = {
        "sensors": len(sensor_ids),
        "sites": len(site_ids),
        "users": len(emails),
        "alerts_without_forecast": next(
            (f["count"] for f in report["findings"] if f["kind"] == "alerts_without_forecast"),
            0,
        ),
        "demo_readings": next(
            (f["count"] for f in report["findings"] if f["kind"] == "demo_readings"),
            0,
        ),
        "kept_superadmin": KEEP_EMAIL or None,
    }

    if not confirm:
        summary["dry_run"] = True
        return summary

    if sensor_ids:
        db.execute(
            text(
                """
                DELETE FROM alert_outcomes
                WHERE alert_id IN (SELECT id FROM alerts WHERE sensor_id = ANY(:ids))
                """
            ),
            {"ids": sensor_ids},
        )
        db.execute(text("DELETE FROM alerts WHERE sensor_id = ANY(:ids)"), {"ids": sensor_ids})
        db.execute(text("DELETE FROM forecasts WHERE sensor_id = ANY(:ids)"), {"ids": sensor_ids})
        db.execute(
            text("DELETE FROM gas_readings WHERE sensor_id = ANY(:ids)"), {"ids": sensor_ids}
        )
        db.execute(text("DELETE FROM sensors WHERE id = ANY(:ids)"), {"ids": sensor_ids})

    db.execute(
        text(
            """
            DELETE FROM alert_outcomes
            WHERE alert_id IN (SELECT id FROM alerts WHERE forecast_id IS NULL)
            """
        )
    )
    deleted_alerts = db.execute(text("DELETE FROM alerts WHERE forecast_id IS NULL")).rowcount

    for sid in site_ids:
        n_left = db.execute(
            text("SELECT count(*) FROM sensors WHERE site_id = :id"), {"id": sid}
        ).scalar()
        if not n_left:
            db.execute(text("DELETE FROM user_site_scopes WHERE site_id = :id"), {"id": sid})
            db.execute(text("DELETE FROM sites WHERE id = :id"), {"id": sid})

    n_users = _delete_users(db, emails)

    import json

    meta = {
        **summary,
        "deleted_users": n_users,
        "deleted_alerts_no_forecast": int(deleted_alerts or 0),
    }
    # INSERT crudo: evita flush ORM si algún mapper no está cargado
    db.execute(
        text(
            """
            INSERT INTO audit_log (user_id, action, resource_type, resource_id, metadata)
            VALUES (NULL, 'data.purge_demo', 'database', NULL, CAST(:meta AS jsonb))
            """
        ),
        {"meta": json.dumps(meta)},
    )
    db.commit()
    summary["dry_run"] = False
    summary["deleted_users"] = n_users
    summary["deleted_alerts_no_forecast"] = int(deleted_alerts or 0)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()

    from tests.db_urls import assert_isolated, load_urls

    assert_isolated(*load_urls())

    db = SessionLocal()
    try:
        summary = purge(db, confirm=args.confirm)
    finally:
        db.close()

    print(summary)
    if not args.confirm:
        print("Dry-run. Pasa --confirm para borrar.")
        return 0

    db = SessionLocal()
    try:
        after = audit(db)
    finally:
        db.close()
    db_findings = [f for f in after["findings"] if f["kind"] != "code_string"]
    print(f"Tras purga, hallazgos DB: {len(db_findings)}")
    for f in db_findings:
        print("-", f)
    print(
        "Si no queda admin: define SUPERADMIN_* en el entorno y corre "
        "python scripts/create_superadmin.py"
    )
    return 0 if not db_findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
