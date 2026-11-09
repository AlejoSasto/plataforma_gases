"""Carga el mapeo equipo → labor. Activa el tipo de sitio del metano.

CSV: serial,site_name,site_kind,map_x,map_y
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def apply_map(db, rows: list[dict[str, str]]) -> dict[str, int]:
    from app.modules.catalog.models import NormativeThreshold
    from app.modules.sensors_ingestion.instruments import ensure_instrument
    from app.modules.sensors_ingestion.models import Site
    from ml_core.domain.thresholds import SITE_METHANE

    sites_with_xy = 0
    for row in rows:
        site = db.query(Site).filter(Site.name == row["site_name"]).one_or_none()
        if site is None:
            site = Site(name=row["site_name"], description=row.get("site_kind") or "")
            db.add(site)
            db.flush()
        instrument = ensure_instrument(db, row["serial"])
        instrument.site_id = site.id
        if row.get("map_x") and row.get("map_y"):
            sites_with_xy += 1
    if sites_with_xy >= 3:
        for spec in SITE_METHANE:
            exists = (
                db.query(NormativeThreshold)
                .filter(
                    NormativeThreshold.gas_code == spec.gas_code,
                    NormativeThreshold.level == spec.level,
                    NormativeThreshold.site_kind == spec.site_kind,
                    NormativeThreshold.metric == spec.metric,
                )
                .one_or_none()
            )
            if exists is None:
                db.add(
                    NormativeThreshold(
                        gas_code=spec.gas_code,
                        level=spec.level,
                        direction=spec.direction,
                        value=spec.value,
                        source_reference=spec.source_reference,
                        verified=False,
                        metric=spec.metric,
                        site_kind=spec.site_kind,
                        kind=spec.kind,
                        article=spec.article,
                    )
                )
    db.commit()
    return {"rows": len(rows), "sites_with_coordinates": sites_with_xy}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    args = parser.parse_args()
    path = Path(args.csv_path)
    if not path.exists():
        print(f"No existe {path}", file=sys.stderr)
        return 1
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        summary = apply_map(db, rows)
    finally:
        db.close()
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
