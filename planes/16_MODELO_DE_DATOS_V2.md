# 16 — Modelo de datos v2

**Objetivo:** un modelo de datos que soporte datos reales con calidad trazable, pronósticos probabilísticos, episodios reales para evaluar, avisos con resultado medido, explicaciones y un control de acceso más fino.
**Prerrequisitos:** Plan 15 F0–F1 (decisión G0 y purga de sintéticos).
**Regla:** todo vía Alembic, con `downgrade` funcional y probado (Plan 20).

---

## 1. Diagrama lógico

```
ACCESO
users ─┬─ user_roles ── roles ── role_permissions ── permissions
       ├─ user_site_scopes ── sites
       ├─ refresh_tokens (sesiones)
       ├─ password_reset_tokens
       ├─ user_invitations
       └─ kiosk_devices (pantallas de sala de control)

CATÁLOGO
gas_types ── normative_thresholds
app_settings

DATOS
sites ── sensors ── gas_readings ── etl_runs ── etl_run_steps
                 │        └── data_quality_issues
                 └── reading_grid
                 └── threshold_events            (verdad de referencia)

MODELOS
model_registry ── model_evaluations (por pliegue)
training_jobs

PRONÓSTICO Y AVISOS
forecasts ── forecast_quantiles
     └── forecast_explanations
     └── alerts ── alert_notifications ── stakeholders ── stakeholder_subscriptions
            └── alert_outcomes                    (¿fue acertado? ¿con cuánta anticipación?)

SALIDAS
reports · audit_log
```

---

## 2. Tablas nuevas y modificadas

### 2.1 Catálogo

**`gas_types`** (nueva; reemplaza las constantes de `gas_catalog.py`, que pasa a leer de la DB con caché)

| Campo | Tipo | Notas |
|-------|------|-------|
| code | varchar(10) PK | CH4, CO, H2S, O2, CO2, NO2 |
| display_name | varchar | “Metano” |
| plain_description | text | “Gas inflamable que se libera del carbón” (para la UI) |
| canonical_unit | varchar | `% vol`, `ppm` |
| lel_percent_vol | numeric null | Solo CH₄ (5,0 o 4,4) |
| physical_max | numeric | Rango físico del instrumento |
| max_rate_per_min | numeric | Límite de “salto imposible” |
| priority | smallint | 1 = CH₄, 2 = CO, 3 = H₂S… |
| is_active | bool | |

**`normative_thresholds`** (nueva)

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| gas_code | FK gas_types | |
| level | enum `vigilar`/`actuar`/`evacuar` | |
| direction | enum `above`/`below` | O₂ = below |
| value | numeric | En unidad canónica |
| source_reference | text | “Decreto 1886 de 2015, art. …” |
| verified | bool | false hasta verificar el artículo |
| valid_from | timestamptz | Los avisos usan el umbral vigente en su fecha |
| created_by | FK users | |
| UQ | (gas_code, level, valid_from) | |

**`app_settings`** (nueva, clave-valor tipado)

| key | Ejemplo |
|-----|---------|
| `grid_step_minutes` | 1 |
| `forecast_horizons_min` | [5, 10] |
| `shift_hours` | 8 |
| `alert_persistence_steps` | 2 |
| `language_register_lint` | true |

### 2.2 Datos

**`sensors`** (modificada): agrega `display_name`, `kind` (`fijo`/`portatil`/`desconocido`), `location_note` (texto libre: “Frente 3, galería norte”), `is_active`.

**`gas_readings`** (modificada)
- Agrega `value_canonical numeric` y `unit_canonical varchar`, calculados en E3.
- Agrega `quality_status` enum `ok`/`advertencia`/`excluida`.
- **Restricción** `UNIQUE (sensor_id, tiempo_inicio)`.
- `is_synthetic` se conserva con `CHECK (is_synthetic = false)` tras la purga (decisión documentada: la plataforma ya no admite sintéticos).
- Índice `(sensor_id, tiempo_inicio DESC)`.

**`etl_run_steps`** (nueva): `etl_run_id`, `step` (E1…E6), `rows_in`, `rows_out`, `rows_rejected`, `duration_ms`, `details JSONB`.

