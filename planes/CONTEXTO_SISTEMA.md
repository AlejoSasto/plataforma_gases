# Contexto del sistema — Vigía (gases en la mina)

> **Documento canónico de contexto.** Describe el **estado real del código** (auditoría 2026-11-02). El mapa de ejecución es [`00_INDICE_Y_ROADMAP.md`](00_INDICE_Y_ROADMAP.md). El paquete **14–22** es el destino del jurado + identidad visual; gana a los planes 04, 05, 07, 11, 12 y 13 cuando haya conflicto. Ante duda: **código = qué hay hoy**.

**Qué cubre:** propósito, planes, stack, arquitectura, datos de campo, notebooks, modelo de datos v2, RBAC y credenciales, flujos (auth / ETL / ML / alertas / reportes), mapa HTTP, UX Vigía, env, arranque, tests, migraciones y pendientes.

**Qué no cubre (a propósito):** marco teórico de la tesis, dumps de notebooks, artefactos MLflow (`mlruns/`), secretos reales de `.env`, ni el código línea a línea.

| Campo | Valor |
|-------|--------|
| Nombre de trabajo (UI) | **Vigía** · descriptor «Gases en la mina» (`app/shared/copy.py`) |
| Nombre formal (tesis) | Plataforma de monitoreo y predicción de gases |
| Arquitectura | Monolito FastAPI + Jinja2 + PostgreSQL |
| Versión app | `0.1.0` (`app/main.py`, título FastAPI `Vigía`) |
| Runtime | Python 3.11+ |
| Base de datos | `proyecto_gases` (Compose: host `5433`); tests: `proyecto_gases_test` |
| Alembic head | `c1d2e3f4a5b6` |
| Actualizado | 2026-11-02 (Vigía + login seguro + planes 15–20) |

### Índice rápido

| § | Tema |
|---|------|
| 1–3 | Propósito, planes, stack |
| 4 | Estructura del repo y módulos |
| 5 | Datasets, catálogo de gases, notebooks |
| 6–7 | Modelo de datos, roles y permisos |
| 8 | Flujos (auth, ETL, Model Zoo, inferencia, alertas, reportes) |
| 9–10 | Rutas HTTP y UX |
| 11–12 | Env y arranque local |
| 13–14 | Reglas de trabajo y pendiente |
| 15 | Tests, migraciones, artefactos legado |

---

## 1. Propósito

Sistema web para:

1. **Ingestar** lecturas de sensores de gases (Excel `dls_report` / CSV processed).
2. **Entrenar y promover** modelos de ML (riesgo + forecast de concentración 5–10 min).
3. **Predecir** concentración a 6/12/18 min con cuantiles; **generar avisos** en lenguaje natural.
4. **Notificar** a partes interesadas (email / WhatsApp stub).
5. **Visualizar** proyección por tipo de gas, semáforo operativo, ejecutivo e histórico.
6. **Exportar** reportes PDF/Excel.

No es un microservicio; toda la lógica vive en un solo proceso FastAPI con módulos de dominio. **No usa LLMs**: el Model Zoo es sklearn / XGBoost / PyTorch propio. Detalle de algoritmos, features, métricas thesis, promote e inferencia: **§8.3–8.4**.

---

## 2. Estado de planes

| Plan | Fase | Estado |
|------|------|--------|
| 01 Infraestructura base | F0 | ✅ |
| 02 Auth / usuarios / roles | F1 | ✅ |
| 03 Ingesta ETL | F2 | ✅ |
| 04 ML entrenamiento | F3 | ✅ |
| 05 Predicciones / alertas | F4 | ✅ |
| 06 Stakeholders / notificaciones | F5 | ✅ |
| 07 Dashboard UI | F6 | ✅ |
| 08 Reportes | F7 | ✅ |
| 09 Despliegue GCP / CI-CD | F8 | ⬜ Pendiente |
| 10 Seguridad / hardening | F9 | ⬜ Resto pendiente (login/CSP/CSRF ✅ 2026-11-02) |
| 11 Mapeo UX/UI pantallas | Complementa F6 | ✅ |
| 12 Model Zoo / series / métricas thesis | Extiende F3–F4 | ✅ |
| 13 MVP forecast home + UX presentación | Cierra gap thesis operativo | ✅ historial (supersedido por 17–18) |
| Mejora UX consola profesional | Refino visual | ✅ historial |
| **14** Reformulación índice | Mapa jurado | ✅ documento 2026-11-01 |
| **15** Datos reales y formulación | OE1–OE2 | ✅ G0 6/12/18; ETL E1–E6; 0 sintéticos en DEV; `verify --plan 15` |
| **16** Modelo de datos v2 | forecasts, umbrales, linaje | ✅ M1–M9 + `c1d2e3f4a5b6`; catálogo sembrado en DEV; `verify --plan 16` |
| **17** Transformers y evaluación | OE3 | ✅ 10 adaptadores, conformal, decisión, `reports/thesis/`; `verify --plan 17` |
| **18** UX lenguaje natural | OE4 | ✅ Pantallas ES, copy, contraste; `verify --plan 18` |
| **19** Usuarios, roles y acceso | OE4 | ✅ 6 roles, CSRF, TOTP, kiosco; `verify --plan 19` |
| **20** Pruebas y bucle | transversal | ✅ DB test aislada, `verify` 13 etapas, E2E Playwright |
| **21** Sistema de diseño Vigía | OE4 identidad | ✅ Tokens, tipografía, ilustraciones; doc en `planes/21_*.md` |
| **22** Mockups → app | OE4 UI | ✅ Kit en `mockups/vigia-design-kit/`; cascarón aplicado en `app/` |
| Login / CSP (tramo Plan 10) | seguridad UI | ✅ POST `/ingresar`, strip query, CSRF ASGI, recursos locales |
| 09 Despliegue GCP | F8 | ⬜ edge-first pendiente |
| 10 Hardening (resto) | F9 | ⬜ k6, pip-audit, HSTS prod, backups |

Mapa y orden con compuertas: [`00_INDICE_Y_ROADMAP.md`](00_INDICE_Y_ROADMAP.md). `PLAN_EJECUCION_03_INGESTA_ETL.md` es playbook histórico del Plan 03.

---

## 3. Stack tecnológico

| Capa | Tecnología | Notas |
|------|------------|--------|
| API / web | FastAPI `0.1.0`, Uvicorn, Gunicorn | `app/main.py`; Gunicorn en Docker (no recarga Python montado) |
| Validación | Pydantic v2, pydantic-settings | Config vía env (`.env` + `app/core/config.py`) |
| ORM / migraciones | SQLAlchemy 2, Alembic | Head: `c1d2e3f4a5b6`. Nunca `create_all` |
| DB | PostgreSQL 15 | Host `5433` → `5432`; DEV `proyecto_gases`, TEST `proyecto_gases_test` |
| Auth | JWT + bcrypt + CSRF ASGI | Cookies HttpOnly; form POST `/ingresar` + JSON `/auth/login` |
| Frontend | Jinja2 + **Archivo** (UI) + **IBM Plex Mono** (solo Laboratorio) + ECharts 5 + Lucide sprite + htmx | **Sin CDN**; recursos en `app/static/` |
| Estilos | `tokens.css` (fuente Vigía) + `base` / `layout` / `components` | Color fuerte solo para estado de gases |
| Marca / mockups | `mockups/vigia-design-kit/`, `app/static/img/*.svg`, `app/static/brand/` | Planes 21–22 |
| ETL | pandas, openpyxl | Inbox + upload API + scripts CSV |
| Jobs | APScheduler | Inbox ETL e inferencia (mismo proceso) |
| ML | scikit-learn, XGBoost, **PyTorch**, MLflow `<3` | Zoo Plan 17 en `ml_core/forecasting/` |
| Reportes | ReportLab (PDF), openpyxl (Excel) | `storage/reports/` |
| Tests | pytest, httpx, Playwright (E2E) | DB de test aislada; `scripts/verify.py` |

