"""Backfill: normaliza gas_type, códigos de sensor y nombres de sitio en BD."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.modules.sensors_ingestion.models import Sensor, Site
from app.shared.gas_catalog import (
    canonicalize_gas_type,
    normalize_sensor_code,
    normalize_site_name,
)


def main() -> int:
    db = SessionLocal()
    try:
        n_sites = n_sensors = 0
        for site in db.query(Site).all():
            new_name = normalize_site_name(site.name)
            if new_name != site.name:
                # Evitar colisión unique
                clash = (
                    db.query(Site)
                    .filter(Site.name == new_name, Site.id != site.id)
                    .first()
                )
                if clash is None:
                    site.name = new_name
                    db.add(site)
                    n_sites += 1

        for sensor in db.query(Sensor).all():
            new_gas = canonicalize_gas_type(sensor.gas_type)
            new_code = normalize_sensor_code(sensor.code)
            changed = False
            if new_gas != sensor.gas_type:
                sensor.gas_type = new_gas
                changed = True
            if new_code != sensor.code:
                # unique (code, gas_type)
                clash = (
                    db.query(Sensor)
                    .filter(
                        Sensor.code == new_code,
                        Sensor.gas_type == new_gas,
                        Sensor.id != sensor.id,
                    )
                    .first()
                )
                if clash is None:
                    sensor.code = new_code
                    changed = True
            if changed:
                db.add(sensor)
                n_sensors += 1

        db.commit()
        print(f"OK sites_updated={n_sites} sensors_updated={n_sensors}")
        return 0
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"ERROR: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
