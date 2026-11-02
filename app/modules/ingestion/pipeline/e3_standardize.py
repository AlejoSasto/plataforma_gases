from __future__ import annotations

import pandas as pd

from app.modules.ingestion.pipeline.types import StageResult
from app.shared.gas_catalog import canonicalize_gas_type, normalize_sensor_code, normalize_site_name
from ml_core.domain.units import CanonicalUnitError, to_canonical


def e3_standardize(df: pd.DataFrame) -> StageResult:
    rows_in = int(len(df))
    work = df.copy()
    work["sensor_code"] = [normalize_sensor_code(v) for v in work["Sensor"].tolist()]
    gas_src = work["Descripción"] if "Descripción" in work.columns else work["Gas"]
    alt = work["Gas"] if "Gas" in work.columns else gas_src
    gases = []
    for a, b in zip(gas_src.tolist(), alt.tolist()):
        gases.append(canonicalize_gas_type(a if pd.notna(a) and str(a).strip() else b))
    work["gas"] = gases
    if "Sitio" in work.columns:
        work["site_name"] = [normalize_site_name(v) for v in work["Sitio"].tolist()]
    else:
        work["site_name"] = "Sin sitio asignado"

    values = []
    units = []
    conversions = 0
    unknown = 0
    for _, row in work.iterrows():
        raw_u = row.get("Unidad")
        try:
            v, u = to_canonical(float(row["Leyendo"]), gas_code=str(row["gas"]), unit=raw_u)
            if raw_u and u != str(raw_u).strip():
                conversions += 1
            values.append(v)
            units.append(u)
        except (CanonicalUnitError, TypeError, ValueError):
            values.append(float(row["Leyendo"]))
            units.append(str(raw_u or ""))
            unknown += 1
    work["value_canonical"] = values
    work["unit_canonical"] = units
    return StageResult(
        name="E3",
        dataframe=work,
        rows_in=rows_in,
        rows_out=int(len(work)),
        details={"conversions": conversions, "unidad_desconocida": unknown},
    )