Dependencias: `requirements.txt` (no hay `pyproject.toml` ni `pytest.ini`). Torch en Linux/Docker: CPU (`pip install torch --index-url https://download.pytorch.org/whl/cpu`). En Windows el `requirements` instala `torch` de PyPI.

---

## 4. Arquitectura y estructura

```
plataforma-gases/
├── app/
│   ├── main.py                 # App, routers, schedulers, /health
│   ├── core/                   # config, database, security, csrf, passwords, rate_limit, logging
│   ├── shared/                 # copy, design_tokens, access, dependencies, gas_catalog, templating
│   ├── modules/                # dominios (ver §6–§7); ingestion/pipeline E1–E6; forecasting/
│   ├── templates/              # Jinja2 (base, auth, dashboard, alerts, laboratorio, …)
│   └── static/                 # css/, fonts/, icons/sprite.svg, img/*.svg, brand/, vendor/, js/
├── ml_core/                    # forecasting/, validation/, domain/, features/, models/ (legado tabular)
├── migrations/versions/        # cadena Alembic (head c1d2e3f4a5b6)
├── scripts/                    # seed, verify, diagnose, load, train, purge_synthetic, …
├── tests/                      # unit, integration, guards, ui, e2e, perf
├── mockups/vigia-design-kit/   # tokens, mockups HTML, screenshots, tools (Planes 21–22)
├── notebooks/                  # investigación (no runtime) — ver §5.4
├── data/                       # raw/, processed/, inbox/
├── docs/                       # g0_visto_director, ux/, marca/, etl/
├── storage/                    # reports/, outbox/ (gitignored)
├── docker/                     # Dockerfile.app, mlflow, worker (placeholder)
├── planes/                     # 00, CONTEXTO, 01–22, BITACORA
├── .github/workflows/          # verify.yml (Plan 20)
├── docker-compose.yml          # db:5433, mlflow:5000, app:8000
├── alembic.ini
├── requirements.txt
└── .env.example
```

`mlruns/` es local/gitignored. `templates/home.html` es legado; el home operativo es `dashboard/hoy.html`.

### Convención por módulo

Plantilla objetivo en `app/modules/<nombre>/`:

- `models.py` — SQLAlchemy
- `schemas.py` — Pydantic
- `repository.py` — acceso a datos (si aplica)
- `service.py` — lógica de negocio
- `router.py` — HTTP API y/o HTML

**Estado real de archivos:**

| Módulo | models | schemas | repository | service | router / extra |
|--------|:------:|:-------:|:----------:|:-------:|----------------|
| `auth` | — (usa `users`) | sí | sí | sí | `router.py` (login HTML + API) |
| `users` | sí | sí | sí | sí | `router.py` |
| `roles_permissions` | sí | sí | sí | sí | `router.py` |
| `sensors_ingestion` | sí | sí | sí | sí | `router.py` + `scheduler.py` |
| `ml_training` | sí | sí | sí | sí | `router.py` |
| `catalog` | sí | sí | sí | sí | `router.py` + `seed.py` |
| `forecasting` | sí | sí | sí | sí | `router.py` + `scheduler.py` |
| `alerts` | sí | sí | — | sí | `router.py` + `rules.py` + `recommendations.py` |
| `stakeholders` | sí | sí | — | sí | `router.py` + `notifier.py` |
| `reports` | sí | sí | — | sí | `router.py` + `generator.py` |
| `dashboard` | — | — | — | sí | `ui_router.py` + `api_router.py` + `nav.py` |
| `audit` | sí | — | — | sí | `router.py` |

### Mapa de dependencias

```
core (config, db, security)
  ├── auth / users / roles_permissions     ← requeridos por casi todo
  ├── catalog
  ├── sensors_ingestion
  │     └── ml_training
  │           └── forecasting
  │                 └── alerts
  │                       └── stakeholders (notificaciones)
  ├── dashboard     (consume todo; UI + APIs de polling)
  ├── reports       (alerts, ML, visibilidad stakeholders)
  └── audit         (transversal)
```

---

## 5. Datos de campo y datasets

Fuente de verdad para entrenamiento/ingesta: `gas_readings` en PostgreSQL. Los archivos de `data/` son el origen y el respaldo.

### Dónde está cada cosa

| Ruta | Qué es | ¿Entra al ETL? |
|------|--------|----------------|
| `data/raw/dls_report_*.xlsx` | **56** Excel iNet (incluye copias `(1)`/`(2)`). Hoja `Resumen`, cabecera fila **24** | Sí (`ml_core.data_io.load_dls_report`) vía upload o inbox |
| `data/raw/alarmReport_*.xlsx` | **2** reportes de alarma | No (no hay parser) |
| `data/raw/Historial del registro de datos.xlsx` | Bitácora de **sesiones** de un MX6 CO2 (nov–dic 2024). No son lecturas | No |
| `data/processed/Procesamiento_de_Datos.csv` | Consolidado **real** | Sí (`--consolidado`) |
| `data/processed/Procesamiento_de_Datos_YYYY-MM.csv` | Mismo consolidado partido por mes (9 archivos) | Origen del consolidado |
| `data/processed/Procesamiento de Datos.xlsx` | Copia Excel del consolidado | No (el loader usa CSV) |
| `data/processed/Procesamiento_de_Datos_24m.csv` | Zoo aumentado a 24 meses | Sí (`--augmented-24m`, marca `is_synthetic`) |
| `data/processed/augmentation_manifest.json` | Trazabilidad source_month → target_month | Solo al marcar sintéticos (`ml_core/augmentation.py`) |
| `data/inbox/` | Cola automática (.xlsx/.xls) + `processed/` y `failed/` | Sí, si `ETL_INBOX_ENABLED` |
| `data/curated/` | Carpeta vacía (legado de un diseño anterior) | No |

**Compose:** el servicio `app` **no monta** `data/` ni copia `scripts/`. Inbox y carga CSV se ejecutan contra el host (`uvicorn` + `python scripts/...`), no dentro del contenedor.

Esquema canónico de 15 columnas: `ml_core/columns.py` (`Leyendo`, `Gas`, `Sensor`, `Tiempo de Inicio`, STEL/TWA, temperatura, etc.).

### Datos reales (consolidado)

~**13.894 filas**, **50 sensores**, **6 gases**. Rango: **2023-03-31** → **2025-12-11**. La columna `Sitio` en los CSV suele ir vacía (el ETL crea “Sin sitio asignado”).

| Mes | Filas | Notas |
|-----|------:|-------|
| 2023-03 | 40 | Un solo día |
| 2024-09 | 513 | |
| 2024-11 | 8.937 | Mes más denso |
| 2024-12 | 18 | Muy poco |
| 2025-08 | 236 | |
| 2025-09 | 322 | |
| 2025-10 | 184 | |
| 2025-11 | 2.344 | |
| 2025-12 | 1.300 | Hasta el día 11 |

Huecos: abr-2023–ago-2024, oct-2024, ene–jul 2025.

Gases (nombre → código canónico `gas_catalog`): CO2, CO, O2, H2S, NO2, gas combustible/`LEL(CH4)` → **CH4**. Prioridad thesis: **CH4, CO, H2S**.

Unidades típicas: `%vol`, `ppm`, `%lel`.

### Dataset sintético 24 meses (retirado del loader)

El archivo `Procesamiento_de_Datos_24m.csv` puede seguir en disco, pero **`--augmented-24m` ya no existe** (Plan 15 F1). El loader solo acepta el consolidado real. `ml_core/augmentation.py` se movió a `legacy/`. CHECK en DB: `is_synthetic=false`.

Carga permitida:

```bash
python scripts/load_processed_dataset.py --consolidado
```

### Catálogo de gases (`app/shared/gas_catalog.py`)