**`data_quality_issues`** (nueva): `id`, `gas_reading_id null`, `sensor_id`, `etl_run_id`, `code` (ver Plan 15 F2), `severity`, `detected_at`, `details JSONB`.

**`reading_grid`** (nueva; la entrada de los modelos)

| Campo | Notas |
|-------|-------|
| sensor_id, ts | PK compuesta |
| value | null si falta |
| is_imputed | Hueco corto rellenado |
| is_missing | Hueco largo |
| source_etl_run_id | Linaje |

Particionado declarativo por mes si supera ~5 M de filas (no es necesario con el volumen actual; se deja documentado).

**`threshold_events`** (nueva; la verdad de referencia)

| Campo | Notas |
|-------|-------|
| id, sensor_id, gas_code, level | |
| threshold_id | FK al umbral vigente |
| started_at, ended_at | Del cruce de inicio al regreso bajo el umbral |
| peak_value, peak_at | |
| detected_by | `etl` (recalculable con `scripts/rebuild_events.py`) |

### 2.3 Modelos

**`model_registry`** (modificada): agrega `family` (`baseline`/`tabular`/`recurrente`/`transformer`/`fundacional`), `problem_spec JSONB` (lookback, horizontes, cuantiles), `calibration JSONB` (cuantiles conformales por horizonte y $\pi_\ell$ por nivel), `selection_score JSONB`. Los estados siguen siendo `staging`/`production`/`archived`.

**`model_evaluations`** (nueva)

| Campo | Notas |
|-------|-------|
| model_id, fold_index | |
| fold_spec JSONB | Rangos de entrenamiento, calibración y validación; brecha de purga |
| gas_code, horizon_min | Una fila por combinación |
| forecast_metrics JSONB | MAE, RMSE, MASE, pinball, cobertura, ancho |
| event_metrics JSONB | Por nivel: recall, precisión, F1, tasa FN, anticipación p10/p50, falsas alarmas/turno, IC bootstrap |
| is_final_test | true solo para la prueba final intocable |

### 2.4 Pronóstico y avisos

**`forecasts`** (nueva; reemplaza `predictions`)

| Campo | Notas |
|-------|-------|
| id, sensor_id, model_id | |
| issued_at | Último paso de rejilla usado |
| status_level | `normal`/`vigilar`/`actuar`/`evacuar` (estado operativo resultante) |
| exceed_prob JSONB | `{"vigilar": {"5": 0.12, "10": 0.31}, ...}` (uso interno; la UI lo traduce) |
| confidence | `alta`/`media`/`baja` (del ancho del intervalo calibrado) |
| latency_ms | |
| UQ | (sensor_id, model_id, issued_at), idempotente |

**`forecast_quantiles`** (nueva): `forecast_id`, `horizon_min`, `q10`, `q50`, `q90`, `q95`.

**`forecast_explanations`** (nueva): `forecast_id`, `method` (`tft_vsn`, `integrated_gradients`, `shap`), `factors JSONB` (lista ordenada `{factor_code, weight, direction}`), `plain_text` (frase generada con plantillas; Plan 17 F6).

**`alerts`** (modificada)
- Agrega `forecast_id`, `kind` (`anticipado` = por pronóstico / `confirmado` = el sensor ya superó el umbral), `level` (enum nuevo), `threshold_id`, `expected_at` (cuándo se espera el cruce), `plain_message`, `plain_recommendation`.
- Se conservan los estados `abierta` → `reconocida` → `resuelta`. Agrega `resolved_by`, que faltaba.

**`alert_outcomes`** (nueva; alimenta “¿Qué tan confiable es el sistema?”)

| Campo | Notas |
|-------|-------|
| alert_id | PK/FK |
| outcome | `acertado` / `falsa_alarma` / `pendiente` |
| event_id | FK `threshold_events` si se confirmó |
| lead_minutes | Anticipación real |
| evaluated_at | Job que cierra los resultados pasado $k_{\max}$ + tolerancia |

Se agrega también una vista `missed_events_v`: episodios sin aviso previo (= no detectados).

