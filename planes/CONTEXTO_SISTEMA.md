# Contexto del sistema — Plataforma de Monitoreo y Predicción de Gases

> **Documento canónico de contexto.** Úsalo como fuente única para agentes, onboarding y decisiones de implementación. Los planes numerados (`01`–`13`) son el historial de ejecución; este archivo describe el **estado real del sistema**.

| Campo | Valor |
|-------|--------|
| Nombre | Plataforma de monitoreo y predicción de gases (tesis) |
| Arquitectura | Monolito FastAPI + Jinja2 + PostgreSQL |
| Versión app | `0.1.0` |
| Runtime | Python 3.11+ |
| Actualizado | 2026-09-21 |

---

## 1. Propósito

Sistema web para:

1. **Ingestar** lecturas de sensores de gases (Excel/CSV).
2. **Entrenar y promover** modelos de ML (riesgo + forecast de concentración 5–10 min).
3. **Predecir** concentración futura y riesgo por lectura; **generar alertas** tempranas.
4. **Notificar** a partes interesadas (email / WhatsApp stub).
5. **Visualizar** proyección por tipo de gas, semáforo operativo, ejecutivo e histórico.
6. **Exportar** reportes PDF/Excel.

No es un microservicio; toda la lógica vive en un solo proceso FastAPI con módulos de dominio.

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
| 10 Seguridad / hardening | F9 | ⬜ Pendiente |
| 11 Mapeo UX/UI pantallas | Complementa F6 | ✅ |
| 12 Model Zoo / series / métricas thesis | Extiende F3–F4 | ✅ |
| 13 MVP forecast home + UX presentación | Cierra gap thesis operativo | ✅ |
| Mejora UX consola profesional | Refino visual | ✅ |

---

## 3. Stack tecnológico

| Capa | Tecnología | Notas |
|------|------------|--------|
| API / web | FastAPI, Uvicorn, Gunicorn | `app/main.py` |
| Validación | Pydantic v2, pydantic-settings | Config vía env |
| ORM / migraciones | SQLAlchemy 2, Alembic | Nunca `create_all` en entornos compartidos |
| DB | PostgreSQL 15 | Compose puerto host `5433` |
| Auth | JWT (python-jose) + bcrypt (passlib) | Cookies HttpOnly |
| Frontend | Jinja2 + Bootstrap 5 + Inter + Chart.js | Sin SPA |
| Estilos | `app/static/css/theme.css` | Tokens teal/slate |
| ETL | pandas, openpyxl | Inbox + upload API |
| Jobs | APScheduler | Inbox ETL e inferencia opcional |
| ML | scikit-learn, XGBoost, MLflow | `ml_core/` + registry en DB |
| Reportes | ReportLab (PDF), openpyxl (Excel) | `storage/reports/` |
| Tests | pytest, httpx | `tests/unit`, `tests/integration` |

Dependencias: `requirements.txt` (no hay `pyproject.toml`).

---

## 4. Arquitectura y estructura

```
plataforma-gases/
├── app/
│   ├── main.py                 # App, routers, schedulers, /health
│   ├── core/                   # config, database, security, logging
│   ├── shared/                 # dependencies, exceptions, pagination, gas_catalog, formatting
│   ├── modules/                # dominios (ver §5–§6)
│   ├── templates/              # Jinja2 por pantalla + partials
│   └── static/                 # css/, js/, img/
├── ml_core/                    # features, Model Zoo, train tabular/sequence, metrics
├── migrations/                 # Alembic versions/
├── scripts/                    # seed, superadmin, ETL, normalize_sensors, retrain DL
├── tests/
├── data/                       # raw, processed, curated, inbox/
├── storage/reports/
├── docker/                     # Dockerfile.app, Dockerfile.mlflow
├── planes/                     # este contexto + planes 00–13
├── docker-compose.yml          # db:5433, mlflow:5000, app:8000
└── .env.example
```

### Convención por módulo

Cada dominio en `app/modules/<nombre>/`:

- `models.py` — SQLAlchemy
- `schemas.py` — Pydantic
- `repository.py` — acceso a datos (si aplica)
- `service.py` — lógica de negocio
- `router.py` — HTTP API y/o HTML

### Mapa de dependencias

```
core (config, db, security)
  ├── auth / users / roles_permissions     ← requeridos por casi todo
  ├── sensors_ingestion
  │     └── ml_training
  │           └── predictions
  │                 └── alerts
  │                       └── stakeholders (notificaciones)
  ├── dashboard     (consume todo; UI + APIs de polling)
  ├── reports       (alerts, ML, visibilidad stakeholders)
  └── audit         (transversal)
```

