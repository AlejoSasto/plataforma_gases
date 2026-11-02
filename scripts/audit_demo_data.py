"""Auditoría de datos demo en DB de desarrollo y en el código (Plan 24 F1).

  python scripts/audit_demo_data.py
  exit 0 si limpio; 1 si hay hallazgos.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from app.core.database import SessionLocal

DEMO_SENSOR_RE = re.compile(r"(TEST#|LIFE#|PRED#|^P19[A-Z]?$|SN#MINA)", re.I)
DEMO_SITE_NAMES = {"Mina Norte", "Zona Plan19 A", "Zona Plan19 B", "Frente 3", "Frente 3 Sur"}
BLACKLIST_STRINGS = [
    "Frente 3 Sur",
    "Frente 3",
    "Ana Rojas",
    "Carlos Pinzón",
    "Carlos Pinzon",
    "0,72",
    "Mina caso de estudio",
]
CODE_GLOBS = [
    "app/templates/**/*.html",
    "app/shared/copy.py",
]


def _scan_code() -> list[dict]:
    hits: list[dict] = []
    for pattern in CODE_GLOBS:
        for path in ROOT.glob(pattern):
            if not path.is_file():
                continue
            text_body = path.read_text(encoding="utf-8", errors="replace")
            for needle in BLACKLIST_STRINGS:
                if needle in text_body:
                    hits.append(
                        {
                            "kind": "code_string",
                            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                            "needle": needle,
                        }
                    )
    return hits


def audit(db) -> dict:
    findings: list[dict] = []

    for (email,) in db.execute(text("SELECT email FROM users ORDER BY id")).all():
        if email and ("@example.com" in email.lower() or email.lower().startswith("test.")):
            findings.append({"kind": "user", "email": email})

    for row in db.execute(text("SELECT id, name FROM sites ORDER BY id")).all():
        if row.name in DEMO_SITE_NAMES:
            findings.append({"kind": "site", "id": row.id, "name": row.name})

    for row in db.execute(text("SELECT id, code, gas_type FROM sensors ORDER BY id")).all():
        if DEMO_SENSOR_RE.search(row.code or ""):
            findings.append(
                {"kind": "sensor", "id": row.id, "code": row.code, "gas_type": row.gas_type}
            )

    orphan_alerts = db.execute(
        text(
            """
            SELECT count(*) FROM alerts
            WHERE forecast_id IS NULL AND gas_reading_id IS NULL
            """
        )
    ).scalar()
    if orphan_alerts:
        findings.append({"kind": "alerts_no_lineage", "count": int(orphan_alerts)})

    no_fc = db.execute(text("SELECT count(*) FROM alerts WHERE forecast_id IS NULL")).scalar()
    if no_fc:
        findings.append({"kind": "alerts_without_forecast", "count": int(no_fc)})

    demo_sensor_ids = [f["id"] for f in findings if f["kind"] == "sensor"]
    if demo_sensor_ids:
        n_read = db.execute(
            text("SELECT count(*) FROM gas_readings WHERE sensor_id = ANY(:ids)"),
            {"ids": demo_sensor_ids},
        ).scalar()
        if n_read:
            findings.append({"kind": "demo_readings", "count": int(n_read)})
    # Sensores sin ninguna lectura ligada a etl_run
    n_orphan_sensors = db.execute(
        text(
            """
            SELECT count(*) FROM sensors s
            WHERE NOT EXISTS (
              SELECT 1 FROM gas_readings g
              WHERE g.sensor_id = s.id AND g.etl_run_id IS NOT NULL
            )
            """
        )
    ).scalar()
    if n_orphan_sensors:
        findings.append({"kind": "sensors_without_etl", "count": int(n_orphan_sensors)})

    findings.extend(_scan_code())
    return {"ok": len(findings) == 0, "findings": findings, "n": len(findings)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        report = audit(db)
    finally:
        db.close()

    if args.json:
        import json

        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Hallazgos: {report['n']}")
        for f in report["findings"]:
            print("-", f)
        if report["ok"]:
            print("OK: sin datos demo detectados")
        else:
            print("FAIL: hay datos demo. Usa scripts/purge_demo_data.py --confirm")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