Códigos: `CH4`, `CO`, `H2S`, `CO2`, `O2`, `NO2`, `UNKNOWN`. Alias: `LEL(CH4)`/`LEL`/`Gas combustible`/`METANO` → CH4; se limpia prefijo `Sensor SN:`; `SIN_SITIO` → “Sin sitio asignado”. Labels UI: Metano (CH₄), etc. Prioridad thesis: `thesis_priority_gases()` → CH4, CO, H2S.

El CSV canónico tiene 15 columnas (`ml_core/columns.py`). En PostgreSQL **no** se persisten `Descripción`, `Número de Periodo`, `Factor de Respuesta` ni `Factor`; sí `leyendo`, `unidad`, `stel_max`, `twa_max`, `alarma`, `temperatura`, `tiempo_inicio/fin`, `is_synthetic`, `source_file`.

### 5.4 Notebooks (investigación, no runtime)

La app **no importa** notebooks. El pipeline productivo es `ml_core` + `scripts/` + módulo `sensors_ingestion`. Los notebooks documentan el trabajo exploratorio de tesis y **generaron** los CSV processed.

| Archivo | Rol | Notas |
|---------|-----|-------|
| `notebooks/01_exploracion.ipynb` | Explora `data/raw` y conforma CSV mes a mes | Fuente original de `cargar_dls_report` (portado a `ml_core/data_io.py`) |
| `notebooks/ETL_–_Carga_y_limpieza_de_datos_.ipynb` | ETL de investigación (Colab) | Misma familia que 02/03 |
| `notebooks/02_ETL_–_Carga_y_limpieza_de_datos copy.ipynb` | Copia del ETL (~3.6 MB, outputs) | No usar como fuente de código |
| `notebooks/03_ETl_PROCESADO.ipynb` | ETL procesado (~33 MB, outputs) | Confirma 13.894 filas en 9 CSV mes-año |

`01_exploracion.ipynb` importa `from config import RAW_DIR, PROCESSED_DIR, …`. **Ese `config.py` de raíz ya no existe** (la app usa `app.core.config`). Los notebooks son legado; no hay que “arreglarlos” para correr el sistema.

---

## 6. Modelo de datos

Esquema **v2** (Plan 16–19, Alembic `b1c2d3e4f5a6` … `c1d2e3f4a5b6`). La tabla `predictions` se retiró: el pronóstico vive en `forecasts` + `forecast_quantiles`. El permiso `predictions.view` queda como alias de `status.view` / `history.view`.

### Diagrama lógico (resumen)

```
ACCESO
users ─┬─ user_roles ── roles ── role_permissions ── permissions
       ├─ user_site_scopes ── sites
       ├─ refresh_tokens
       ├─ password_reset_tokens
       ├─ user_invitations
       └─ kiosk_devices

CATÁLOGO
gas_types ── normative_thresholds
app_settings

DATOS
sites ── sensors ── gas_readings ── etl_runs ── etl_run_steps
                 │        └── data_quality_issues
                 └── reading_grid
                 └── threshold_events

MODELOS
model_registry ── model_evaluations
training_jobs

PRONÓSTICO Y AVISOS
forecasts ── forecast_quantiles
     └── forecast_explanations
     └── alerts ── alert_notifications ── stakeholders
            └── alert_outcomes                  └── stakeholder_subscriptions
                                                    └── stakeholder_user ── users

SALIDAS
reports · audit_log
```

### Tablas y campos principales

#### Identidad y RBAC

| Tabla | Campos clave | Relaciones |
|-------|--------------|------------|
| `users` | email (unique), password_hash, full_name, is_active, failed_login_count, locked_until, last_login_at, must_change_password, totp_* | M2M roles; 1:N refresh_tokens |
| `user_roles` | user_id, role_id | PK compuesta |
| `refresh_tokens` | token_hash, expires_at, revoked_at, user_agent, ip, last_used_at | N:1 user |
| `user_site_scopes` | user_id, site_id | sin filas = todos los sitios (si el rol lo permite) |
| `password_reset_tokens` | token_hash, user_id, expires_at, used_at | N:1 user |
| `user_invitations` | email, role_ids JSONB, token_hash, invited_by, expires_at, accepted_at | — |
| `kiosk_devices` | name, token_hash, site_ids JSONB, created_by, revoked_at | — |
| `roles` | name (unique), description | M2M permissions |
| `permissions` | code (unique), description | — |
| `role_permissions` | role_id, permission_id | PK compuesta |

#### Catálogo

| Tabla | Campos clave | Relaciones |
|-------|--------------|------------|
| `gas_types` | code PK, display_name, canonical_unit, lel_percent_vol, physical_max, max_rate_per_min, priority | 1:N umbrales |
| `normative_thresholds` | gas_code, level (vigilar/actuar/evacuar), direction, value, verified, valid_from | UQ (gas_code, level, valid_from) |
| `app_settings` | key PK, value JSONB | horizontes 6/12/18, grid_step 6 |

#### Sensores e ingesta

| Tabla | Campos clave | Relaciones |
|-------|--------------|------------|
| `sites` | name (unique), description | 1:N sensors |
| `sensors` | site_id, code, gas_type, unit, display_name, kind, location_note, is_active; UQ (code, gas_type) | N:1 site |
| `etl_runs` | status, rows_ingested/rejected, source_files, log, triggered_by_user_id | 1:N readings, steps |
| `etl_run_steps` | etl_run_id, step E1–E6, rows_in/out/rejected, duration_ms, details | N:1 etl_run |
| `gas_readings` | sensor_id, leyendo, value_canonical, unit_canonical, quality_status, tiempo_inicio; UQ (sensor_id, tiempo_inicio); CHECK is_synthetic=false | N:1 sensor, etl_run |
| `data_quality_issues` | gas_reading_id?, sensor_id, etl_run_id, code, severity, details | linaje |
| `reading_grid` | PK (sensor_id, ts), value, is_imputed, is_missing | entrada de modelos |
| `threshold_events` | sensor_id, gas_code, level, started_at, ended_at, peak_value | verdad de referencia |

#### ML y pronóstico

| Tabla | Campos clave | Relaciones |
|-------|--------------|------------|
| `model_registry` | name, version, algorithm, family, problem_spec/calibration/selection_score JSONB, status, scope | FK users |
| `model_evaluations` | model_id, fold_index, gas_code, horizon_min, forecast_metrics, event_metrics, is_final_test | N:1 registry |
| `training_jobs` | model_registry_id, status, dataset_version, params, log | FK registry, users |
| `forecasts` | sensor_id, model_id, issued_at, status_level, exceed_prob, confidence; UQ (sensor_id, model_id, issued_at) | reemplaza `predictions` |
| `forecast_quantiles` | forecast_id, horizon_min, q10, q50, q90, q95 | N:1 forecast |
| `forecast_explanations` | forecast_id, method, factors JSONB, plain_text | N:1 forecast |

#### Alertas y stakeholders

| Tabla | Campos clave | Relaciones |
|-------|--------------|------------|
| `alerts` | forecast_id, gas_reading_id, sensor_id, kind (anticipado/confirmado), level, threshold_id, expected_at, plain_message, status, resolved_by | FKs forecast, reading, sensor, user |
| `alert_outcomes` | alert_id PK, outcome, event_id, lead_minutes | ¿fue acertado? |
| `stakeholders` | name, type, organization, email, phone, notify_channels (JSONB) | 1:N subscriptions; M2M users |
| `stakeholder_user` | stakeholder_id, user_id | vínculo interesado ↔ stakeholder |
| `stakeholder_subscriptions` | stakeholder_id, site_id?, sensor_id?, min_level | filtros de notificación |
| `alert_notifications` | alert_id, stakeholder_id, channel, status, sent_at, error | trazabilidad de envío |

Vista `missed_events_v`: episodios en `threshold_events` sin aviso previo acertado.

#### Reportes y auditoría