---

## 5. Modelo de datos

### Diagrama lógico (resumen)

```
users ──┬── user_roles ── roles ── role_permissions ── permissions
        └── refresh_tokens

sites ── sensors ── gas_readings ── etl_runs
                 └── predictions ── model_registry / training_jobs
                 └── alerts ── alert_notifications ── stakeholders
                                                      └── stakeholder_subscriptions
                                                      └── stakeholder_user ── users

reports ── users
audit_log ── users
```

### Tablas y campos principales

#### Identidad y RBAC

| Tabla | Campos clave | Relaciones |
|-------|--------------|------------|
| `users` | email (unique), password_hash, full_name, is_active | M2M roles; 1:N refresh_tokens |
| `user_roles` | user_id, role_id | PK compuesta |
| `refresh_tokens` | token_hash, expires_at, revoked_at | N:1 user |
| `roles` | name (unique), description | M2M permissions |
| `permissions` | code (unique), description | — |
| `role_permissions` | role_id, permission_id | PK compuesta |

#### Sensores e ingesta

| Tabla | Campos clave | Relaciones |
|-------|--------------|------------|
| `sites` | name (unique), description | 1:N sensors |
| `sensors` | site_id, code, gas_type (canónico CH4/CO/H2S/…), unit; UQ (code, gas_type) | N:1 site; 1:N gas_readings |
| `etl_runs` | status, rows_ingested/rejected, source_files (JSONB), log (JSONB), triggered_by_user_id | 1:N gas_readings |
| `gas_readings` | sensor_id, leyendo, unidad, stel_max, twa_max, alarma, temperatura, tiempo_inicio/fin, is_synthetic, source_file, etl_run_id | N:1 sensor, etl_run |

#### ML y predicciones

| Tabla | Campos clave | Relaciones |
|-------|--------------|------------|
| `model_registry` | name, version, algorithm, params/metrics (JSONB), mlflow_run_id, artifact_uri, status (`staging`/`production`/`archived`), scope, trained_by, trained_at | FK users |
| `training_jobs` | model_registry_id, status, dataset_version, params, log, triggered_by | FK registry, users |
| `predictions` | gas_reading_id, model_registry_id, probability, predicted_label, risk_level, **predicted_concentration**, **horizon_minutes** | FK readings, registry |

#### Alertas y stakeholders

| Tabla | Campos clave | Relaciones |
|-------|--------------|------------|
| `alerts` | prediction_id, gas_reading_id, sensor_id, level, message, recommendation, status (`abierta`/`reconocida`/`resuelta`), acknowledged_*, resolved_*, resolution_note | FKs prediction, reading, sensor, user |
| `stakeholders` | name, type, organization, email, phone, notify_channels (JSONB) | 1:N subscriptions; M2M users |
| `stakeholder_user` | stakeholder_id, user_id | vínculo interesado ↔ stakeholder |
| `stakeholder_subscriptions` | stakeholder_id, site_id?, sensor_id?, min_level | filtros de notificación |
| `alert_notifications` | alert_id, stakeholder_id, channel, status, sent_at, error | trazabilidad de envío |

#### Reportes y auditoría

| Tabla | Campos clave | Relaciones |
|-------|--------------|------------|
| `reports` | type, period_start/end, file_path, generated_by | FK users |
| `audit_log` | user_id, action, resource_type/id, metadata (JSONB), details | FK users |

---

## 6. Roles, permisos y aterrizaje UI

### Permisos (`scripts/seed_roles_permissions.py`)

`users.manage`, `roles.manage`, `sensors.manage`, `models.train`, `models.promote`, `predictions.view`, `alerts.view`, `alerts.resolve`, `stakeholders.manage`, `reports.export`, `dashboard.view_all_sites`, `audit.view`.

### Roles

| Rol | Permisos (resumen) | Home UI |
|-----|-------------------|---------|
| `admin` | todos | Semáforo / admin |
| `ingeniero_datos` | sensors, models train/promote, predictions, alerts view, reports | Panel ingeniero |
| `operador_mina` | alerts view/resolve, predictions.view | Semáforo `/` |
| `interesado` | alerts.view, reports.export | `/executive` |
| `auditor` | predictions, alerts, reports, dashboard.view_all_sites, audit.view | `/audit` |

Superadmin: `scripts/create_superadmin.py` + `SUPERADMIN_*` en env.

