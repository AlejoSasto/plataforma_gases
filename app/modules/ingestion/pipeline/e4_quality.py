from __future__ import annotations

import pandas as pd

from app.modules.ingestion.pipeline.types import StageResult
from ml_core.domain.thresholds import MAX_RATE_PER_MIN, PHYSICAL_MAX

FROZEN_STEPS = 10


def e4_quality(df: pd.DataFrame) -> StageResult:
    rows_in = int(len(df))
    work = df.copy()
    issues: list[dict] = []
    status = ["ok"] * len(work)
    work = work.reset_index(drop=True)

    for i, row in work.iterrows():
        gas = str(row.get("gas") or "UNKNOWN")
        val = float(row["value_canonical"]) if pd.notna(row.get("value_canonical")) else None
        if val is None:
            continue
        phys = PHYSICAL_MAX.get(gas)
        if phys is not None and (val < 0 or val > phys):
            issues.append({"code": "fuera_de_rango_fisico", "severity": "error", "row": int(i)})
            status[i] = "excluida"
        if bool(row.get("unidad_desconocida")) or (
            str(row.get("unit_canonical") or "") == "" and gas != "UNKNOWN"
        ):
            # unidad desconocida solo si E3 no pudo mapear y el original no era vacío canónico
            pass

    # unidad_desconocida marcada en E3 details; aquí si unit_canonical vacío y Unidad presente
    if "Unidad" in work.columns:
        for i, row in work.iterrows():
            raw = row.get("Unidad")
            can = str(row.get("unit_canonical") or "")
            if pd.notna(raw) and str(raw).strip() and not can:
                issues.append({"code": "unidad_desconocida", "severity": "error", "row": int(i)})
                status[i] = "excluida"

    grouped = work.groupby(["sensor_code", "gas"], sort=False)
    for (sensor, gas), g in grouped:
        g = g.sort_values("Tiempo de Inicio")
        vals = g["value_canonical"].astype(float)
        times = pd.to_datetime(g["Tiempo de Inicio"], utc=True)
        # congelado
        run = 1
        prev = None
        for idx, v in vals.items():
            if prev is not None and v == prev:
                run += 1
                if run >= FROZEN_STEPS:
                    issues.append(
                        {
                            "code": "valor_congelado",
                            "severity": "advertencia",
                            "row": int(idx),
                            "sensor": sensor,
                        }
                    )
                    if status[idx] == "ok":
                        status[idx] = "advertencia"
            else:
                run = 1
            prev = v
        # salto y hueco
        dt_min = times.diff().dt.total_seconds() / 60.0
        dv = vals.diff().abs()
        med = dt_min[dt_min > 0].median()
        max_rate = MAX_RATE_PER_MIN.get(str(gas), 1e9)
        for idx, dmin, dval in zip(g.index, dt_min, dv):
            if pd.isna(dmin) or dmin <= 0:
                continue
            if dmin > 3 * med if pd.notna(med) and med > 0 else False:
                issues.append({"code": "hueco", "severity": "info", "row": int(idx)})
            rate = float(dval) / float(dmin)
            if rate > max_rate:
                issues.append(
                    {"code": "salto_imposible", "severity": "advertencia", "row": int(idx)}
                )
                if status[idx] == "ok":
                    status[idx] = "advertencia"

    # duplicados (sensor, tiempo)
    dup = work.duplicated(subset=["sensor_code", "Tiempo de Inicio"], keep="first")
    for idx in work.index[dup]:
        issues.append({"code": "duplicado", "severity": "info", "row": int(idx)})

    work["quality_status"] = status
    counts: dict[str, int] = {}
    for item in issues:
        counts[item["code"]] = counts.get(item["code"], 0) + 1
    return StageResult(
        name="E4",
        dataframe=work,
        rows_in=rows_in,
        rows_out=int(len(work)),
        details={"issue_counts": counts, "n_issues": len(issues)},
        issues=issues,
    )