| Tabla | Campos clave | Relaciones |
|-------|--------------|------------|
| `reports` | type, period_start/end, file_path, generated_by | FK users |
| `audit_log` | user_id, action, resource_type/id, metadata (JSONB), details | FK users |

---

## 7. Roles, permisos y aterrizaje UI

### Permisos (`scripts/seed_roles_permissions.py`, Plan 19)

Canónicos: `status.view`, `alerts.view`, `alerts.acknowledge`, `alerts.resolve`, `history.view`, `reliability.view`, `reports.export`, `thresholds.manage`, `stakeholders.manage`, `data.upload`, `data.quality.view`, `models.train`, `models.promote`, `users.manage`, `roles.manage`, `kiosk.manage`, `audit.view`.

Alias de compatibilidad (siguen existiendo en DB): `predictions.view`, `sensors.manage`, `dashboard.view_all_sites`.

### Roles (v2)

| Rol visible | Código | Permisos (resumen) | Home UI |
|-------------|--------|-------------------|---------|
| Administrador | `admin` | todos | Hoy `/` |
| Supervisor de seguridad | `supervisor_seguridad` | ver, avisos, límites, contactos, informes, kiosco | Hoy `/` |
| Operador de sala | `operador` | estado/avisos/historial de **sus zonas**; Ya lo vi / cerrar | Hoy `/` |
| Gerencia | `gerencia` | resumen, confiabilidad, informes (lectura) | `/resumen` |
| Analista de datos | `analista` | cargar datos, calidad, laboratorio, promover | `/?view=ingeniero` |
| Auditor | `auditor` | lectura + calidad + bitácora | `/bitacora` |

Migración: `ingeniero_datos` → `analista`, `operador_mina` → `operador`, `interesado` → `gerencia`. Script `scripts/migrate_roles_v2.py`. Un operador **sin zonas** no ve nada. Quien entrena no aprueba umbrales, salvo admin.

Superadmin: `scripts/create_superadmin.py` + `SUPERADMIN_EMAIL` / `SUPERADMIN_PASSWORD` / `SUPERADMIN_FULL_NAME` (opcional, default `Super Admin`). El script **actualiza** el usuario si el email ya existe.

### Credenciales locales

**No hay usuarios semilla fijos embebidos en la imagen.** Se crean con scripts o fixtures.

| Origen | Email | Password | Rol | Cuándo existe |
|--------|-------|----------|-----|----------------|
| Superadmin (`.env` + script) | el de `SUPERADMIN_EMAIL` | `SUPERADMIN_PASSWORD` | `admin` | Tras `python scripts/create_superadmin.py` |
| Pruebas / DEV habitual | `test.admin@example.com` | `AdminPass123!` | `admin` | Fixture pytest; **también en DEV** si se sembró a mano (Compose actual) |
| Fixture operador | `test.operador@example.com` | `OperadorPass123!` | `operador` | Solo test DB salvo que exista en DEV |

Login UI: `http://localhost:8000/ingresar` (`/login` → 301).  
- **Nativo (sin JS):** `POST /ingresar` (form + `csrf_token`) → cookies + 303 a `/` o `/mi-cuenta`.  
- **JSON:** `POST /auth/login` (con cabecera CSRF).  
`GET /ingresar?email=&password=` → 302 a `/ingresar` limpio (nunca reutiliza la clave en Location).  
`DELETE /api/users/{id}` es **baja lógica** (`is_active=false`).

La navegación del sidebar se arma por **permisos**, no por rol hardcodeado. El **aterrizaje** (`home_path_for_user` / `GET /`) sí usa roles (gerencia pura → `/resumen`; analista puro → panel; auditor puro → `/bitacora`).

---

## 8. Flujos de negocio

### 8.1 Autenticación

1. UI `/ingresar` (layout Vigía a dos columnas). Envío nativo `POST /ingresar` (form) **o** mejora progresiva JSON `POST /auth/login`. CSRF double-submit: cookie `csrf_token` + campo/cabecera; middleware ASGI en `app/core/csrf.py` (no consume el body del POST).
2. Access JWT 15 min en cookie **`access_token`**. Refresh opaco 8 h en **`refresh_token`**, con rotación y detección de reutilización (revoca todas las sesiones).
3. Cookies: `HttpOnly` (sesión), `SameSite=lax`, `path=/`. `Secure` si `ENVIRONMENT=prod`. CSP **`default-src 'self'`** (sin CDN). Páginas auth: `Referrer-Policy: no-referrer`, `Cache-Control: no-store`.
4. Scripts de página en `app/static/js/` y `app/static/js/pages/` (CSP bloquea inline).
5. 5 fallos → bloqueo 15 min (mensaje genérico). Rate limit por IP y correo. Contraseña NIST: 12+, lista de comunes, no nombre/correo.
6. Invitación 72 h, recuperación 30 min, cambio forzado, TOTP + códigos de respaldo. Sin SMTP: `storage/outbox/`.
7. Kiosco: `/sala?kiosk=` con token hasheado. Equipo `/equipo`, pantallas `/pantallas`, cuenta `/mi-cuenta`.
8. HTML sin sesión → `/ingresar`; sin permiso → 403. Auditoría: `auth.login_ok`, `auth.locked`, `user.invited`, `kiosk.created`, …

### 8.2 Ingesta ETL

1. **Upload:** `POST /api/ingestion/upload` (Excel `dls_report`) → limpieza `ml_core.data_io` → persistencia.
2. **Inbox:** `data/inbox` (.xlsx/.xls); APScheduler si `ETL_INBOX_ENABLED=true`.
3. **Scripts:** `scripts/load_processed_dataset.py`, `scripts/run_etl_inbox.py`.
4. Por fila: get_or_create `Site`/`Sensor` con **nombres canónicos** (`gas_catalog`) → `GasReading` → `EtlRun`.
5. Tras ETL exitoso: ciclo de pronóstico (`app/modules/forecasting/cycle.py`); un fallo de ML no aborta el ETL.
6. Éxito inbox → `inbox/processed`; error → `inbox/failed`.
7. Backfill opcional: `scripts/normalize_sensors_display.py`.
8. El historial de sesiones MX6 y los `alarmReport_*` **no** se ingieren.

### 8.3 Modelos de IA — qué son y qué NO son

El sistema **no usa LLMs** para explicar avisos. El zoo **vigente (Plan 17)** está en `ml_core/forecasting/adapters/`: persistencia, ETS, LightGBM cuantílico, LSTM, TFT, PatchTST, iTransformer, Chronos-2, TimesFM y TTM. Horizontes **6 / 12 / 18 min** (G0). Inferencia: `ml_core/forecasting/serve.py` + `app/modules/forecasting/cycle.py`, persistida en `forecasts` / `forecast_quantiles`.

El zoo tabular histórico (sklearn/XGBoost, Plan 12) sigue en `ml_core/models/` y MLflow `plataforma-gases-training`; **ya no** hay módulo `app/modules/predictions`.

#### 8.3.1 Catálogo (10 algoritmos)

| Clave | Familia | Label | Arquitectura | Framework | Tareas | Métricas aplicables |
|-------|---------|-------|--------------|-----------|--------|---------------------|
| `logistic_regression` | tabular | Regresión logística | Lineal (baseline) | sklearn | solo classification | recall, precision, F1, FN |
| `decision_tree` | tabular | Árboles de decisión | Árbol max_depth=12 | sklearn | solo classification | recall, precision, F1, FN |
| `random_forest` | tabular | Random Forest | 150 árboles | sklearn | classification, regression, both | + RMSE |
| `xgboost` | tabular | XGBoost | Gradient boosting (150, depth 6, lr 0.1) | xgboost | classification, regression, both | + RMSE |
| `svm` | tabular | SVM | RBF + `probability=True` | sklearn | solo classification | recall, precision, F1, FN |
| `mlp` | tabular | MLP sklearn | Capas (64, 32), 150 iter | sklearn | classification, regression, both | + RMSE |
| `lstm` | sequence | LSTM | RNN last hidden + cabezas | torch | classification, regression, both | + RMSE + **lead** |
| `gru` | sequence | GRU | RNN gated + cabezas | torch | classification, regression, both | + RMSE + **lead** |
| `transformer` | sequence | Transformer | Encoder atención (`hidden=64`, 4 heads, 2 layers) — **no** es BERT/GPT | torch | classification, regression, both | + RMSE + **lead** |
| `cnn1d` | sequence | CNN 1D | Conv1d + AdaptiveAvgPool + cabezas | torch | classification, regression, both | + RMSE + **lead** |