La navegación del sidebar se arma por **permisos**, no por rol hardcodeado.

---

## 7. Flujos de negocio

### 7.1 Autenticación

1. UI `/login` → `POST /auth/login` (email/password).
2. Access JWT en cookie `access_token` (claims: sub, roles, permissions).
3. Refresh opaco (hash SHA-256 en DB) en cookie `refresh_token`.
4. `get_current_user` + `require_permission(code)` en rutas protegidas.
5. `POST /auth/refresh` rota tokens; `POST /auth/logout` revoca y limpia cookies.
6. HTML sin sesión → redirect `/login`; sin permiso → `/403`.
7. Defaults: access 30 min, refresh 7 días, HS256.

### 7.2 Ingesta ETL

1. **Upload:** `POST /api/ingestion/upload` (Excel) → limpieza `ml_core.data_io` → persistencia.
2. **Inbox:** `data/inbox` (.xlsx/.xls); APScheduler si `ETL_INBOX_ENABLED=true`.
3. **Scripts:** `scripts/load_processed_dataset.py`, `scripts/run_etl_inbox.py`.
4. Por fila: get_or_create `Site`/`Sensor` con **nombres canónicos** (`gas_catalog`: alias `LEL(CH4)`→`CH4`, limpieza `Sensor SN:`, sitios `SIN_SITIO`→“Sin sitio asignado”) → `GasReading` → `EtlRun`.
5. Tras ETL exitoso: `run_predictions_for_etl_run` (fallo ML no aborta el ETL).
6. Éxito inbox → `inbox/processed`; error → `inbox/failed`.
7. Backfill opcional: `scripts/normalize_sensors_display.py`.

### 7.3 ML / entrenamiento (Model Zoo — Plan 12)

- **Tabulares:** `logistic_regression`, `decision_tree`, `random_forest`, `svm`, `mlp`, `xgboost`.
- **Secuencias (PyTorch):** `lstm`, `gru`, `transformer`, `cnn1d`.
- Pipeline dual: features **2D** (`build_features`) y **3D** (`build_sequences` con lookback + horizonte 5–10 min).
- Tareas: `classification` | `regression` | `both`.
- `POST /api/ml/train` acepta `algorithms[]`, `task`, `lookback_steps`, `horizon_minutes`.
- Métricas thesis en JSONB: precision, recall, f1, false_negative_rate, rmse, lead_time_*, gates `meets_*`.
- Promoción: un `production` por `(scope, task)`; inferencia **prefiere** production `family=sequence` con task `both`/`regression`.
- Retrain dirigido forecast: `scripts/retrain_promote_dl_forecast.py`.

### 7.4 Predicciones, riesgo y forecast (Plan 13)

- Modelo `production` desde `artifact_uri` (preferir PyTorch sequence si existe).
- Features tabular rolling (~20) o secuencia 3D según familia.
- Guarda `Prediction`:
  - `probability` / `predicted_label` / `risk_level` (clasificación)
  - `predicted_concentration` + `horizon_minutes` cuando el modelo tiene cabeza de regresión (desnormalizada con `reg_mean`/`reg_std` del `.pt`)
- Triggers: post-ETL (`PREDICTION_POST_ETL_LIMIT`) y job opcional `PREDICTION_JOB_*`.
- Dashboard: `GET /dashboard/api/forecast-by-gas` agrega histórico por gas canónico + trazo proyectado a t+h.

| Nivel | Umbral default (env) |
|-------|----------------------|
| NORMAL | &lt; 0.3 |
| PRECAUCION | ≥ 0.3 |
| ALERTA | ≥ 0.6 |
| CRITICO | ≥ 0.85 |

### Umbrales thesis (Model Zoo + forecast)

| Métrica | Umbral | Notas |
|---------|--------|-------|
| Recall | ≥ 0.95 | Clasificación |
| Precisión | ≥ 0.90 | Clasificación |
| F1 | ≥ 0.92 | Clasificación |
| FN rate | ≤ 0.05 | Clasificación |
| RMSE | ≤ 0.05 | Concentración a 5–10 min; en datos reales puede no alcanzarse — documentar al promover |
| Lead time | 5–10 min | Alerta anticipada |

### 7.5 Alertas

- Se crean si riesgo ∈ {ALERTA, CRITICO} o hard-alarm (alarma / STEL / TWA).
- Estados: `abierta` → reconocer → resolver (API + UI).
- Recomendaciones por gas en `alerts/recommendations.py`.
- Al crear → `dispatch_alert_notifications`.

