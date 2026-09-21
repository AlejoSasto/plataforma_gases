# Plan 13 — MVP forecast operativo + home por gas + UX presentación

> Cierra el gap thesis: en entrenamiento ya existía regresión a 5–10 min (RMSE) y clasificación; en **operación** solo corría riesgo. Este plan expone forecast de concentración en runtime, gráfica en home por tipo de gas, normalización de nombres y pulido UI para demo/MVP.

## Objetivo

1. Inferencia dual: `predicted_concentration` (horizonte 5–10 min) + `risk_level`.
2. Home operador con Chart.js (real vs proyectado) por CH₄ / CO / H₂S.
3. Catálogo canónico de gases/sensores/sitios (sin `LEL(CH4)`, `SIN_SITIO`, `Sensor SN:` crudos en UI).
4. Documentación alineada al DoD thesis.

## Prerrequisitos

- Plan 12 (Model Zoo) operativo.
- Datos en `gas_readings` y al menos un modelo sequence entrenable.

## Fases

### A — Catálogo canónico
- [x] `app/shared/gas_catalog.py` (alias → CH4/CO/H2S/CO2/O2/NO2)
- [x] Normalización en ETL (`sensors_ingestion/service.py`)
- [x] `scripts/normalize_sensors_display.py` (backfill)
- [x] `display_gas` / `display_sensor_code` / `display_site_name` en `formatting.py`

### B — Forecast operativo
- [x] Columnas `predictions.predicted_concentration`, `horizon_minutes` (Alembic `a1b2c3d4e5f6`)
- [x] Inferencia torch: desnormaliza `reg` con `reg_mean`/`reg_std` del `.pt`
- [x] Preferencia production: familia `sequence` + task `both`/`regression`
- [x] Script `scripts/retrain_promote_dl_forecast.py` (LSTM/GRU/Transformer)

### C — Home chart
- [x] `GET /dashboard/api/forecast-by-gas?site_id&hours&horizon_minutes`
- [x] `operador.html`: panel Chart.js + tabs por gas + polling ~10 s
- [x] Empty state si no hay modelo sequence en production

### D — Pulido UX
- [x] Brand “Monitoreo predictivo de gases · mina”
- [x] Fechas cortas en alertas, audit, ingeniero, ingesta UI
- [x] Badge “Forecast activo” en modelos production sequence
- [x] Login / 403 copy alineados a prevención 5–10 min

### E — Docs
- [x] Este plan + actualización `CONTEXTO_SISTEMA.md`

## Definition of Done

| Criterio | Verificación |
|----------|--------------|
| Home muestra gráfica CH4/CO/H2S real + proyección | `/` con modelo sequence en production |
| Inferencia persiste concentración + riesgo | Filas en `predictions` con ambos campos |
| Nombres legibles | Sin `SIN_SITIO` / `LEL(CH4)` crudos en UI |
| Fechas legibles | `dd/mm/aaaa HH:MM` en flujos demo |
| Umbrales thesis documentados | RMSE≤0.05, Recall≥0.95, Precisión≥0.90 (gates en métricas; en datos reales el RMSE estricto puede no alcanzarse — documentar al promover) |

## Scripts útiles

```bash
python scripts/normalize_sensors_display.py
python scripts/retrain_promote_dl_forecast.py
alembic upgrade head
```

## Fuera de alcance

Plan 09 (GCP) y Plan 10 (hardening completo).