Listas de conveniencia:

- `DEFAULT_TABULAR` = los 6 tabulares (default si `POST /api/ml/train` no manda `algorithms`).
- `DEFAULT_SEQUENCE` = lstm, gru, transformer, cnn1d.
- `DEFAULT_ALL` = 10. Se usa con `algorithms=["all"]` o `scripts/train_full_model_zoo.py`.

**Desbalance:** tabulares sklearn usan `class_weight="balanced"`; XGBoost `scale_pos_weight = neg/pos`; DL usa `BCEWithLogitsLoss(pos_weight=neg/pos)`.

**DL `SequenceMultiHead`:** encoder (LSTM/GRU/Transformer/CNN) → vector; cabeza `cls_head` (logits binarios) y/o `reg_head` (concentración). Entrada `[B, T, F]` con `T=lookback_steps` (default 20) y `F=5` features.

#### 8.3.2 Features, labels y split (el “data engine”)

Todo sale de PostgreSQL (`load_readings_df`), no del CSV directo.

**Features 2D** (`ml_core/features/build_features.py`), por sensor, ventana rolling 20:

| Feature | Cómo se calcula |
|---------|-----------------|
| `Leyendo` | concentración cruda |
| `Media_Movil` | media móvil 20 lecturas (`min_periods=1`) |
| `Cambio` | \|diff\| de `Leyendo` |
| `Cambio_Brusco` | 1 si `Cambio` > media + 2σ del sensor |
| `Temperatura` | numérica |

**Label `evento_final` (clasificación):** 1 si ocurre **cualquiera**: alarma no vacía, `Leyendo > STEL Máx`, o `Leyendo > percentil 95 del mismo sensor`.

**Targets futuros** (`ml_core/features/targets.py`), por sensor, según la mediana del intervalo entre lecturas:

| Target | Significado | Default |
|--------|-------------|---------|
| `y_reg` | `Leyendo` en t + horizonte | horizonte **7.5 min** |
| `y_alert_lead` | 1 si hay `evento_final` en [t+5 min, t+10 min] | lead 5–10 |

**Split temporal:** últimos `test_months=3` al test; si un lado queda vacío (datos irregulares), fallback **80/20 temporal**. No es split aleatorio.

**Secuencias 3D** (`ml_core/features/sequences.py`): ventanas `[N, T, 5]` por sensor. Mínimo para entrenar DL: **≥10** ventanas train y **≥5** test.

#### 8.3.3 Cómo se entrena dentro del sistema

```
UI /ml/train  o  POST /api/ml/train  o  scripts/train_*.py
        ↓ permiso models.train
ml_training.service.start_training
        ↓ crea training_jobs (pending → success/failed)
ml_core.models.train_model.train
        ├── tabulares → train_tabular.py (sklearn/XGB) + MLflow sklearn/xgboost
        └── secuencias → train_sequence.py (PyTorch CPU) + artifact model.pt
        ↓ cada algoritmo → fila model_registry status=staging
        ↓ best_result() elige el mejor (no lo promueve solo)
```

`POST /api/ml/train` body (`TrainRequest`): `dataset_version`, `scope` (default `global`), `task` (`classification` \| `regression` \| `both`), `algorithms[]`, `lookback_steps`, `horizon_minutes`, `params` extra (`max_rows`, `test_months`, `epochs` default 12 en DL).

Comportamiento:

- Sin `algorithms` → solo tabulares.
- `algorithms: "all"` o `["all"]` → zoo completo.
- Task default del API: **classification**.
- Entrenamiento es **síncrono** (bloquea el request). Experimento MLflow: `plataforma-gases-training`.
- Tras el job: **todos** los modelos quedan `staging`. El `best_model_id` se anota en el job; **producción requiere promote explícito** (la UI o los scripts de retrain sí pueden promover).

**Elección del “mejor”** (`best_result`): orden lexicográfico

1. `gates.meets_thesis` (1 gana a 0)
2. F1 más alto
3. Recall más alto
4. RMSE más bajo (si no hay RMSE, se penaliza)

**Artefactos**

- Tabular: `mlflow.sklearn` o `mlflow.xgboost` en `artifact_uri/.../model`.
- Sequence: `model.pt` con `state_dict`, `norm_mean/std` (features), `reg_mean/std` (target), `cls_threshold`, `lookback_steps`, `task`. Threshold DL: `min(0.5, max(0.15, pos/(pos+neg)))`.

**Scripts**

| Script | Qué hace |
|--------|----------|
| `train_full_model_zoo.py` | `DEFAULT_ALL`, task `both`, lookback 20; **promueve** el mejor |
| `retrain_dl_and_promote.py` | solo `DEFAULT_SEQUENCE` y promote |
| `retrain_promote_dl_forecast.py` | DL orientado a forecast y promote |

Permisos: entrenar = `models.train`; promover = `models.promote`. Auditoría: `ml.train`, `ml.promote`.

#### 8.3.4 Métricas y gates thesis

Implementación: `ml_core/models/metrics.py`. Se guardan en `model_registry.metrics` (JSONB) y se muestran en `/ml/models`, `/ml/compare`, detalle y reporte `comparativa_modelos`.

**Clasificación** (test set, labels 0/1):

| Métrica | Fórmula / origen | Gate thesis | Env |
|---------|------------------|-------------|-----|
| `precision` | sklearn, `zero_division=0` | ≥ 0.90 | `THESIS_PRECISION_MIN` |
| `recall` | sklearn | ≥ 0.95 | `THESIS_RECALL_MIN` |
| `f1` | sklearn | ≥ 0.92 | `THESIS_F1_MIN` |
| `false_negative_rate` | FN / positivos reales | ≤ 0.05 | `THESIS_FN_MAX` |
| `support_pos` | conteo de y=1 en test | — | — |
| `confusion_matrix` | `{tn, fp, fn, tp}` | — | — |

**Regresión** (sobre `y_reg` finito):

| Métrica | Fórmula | Gate thesis | Env |
|---------|---------|-------------|-----|
| `rmse` | √MSE | ≤ 0.05 | `THESIS_RMSE_MAX` |
| `mae` | media \|error\| | no hay gate | — |

El RMSE ≤ 0.05 es **muy estricto** en unidades reales de gas; con el consolidado irregular a menudo **no se cumple**. Hay que documentarlo al promover. El gate solo se evalúa si el algoritmo/tarea **usa** RMSE (`applicability_for`).

**Lead time** (solo sequence, `uses_lead=True`):

| Campo | Significado |
|-------|-------------|
| `lead_time_hit_rate` | De las ventanas con evento futuro (`y_alert_lead=1`), fracción donde el modelo predijo 1 |
| `lead_time_minutes_mean` | **Proxy:** punto medio de la ventana (7.5) si hubo al menos un hit; no es lead medido muestra a muestra |
| `lead_window_min` / `_max` | 5 y 10 (env `ML_LEAD_MINUTES_*`) |

Gate `meets_lead`: hit_rate ≥ **0.50** y el mean (si existe) cae en [5, 10].

**Flags `metrics.gates`:** `meets_recall`, `meets_precision`, `meets_f1`, `meets_fn`, `meets_rmse`, `meets_lead`. Cada uno es `true`/`false` o `null` si no aplica a ese algoritmo/tarea. `meets_thesis` = **AND** de los gates evaluados (no nulos). También se persiste `metrics.thresholds` (copia de los umbrales usados).