### 7.6 Stakeholders / notificaciones

- CRUD stakeholders + suscripciones (site/sensor, `min_level`).
- `StakeholderUser` filtra vistas de interesado.
- Canales: `email` (SMTP si no dry-run), `whatsapp` (stub).
- `NOTIFICATIONS_DRY_RUN=true` por defecto (solo log).

### 7.7 Reportes

Tipos: `alertas_periodo`, `desempeno_modelo`, `resumen_ejecutivo`, `comparativa_modelos`.

- Generación PDF/Excel → archivo en `REPORTS_DIR` + fila en `reports`.
- API: `POST /api/reports/alertas|ejecutivo|modelo/{id}|comparativa`; `GET /api/reports/{id}/download`.
- Interesado: restringido a alertas/suscripciones visibles.
- Auditoría: `report.generate`.

---

## 8. Rutas HTTP (mapa)

### Auth

| Método | Ruta | Notas |
|--------|------|-------|
| GET | `/login` | HTML |
| POST | `/auth/login` | cookies |
| POST | `/auth/refresh` | rota refresh |
| POST | `/auth/logout` | revoca |
| GET | `/auth/me` | usuario actual |

### UI HTML (`dashboard/ui_router`)

| Ruta | Permiso típico | Template |
|------|----------------|----------|
| `/` | home por rol | `dashboard/operador.html` / `ingeniero.html` |
| `/sites`, `/sites/{id}`, `/sensors/{id}` | `predictions.view` | `sites/*` |
| `/alerts`, `/alerts/{id}` | `alerts.view` | `alerts/*` |
| `/ingestion` | `sensors.manage` | `ingestion/panel.html` |
| `/ml/models`, `/ml/models/{id}`, `/ml/train` | `models.train` | `ml/*` |
| `/executive` | `alerts.view` | `dashboard/ejecutivo.html` |
| `/reports` | `reports.export` | `reports/index.html` |
| `/stakeholders` | `stakeholders.manage` | `stakeholders/list.html` |
| `/users` | `users.manage` | `users/list.html` |
| `/roles` | `roles.manage` | `roles/list.html` |
| `/audit` | `audit.view` | `audit/list.html` |
| `/profile` | autenticado | `profile/index.html` |
| `/403` | — | `errors/403.html` |

### Dashboard API (polling)

Prefijo `/dashboard/api`: `semaforo`, `forecast-by-gas`, `series/{sensor_id}`, `alertas-activas`, `sites`, `executive`, `ingeniero`.

### APIs REST

| Prefijo | Uso |
|---------|-----|
| `/api/users` | CRUD + roles |
| `/api/roles`, `/api/permissions` | RBAC |
| `/api/ingestion` | upload, runs |
| `/api/ml` | train, jobs, models, compare, promote |
| `/api/predictions` | list/get |
| `/api/alerts` | list/get, acknowledge, resolve |
| `/api/stakeholders` (+ subscriptions) | CRUD |
| `/api/audit` | list |
| `/api/reports` | generate + download |

Otros: `GET /health`, estáticos en `/static`.

---

## 9. UX / UI — consola profesional

### Identidad visual

| Token | Valor | Uso |
|-------|-------|-----|
| Primary | `#0F766E` (teal) | Botones, acentos, focus |
| Info | `#0284C8` | Charts / links secundarios |
| Canvas | `#F1F5F9` (slate claro) | Fondo main |
| Surface | `#FFFFFF` | Paneles |
| Sidebar | `#0F172A` (slate profundo) | Nav |
| Tipografía | Inter | UI completa |
| Radio / sombra | 12px / sombra suave | `.panel` |

Colores de riesgo (semántica conservada): NORMAL verde, PRECAUCION ámbar, ALERTA naranja, CRITICO rojo — badges en estilo *pill suave* (tint + texto).

### Primitivas de layout (`theme.css`)

- `.panel` / `.panel-flush` — superficie blanca con borde y padding
- `.page-header` — título + subtítulo + acciones
- `.filters-bar` — toolbar de filtros con gap amplio
- `.section-title` / `.section-desc` — jerarquía de sección
- `.kpi-card`, `.sensor-card` — métricas y semáforo
- Sidebar flex columna (`mt-auto` en perfil); grupos **Operación / Datos / Administración**
- Responsive: sidebar colapsable `<768px` (`.app-sidebar.is-open`)

### Partials reutilizables

`_kpi_card.html`, `_risk_badge.html`, `_alerts_table.html`, `_empty_state.html`.