### 2.5 Acceso (detalle en el Plan 19)

- `users`: agrega `failed_login_count`, `locked_until`, `last_login_at`, `must_change_password`, `password_changed_at`, `totp_secret_enc` (cifrado con clave de entorno), `totp_enabled`.
- `user_site_scopes`: `user_id`, `site_id` (sin filas = todos los sitios, solo si el rol lo permite).
- `password_reset_tokens`: `token_hash`, `user_id`, `expires_at`, `used_at`.
- `user_invitations`: `email`, `role_ids JSONB`, `token_hash`, `invited_by`, `expires_at`, `accepted_at`.
- `refresh_tokens`: agrega `user_agent`, `ip`, `last_used_at` (para listar sesiones activas).
- `kiosk_devices`: `name`, `token_hash`, `site_ids JSONB`, `created_by`, `revoked_at`, `last_seen_at`.

---

## 3. Migraciones (orden)

| # | Revisión | Contenido | Datos |
|---|----------|-----------|-------|
| M1 | `catalog_gas_types_thresholds_settings` | gas_types, normative_thresholds, app_settings | Semillas en scripts, no en la migración |
| M2 | `readings_quality_lineage` | Columnas nuevas en sensors y gas_readings, etl_run_steps, data_quality_issues | Rellenar `value_canonical`; deduplicar **antes** de la UQ (script M2a) |
| M3 | `readings_no_synthetic_check` | CHECK `is_synthetic=false` | Requiere el Plan 15 F1 ejecutado |
| M4 | `reading_grid_and_events` | reading_grid, threshold_events | `scripts/rebuild_grid.py`, `scripts/rebuild_events.py` |
| M5 | `models_evaluations` | Columnas nuevas en model_registry, model_evaluations | — |
| M6 | `forecasts_explanations` | forecasts, forecast_quantiles, forecast_explanations | — |
| M7 | `alerts_v2_outcomes` | Columnas nuevas en alerts, alert_outcomes, vista missed_events_v | Avisos antiguos: `kind='confirmado'` si venían de alarma dura; el resto se archiva |
| M8 | `access_v2` | Campos de users, scopes, reset, invitaciones, kiosk, sesiones | — |
| M9 | `drop_predictions` | Elimina `predictions` y la FK `alerts.prediction_id` | Solo tras verificar que nada la lee (`grep` en CI) |

Cada migración debe pasar `upgrade → downgrade → upgrade` en la DB de pruebas (Plan 20).

---

## 4. Organización por módulos

| Módulo | Tablas propias |
|--------|----------------|
| `catalog` (nuevo) | gas_types, normative_thresholds, app_settings |
| `ingestion` (renombre de `sensors_ingestion`) | sites, sensors, gas_readings, etl_runs, etl_run_steps, data_quality_issues, reading_grid, threshold_events |
| `ml_training` | model_registry, model_evaluations, training_jobs |
| `forecasting` (reemplaza `predictions`) | forecasts, forecast_quantiles, forecast_explanations |
| `alerts` | alerts, alert_outcomes |
| `stakeholders` | sin cambios |
| `access` (fusiona `auth`, `users`, `roles_permissions`) | users, roles, permissions, scopes, tokens, invitaciones, kiosk |
| `reports`, `audit` | sin cambios estructurales |

Cada uno con `models.py`, `schemas.py`, `repository.py`, `service.py` y `router.py`. Los repositorios son el **único** lugar con SQL/ORM. Los servicios no importan modelos ORM de otro módulo: llaman a su servicio.

---

## Definición de terminado del Plan 16
- [x] M1–M9 aplican y revierten limpias en la DB de pruebas.
- [x] Semillas idempotentes (`seed_gas_types`, `seed_thresholds`, `seed_settings`).
- [x] `rebuild_grid` y `rebuild_events` reproducen los mismos conteos en dos corridas.
- [x] Ningún código referencia `predictions` (prueba de búsqueda en el código fuente).
- [x] Diagrama actualizado en `CONTEXTO_SISTEMA.md` §6.
- [x] `python scripts/verify.py --plan 16` en verde.