UI: partial `_metric_gate.html` pinta verde/rojo por gate.

#### 8.3.5 Promoción y modelo activo

Estados: `staging` → `production` → `archived`.

`POST /api/ml/models/{id}/promote` (`models.promote`):

1. Lee `task` de `params` del modelo (default classification).
2. Archiva todo `production` del mismo `scope` y `task`.
3. Deja este en `production`.

**Selección en inferencia** (`get_production_model`, scope `global`):

1. Entre production del scope, **prioriza family=sequence** (o algoritmo lstm/gru/transformer/cnn1d).
2. Dentro de sequence, prefiere task `both`, luego `regression`, si no el primero.
3. Si no hay sequence, elige por `task` pedido o el production más reciente.

Puede haber más de un `production` si tienen **tasks distintas**. El runtime **ignora** un tabular production si existe un DL production: el forecast de Hoy depende de eso.

---

### 8.4 Inferencia, semáforo y forecast (producción)

**Vigente (Plan 17):** `ml_core/forecasting/serve.py` + `app/modules/forecasting/cycle.py` escriben `forecasts` / `forecast_quantiles` (horizontes G0: 6/12/18 min). Semáforo y avisos en Hoy vía `dashboard`. API: `/api/forecasts`. Gráficos con `charts.js` (SVG) / ECharts local — **sin Chart.js ni CDN**.

Ciclo actual (resumen):

```
gas_readings (reales)
        ↓
forecasting/cycle → forecasts + forecast_quantiles
        ↓
reglas de avisos (umbrales / probabilidad de excedencia)
        ↓
UI Hoy `/` · Avisos `/avisos` · Resumen `/resumen` · Confiabilidad
```

**Triggers** (vars `PREDICTION_*` siguen vigentes en env):

| Trigger | Condición | Límite |
|---------|-----------|--------|
| Post-ETL | Tras ingesta exitosa | `PREDICTION_POST_ETL_LIMIT` (default 500; 0 = todas). Solo `is_synthetic=false` |
| Job APScheduler | `PREDICTION_JOB_ENABLED=true` | intervalo `PREDICTION_JOB_INTERVAL_SECONDS` (120) |
| Serve on-demand | `ml_core/forecasting/serve` | persiste cuantiles; UI lee `forecasts` |

Si no hay modelo production, el ETL **no falla** (stats `skipped=1`).

**Camino sequence / transformers (producción actual)**

1. Ventana lookback → tensor; normalización del artefacto.
2. Salida multihorizonte + cuantiles (conformal cuando aplica).
3. Decisión operativa: Normal / Vigilar / Actuar ya / Evacuar según umbrales del catálogo.
4. Persistencia en `forecasts` / `forecast_quantiles` (no en la tabla retirada `predictions`).

**Camino tabular legado (sklearn/XGB, zoo / laboratorio)**

Sigue en `ml_core/models/` y MLflow para entrenamiento y comparación. Inferencia home ya no escribe `predictions`. Detalle de features/métricas: §8.3.

**Riesgo / estados operativos** (umbrales de probabilidad o excedencia; nombres UI en `copy.py`):

| Estado UI | Idea | Env (legado probabilidad) |
|-----------|------|---------------------------|
| Normal | bajo riesgo | — |
| Vigilar | atención | `RISK_THRESHOLD_PRECAUTION` (~0.3) |
| Actuar ya | alto | `RISK_THRESHOLD_ALERT` (~0.6) |
| Evacuar | crítico | `RISK_THRESHOLD_CRITICAL` (~0.85) |

**Avisos** (`alerts/rules.py`): se crean ante riesgo alto/crítico o hard-alarm (alarma / STEL / TWA). Recomendación textual por gas.

**Superficies que leen el modelo / sus salidas**

| Superficie | Qué muestra |
|------------|-------------|
| `/` Hoy | Franja de estado, zonas, avisos, proyección |
| `/avisos` | Avisos derivados de forecast + reglas |
| `/resumen` | KPIs gerencia |
| `/confiabilidad` | Lenguaje natural sobre el modelo |
| `/laboratorio/modelos` | Matriz zoo + gates thesis |
| `/laboratorio/entrenar` | Selector algoritmos / task / lookback / horizonte |
| `/laboratorio/comparar` | Comparativa |
| `/informes` | PDF/Excel (`desempeno_modelo`, …) |
| MLflow `:5000` | Runs y artefactos |
| `/api/forecasts` | JSON de pronósticos |

### 8.5 Alertas

- Se crean si riesgo ∈ {ALERTA, CRITICO} o hard-alarm (alarma / STEL / TWA).
- Estados: `abierta` → reconocer → resolver (API + UI).
- Recomendaciones por gas en `alerts/recommendations.py`.
- Al crear → `dispatch_alert_notifications`.

### 8.6 Stakeholders / notificaciones

- CRUD stakeholders + suscripciones (site/sensor, `min_level`).
- `StakeholderUser` filtra vistas de interesado.
- Canales: `email` (SMTP si no dry-run), `whatsapp` (stub).
- `NOTIFICATIONS_DRY_RUN=true` por defecto (solo log).

### 8.7 Reportes

Tipos: `alertas_periodo`, `desempeno_modelo`, `resumen_ejecutivo`, `comparativa_modelos`.

- Generación PDF/Excel → archivo en `REPORTS_DIR` + fila en `reports`.
- API: `POST /api/reports/alertas|ejecutivo|modelo/{id}|comparativa`; `GET /api/reports/{id}/download`.
- Interesado: restringido a alertas/suscripciones visibles.
- Auditoría: `report.generate`.

---

## 9. Rutas HTTP (mapa)

### Auth

| Método | Ruta | Notas |
|--------|------|-------|
| GET | `/ingresar` | HTML login Vigía; strip `?email`/`?password` → 302 limpio |
| POST | `/ingresar` | Form autenticado → 303 `/` o `/mi-cuenta` |
| GET | `/login` | 301 → `/ingresar` |
| POST | `/auth/login` | JSON + CSRF → cookies |
| POST | `/auth/refresh` | rota refresh |
| POST | `/auth/logout` | revoca |
| GET | `/auth/me` | usuario actual |
| POST | `/auth/recuperar`, `/auth/recuperar/confirmar`, `/auth/invitar` | reset / invitación |
| * | `/auth/totp/*`, `/auth/sesiones*` | TOTP y sesiones (Mi cuenta) |

### UI HTML en español (`dashboard/ui_router`)

Las rutas inglesas (`/alerts`, `/sites`, `/ml/models`, `/login`, …) hacen **301** a las españolas.

| Ruta | Permiso típico | Notas |
|------|----------------|-------|
| `/` | autenticado | **Hoy** (`dashboard/hoy.html`) |
| `/fragmentos/hoy` | autenticado | Fragmento htmx |
| `/avisos`, `/avisos/{id}` | `alerts.view` | Lista / detalle |
| `/zonas`, `/zonas/{id}`, `/sensores/{id}` | status/history | Sitios y sensores |
| `/historial` | history | Series / pasado |
| `/informes` | `reports.export` | Generar PDF/Excel |
| `/confiabilidad` | reliability/audit | Frases “de cada 10” |
| `/resumen` | gerencia | Panel ejecutivo |
| `/datos/cargar`, `/datos/calidad` | data.* | Ingesta y calidad |
| `/ajustes/limites` | `thresholds.manage` | Umbrales |
| `/laboratorio`, `/laboratorio/*` | `models.train` | Área técnica |
| `/equipo`, `/roles` | users/roles.manage | Personas y roles |
| `/contactos` | `stakeholders.manage` | Interesados |
| `/bitacora` | `audit.view` | Auditoría |
| `/mi-cuenta`, `POST …/contrasena` | autenticado | Perfil |
| `/pantallas`, `/sala` | kiosk | Dispositivos y sala |
| `/_componentes` | solo `ENVIRONMENT=local` | Catálogo de macros |
| `/403` | — | Sin acceso |