### Patrón de pantalla

```
page-header → (filters-bar opcional) → panel(s) con contenido
```

### Inventario de pantallas

| # | Pantalla | Ruta | Audiencia |
|---|----------|------|-----------|
| P1 | Login | `/login` | público |
| P2 | Home predictivo (forecast + semáforo) | `/` | operador, admin |
| P3 | Sitios / sensores | `/sites`, `/sensors/{id}` | predictions.view |
| P4–P5 | Alertas list/detail | `/alerts` | alerts.view |
| P6 | Ingesta ETL | `/ingestion` | sensors.manage |
| P7–P9 | Modelos / train | `/ml/*` | models.train |
| P10 | Resumen ejecutivo | `/executive` | interesado, admin |
| P11 | Reportes | `/reports` | reports.export |
| P12 | Stakeholders | `/stakeholders` | stakeholders.manage |
| P13 | Usuarios / roles | `/users`, `/roles` | admin |
| P14 | Auditoría | `/audit` | auditor, admin |
| P15 | Perfil | `/profile` | autenticado |

### Sidebar (agrupado)

```
[Marca] Plataforma Gases — “Monitoreo de gases”
Operación:   Inicio · Sitios · Alertas
Datos:       Ingesta · Modelos · Reportes · Ejecutivo
Admin:       Usuarios · Roles · Stakeholders · Auditoría
[Footer]     Perfil / Cerrar sesión
```

Ítems visibles según permisos del usuario.

### Micro-interacciones

- Hover suave en `.panel` / `.sensor-card`
- Active del sidebar con fondo sólido / barra
- `:focus-visible` accesible en controles

**Fuera de alcance UX actual:** iconos SVG masivos, librerías UI nuevas, cambios de lógica/API.

---

## 10. Variables de entorno

Ver `.env.example`. Resumen:

| Variable | Uso |
|----------|-----|
| `DATABASE_URL`, `DB_PASSWORD` | PostgreSQL |
| `JWT_*`, `ACCESS_TOKEN_*`, `REFRESH_TOKEN_*` | Auth |
| `ENVIRONMENT` | `local` / `prod` |
| `MLFLOW_TRACKING_URI` | Tracking ML |
| `ETL_INBOX_*` | Scheduler inbox |
| `RISK_THRESHOLD_*` | Umbrales de riesgo |
| `PREDICTION_*` | Inferencia post-ETL / job |
| `NOTIFICATIONS_DRY_RUN`, `SMTP_*`, `WHATSAPP_*` | Notificaciones |
| `REPORTS_DIR` | Salida reportes |
| `SUPERADMIN_*` | Solo script create_superadmin |

Nunca versionar secretos reales en `.env` ni en este documento.

---

## 11. Arranque local

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env

docker compose up -d db          # opcional: up -d --build (app+mlflow)
alembic upgrade head
python scripts/seed_roles_permissions.py
# SUPERADMIN_* en .env →
python scripts/create_superadmin.py

uvicorn app.main:app --reload
# http://localhost:8000/health · /login · /docs
```

| Servicio Compose | Puerto host |
|------------------|-------------|
| App | 8000 |
| Postgres | 5433 |
| MLflow | 5000 |

Tests: `pytest`.

---

## 12. Reglas de trabajo (para agentes y humanos)

1. **No saltar fases pendientes** (09 GCP, 10 seguridad) sin que el checklist previo esté verde.
2. **Migraciones solo con Alembic.**
3. **Módulos nuevos** siguen la convención `models/schemas/repository/service/router`.
4. **UI:** reutilizar `.panel`, `.page-header`, `.filters-bar` y partials; no introducir frameworks CSS/JS nuevos sin decisión explícita.
5. **Secretos** solo por env / Secret Manager.
6. **Este archivo** es el contexto general; actualizarlo cuando cambie arquitectura, modelo de datos, rutas o UX de forma material.
7. Los planes `01`–`11` en `planes/` siguen siendo la bitácora de ejecución detallada; ante conflicto, **priorizar el código real** y luego sincronizar este contexto.

---

## 13. Pendiente conocido

- **Plan 09:** Cloud Run, Cloud SQL, GCS, Scheduler, CI/CD.
- **Plan 10:** rate limiting, hardening, pruebas de carga, auditoría de seguridad formal.
- WhatsApp: stub (no implementación productiva).
- Recuperación de contraseña: no implementada en UI.

---

*Fin del contexto canónico. Para detalle de un plan concreto, ver `planes/0X_*.md` correspondiente.*