### Dashboard API (polling)

Prefijo `/dashboard/api`: `semaforo`, `forecast-by-gas`, `series/{sensor_id}`, `alertas-activas`, `sites`, `executive`, `ingeniero`.

### APIs REST (detalle)

| Método | Ruta | Permiso |
|--------|------|---------|
| GET/POST | `/api/users` | `users.manage` |
| GET/PATCH | `/api/users/{id}` | `users.manage` |
| DELETE | `/api/users/{id}` | baja lógica (`is_active=false`) |
| POST | `/api/users/{id}/roles` | asignar roles |
| GET/POST | `/api/roles` | `roles.manage` (POST crea) |
| PATCH | `/api/roles/{id}` | `roles.manage` |
| GET | `/api/permissions` | `roles.manage` |
| POST | `/api/ingestion/upload` | `sensors.manage` (Excel dls_report) |
| GET | `/api/ingestion/runs`, `/api/ingestion/runs/{id}` | `sensors.manage` |
| POST | `/api/ml/train` | `models.train` (síncrono) |
| GET | `/api/ml/catalog`, `/jobs`, `/models`, `/models/compare` | `models.train` |
| POST | `/api/ml/models/{id}/promote` | `models.promote` |
| GET | `/api/forecasts`, … | status/history (reemplaza `/api/predictions`) |
| GET | `/api/alerts`, `/api/alerts/{id}` | `alerts.view` |
| POST | `/api/alerts/{id}/acknowledge`, `/resolve` | `alerts.resolve` (UI detalle llama estas) |
| GET/POST | `/api/stakeholders` | `stakeholders.manage` |
| GET/PATCH/DELETE | `/api/stakeholders/{id}` | |
| GET/POST | `/api/stakeholders/{id}/subscriptions` | |
| DELETE | `/api/subscriptions/{id}` | |
| GET | `/api/audit` | `audit.view` |
| GET | `/api/reports` | `reports.export` |
| POST | `/api/reports/alertas`, `/ejecutivo`, `/modelo/{id}`, `/comparativa` | |
| GET | `/api/reports/{id}/download` | |

Otros: `GET /health` (sin auth), `GET /_demo/not-found` (demo del handler, Plan 01), estáticos en `/static`. OpenAPI: `/docs`.

---

## 10. UX / UI — Vigía

Fuente de verdad visual: [`21_SISTEMA_DE_DISENO_VIGIA.md`](21_SISTEMA_DE_DISENO_VIGIA.md), mockups en `mockups/vigia-design-kit/`, tokens en `app/static/css/tokens.css`. Reglas Cursor: `.cursor/rules/vigia-*.mdc`.

### Identidad

| Elemento | Valor |
|----------|--------|
| Marca | **Vigía** · «Gases en la mina» |
| Fondo | Polvo de roca `#EEF0EF` |
| Texto | Antracita `#1A1E24` |
| Acción | Aire fresco `#1C5A8E` (nunca verde/ámbar/rojo de estado en botones) |
| Tipografía UI | **Archivo** (local, `font-stretch` 88 % en títulos) |
| Tipografía técnica | **IBM Plex Mono** solo Laboratorio / Calidad |
| Estados | Normal / Vigilar / Actuar ya / Evacuar / Sin datos — color + ícono sprite + palabra |
| Sala | `data-theme="sala"`, escala ×1,35 |
| Recursos | Fuentes, `sprite.svg`, ECharts, htmx en `app/static/` — **sin CDN** |
| Ilustraciones | `login-hero.svg`, `vacio-despejado.svg`, `sensor-sin-datos.svg`, `error-galeria.svg`, isotipo |

### Cascarón

- Riel antracita 232 px (grupos Operación / Seguimiento / Datos / Administración), isotipo + franja de estratos.
- Topbar 56 px: mina · datos al día · avisos / salir.
- Contenido máx. 1360 px. Bajo 900 px: barra inferior de 4 ítems.
- Macros: `templates/components/macros.html`. Gráficos solo `app/static/js/charts.js` (renderer SVG).
- Textos operativos: `app/shared/copy.py`. Laboratorio = única zona con jerga técnica.

### Inventario de pantallas (Plan 18 + Vigía)

| # | Pantalla | Ruta | Notas |
|---|----------|------|-------|
| P1 | Ingresar | `/ingresar` | Dos columnas + `login-hero.svg` |
| P2 | Hoy | `/` | Franja de estado + zonas + avisos; *corte de mina pendiente de datos* |
| P3 | Avisos | `/avisos` | Pestañas + filtros |
| P4 | Detalle aviso | `/avisos/{id}` | Lecturas, por qué, qué hacer |
| P5 | Zonas / sensores | `/zonas`, `/sensores/{id}` | |
| P6 | Historial | `/historial` | |
| P7 | Informes | `/informes` | |
| P8 | Confiabilidad | `/confiabilidad` | Lenguaje natural |
| P9 | Resumen | `/resumen` | Gerencia |
| P10 | Equipo | `/equipo` | |
| P11 | Cargar datos / calidad | `/datos/*` | |
| P12 | Límites | `/ajustes/limites` | |
| P13–15 | Laboratorio | `/laboratorio/*` | Banner «Área técnica» |
| P16 | Contactos | `/contactos` | |
| P17 | Bitácora | `/bitacora` | |
| P18 | Sala | `/sala` | Oscuro / kiosco |
| P19 | Mi cuenta / pantallas | `/mi-cuenta`, `/pantallas` | |

### Riel (agrupado)

```
[Isotipo] Vigía — Gases en la mina
Operación:     Hoy · Avisos · Zonas · Historial
Seguimiento:   Informes · Confiabilidad · Resumen
Datos:         Cargar · Calidad · Ajustes · Laboratorio (Técnico)
Administración: Equipo · Pantallas · Contactos · Bitácora
[Pie] avatar + Mi cuenta
```

Ítems filtrados por permisos (`dashboard/nav` / plantilla `base.html`).

### Pendiente de UI (kit aún no cableado del todo)

- Corte esquemático de la mina en Hoy (`sites.map_x` / `map_y` + `mine-map.js`).
- Revisión humana captura a captura vs `mockups/.../screenshots/`.
- Co-diseño con operadores (`docs/ux/codiseno.md`).

---

## 11. Variables de entorno

Ver `.env.example`. Resumen:

| Variable | Uso |
|----------|-----|
| `DATABASE_URL`, `DB_PASSWORD` | PostgreSQL (host local: puerto **5433**) |
| `JWT_*`, `ACCESS_TOKEN_*`, `REFRESH_TOKEN_*` | Auth |
| `ENVIRONMENT` | `local` / `prod` |
| `MLFLOW_TRACKING_URI` | Tracking ML |
| `ETL_INBOX_*` | Scheduler inbox |
| `RISK_THRESHOLD_*` | Umbrales de riesgo |
| `PREDICTION_*` | Inferencia post-ETL / job |
| `ML_LOOKBACK_STEPS`, `ML_LEAD_MINUTES_MIN/MAX` | Series / lead time |
| `THESIS_RECALL_MIN`, `THESIS_PRECISION_MIN`, `THESIS_F1_MIN`, `THESIS_FN_MAX`, `THESIS_RMSE_MAX` | Gates thesis |
| `NOTIFICATIONS_DRY_RUN`, `SMTP_*`, `WHATSAPP_*` | Notificaciones |
| `REPORTS_DIR` | Salida reportes |
| `GCS_BUCKET` | Reservado Plan 09 (opcional) |
| `SUPERADMIN_EMAIL`, `SUPERADMIN_PASSWORD`, `SUPERADMIN_FULL_NAME` | Solo script `create_superadmin.py` |

Nunca versionar secretos reales en `.env` ni en este documento.

---

## 12. Arranque local

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env

docker compose up -d db          # opcional: up -d --build (app+mlflow)
alembic upgrade head
python scripts/check_db.py
python scripts/seed_roles_permissions.py
# SUPERADMIN_* en .env →
python scripts/create_superadmin.py

# Datos (opcional, si la DB está vacía):
python scripts/load_processed_dataset.py --consolidado

docker compose up -d --build   # o uvicorn app.main:app --reload en el host
# http://localhost:8000/health · /ingresar · /docs
# Tras cambiar Python montado: docker compose restart app (Gunicorn no recarga)
```

| Servicio Compose | Puerto host |
|------------------|-------------|
| App | 8000 |
| Postgres | 5433 |
| MLflow | 5000 |

### Scripts útiles

| Script | Uso |
|--------|-----|
| `seed_roles_permissions.py` / `migrate_roles_v2.py` | Permisos y roles Plan 19 |
| `seed_catalog.py` | Gases, umbrales, ajustes G0 |
| `create_superadmin.py` | Usuario admin inicial |
| `check_db.py` | Sanity check de conexión |
| `load_processed_dataset.py --consolidado` | Solo datos reales |
| `purge_synthetic.py` | Purga sintéticos (con `--confirm`) |
| `verify.py` | Verificador Plan 20 (`--plan`, `--fast`, `--full`) |
| `diagnose_real_data.py` | Diagnóstico G0 |
| `run_etl_inbox.py` | Una pasada del inbox |

Tests: `python scripts/verify.py` o `pytest` contra `proyecto_gases_test` (§15).

Login local típico en Compose DEV: `test.admin@example.com` / `AdminPass123!` (§7).

---

## 13. Reglas de trabajo (para agentes y humanos)

1. **No saltar compuertas del paquete 14–22** (G0 en Plan 15). Planes 09/10 al edge-first; no reabrir 04/05/12/13 salvo para retirarlos.
2. **Migraciones solo con Alembic.**
3. **Módulos nuevos** siguen `models/schemas/repository/service/router`.
4. **UI Vigía:** solo variables de `tokens.css`; sin CDN; sin Bootstrap/Chart.js/Inter; color de estado solo para gases. Reglas `.cursor/rules/vigia-*.mdc`.
5. **Secretos** solo por env / Secret Manager.
6. **Este archivo** se actualiza cuando cambie arquitectura, datos, modelo, rutas, tests o UX de forma material.
7. Planes `01`–`13` son bitácora histórica; ante conflicto, **priorizar el código** y este contexto.
8. **Notebooks** no son runtime.

---

## 14. Pendiente conocido

- **Humano (no se inventa):** visto del director en `docs/g0_visto_director.md`; 3–5 sesiones SUS en mina (`docs/ux/aceptacion.md`).
- **UI Vigía restante:** corte esquemático de la mina en Hoy (`map_x`/`map_y`); alinear capturas con `screenshots/`; co-diseño operadores.
- **Plan 09:** Cloud Run / Cloud SQL / GCS — reencuadrar edge-first. CI verify ya existe.
- **Plan 10 (resto):** k6, pip-audit, HSTS de producción, backups Cloud SQL. Login/CSP/CSRF ya operativos.
- WhatsApp stub; sin parser de `alarmReport_*` ni historial MX6.
- RMSE thesis ≤ 0.05 puede no cumplirse con el consolidado irregular.
- Legado inocuo: `templates/home.html`, `data/curated/`, fotos antiguas en `static/img/region/` (sustituidas por SVG Vigía en pantallas activas).

---

## 15. Tests, migraciones y artefactos legado

### 15.1 Suite pytest

`tests/conftest.py` apunta a `TEST_DATABASE_URL` (`proyecto_gases_test`) y **aborta** si coincide con `DATABASE_URL`. Al iniciar la sesión: `alembic upgrade head` + semillas. Cada prueba corre en transacción con SAVEPOINT y rollback. Fábricas: `tests/factories.py`. Comando: `python scripts/verify.py` (`--plan NN`, `--fast`, `--full`). CI: `.github/workflows/verify.yml`.

| Archivo | Qué cubre |
|---------|-----------|
| `tests/unit/test_security.py` | JWT / hash |
| `tests/unit/test_build_features.py` | Features 2D |
| `tests/unit/test_ml_core_data_io.py` | Parser dls_report |
| `tests/unit/test_model_zoo_metrics.py` | Gates thesis |
| `tests/unit/test_risk_and_recommendations.py` | Riesgo + textos de alerta |
| `tests/integration/test_auth_flow.py` | login / me / refresh / logout |
| `tests/integration/test_rbac.py` | Permisos |
| `tests/integration/test_ingestion.py` | Upload ETL |
| `tests/integration/test_ml_training.py` | Train/promote (permisos) |
| `tests/integration/test_alerts.py` | Alertas |
| `tests/integration/test_stakeholders.py` | Stakeholders |
| `tests/integration/test_reports.py` | Reportes |
| `tests/integration/test_dashboard_ui.py` | HTML por rol |
| `tests/integration/test_ux_plan18.py` | Lenguaje natural y pantallas Plan 18 |
| `tests/integration/test_access_plan19.py` | CSRF, TOTP, kiosco, alcance por zona |
| `tests/guards/` | Causalidad, sintéticos, walk-forward, conformal |
| `tests/ui/test_plain_language.py` | Términos prohibidos en HTML operativo |
| `tests/e2e/` | Ingreso, a11y, captura visual |
| `tests/perf/` | Persistencia < 1 s y p95 de `/` |

Comando: `python scripts/verify.py` (`--plan NN`, `--fast`, `--full`). `pytest` directo también apunta a la DB de pruebas.

### 15.2 Cadena Alembic (head actual)

```
0001_init
  → f2b543b2597b  auth_users_roles
  → 3d0bc22f046c  sensors_etl
  → 3984deaeebee  ml_training
  → 33a39369ffe4  predictions_alerts
  → c2be2667ab48  stakeholders_notifications
  → 51e28c39eed2  reports_table
  → a1b2c3d4e5f6  prediction_forecast_fields
  → b1c2d3e4f5a6  catalog_gas_types_thresholds_settings
  → b2c3d4e5f6a7  readings_quality_lineage
  → b3c4d5e6f7a8  readings_no_synthetic_check
  → b4c5d6e7f8a9  reading_grid_and_events
  → b5c6d7e8f9a0  models_evaluations
  → b6c7d8e9f0a1  forecasts_explanations
  → b7c8d9e0f1a2  alerts_v2_outcomes
  → b8c9d0e1f2a3  access_v2
  → b9d0e1f2a3b4  drop_predictions
  → c1d2e3f4a5b6  access_v3          ← HEAD
```

`0001_init` no crea tablas (esqueleto Plan 01).

### 15.3 Docker

| Artefacto | Uso |
|-----------|-----|
| `docker/Dockerfile.app` | Python 3.11-slim + torch CPU + Gunicorn `app.main:app` |
| `docker/Dockerfile.mlflow` | `mlflow server` sqlite + `/mlartifacts` |
| `docker/Dockerfile.worker` | Placeholder (`print(...)`); **no** está en Compose |
| Compose `app` volumes | `./app`, `./ml_core`, `./mlruns`, `./storage/reports` — **no** `data/` |

### 15.4 Acciones de auditoría (códigos `audit_log.action`)

`login`, `logout`; `user.create` / `user.update` / `user.deactivate` / `user.roles_update`; `role.create` / `role.update`; `ingestion.upload`; `ml.train` / `ml.promote`; `alert.acknowledge` / `alert.resolve`; `report.generate` / `report.download`.

---

*Fin del contexto canónico. Planes: `planes/00`–`22`, `BITACORA_BUCLE.md`. Diseño: `mockups/vigia-design-kit/`.*
