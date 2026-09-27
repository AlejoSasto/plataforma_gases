# Contexto del sistema — Plataforma de Monitoreo y Predicción de Gases

> **Documento canónico de contexto.** Úsalo como fuente única para agentes, onboarding y decisiones de implementación. Los planes numerados (`01`–`13`) son el historial de ejecución; este archivo describe el **estado real del sistema**. Ante conflicto, **priorizar el código**.

| Campo | Valor |
|-------|--------|
| Nombre | Plataforma de monitoreo y predicción de gases (tesis) |
| Arquitectura | Monolito FastAPI + Jinja2 + PostgreSQL |
| Versión app | `0.1.0` |
| Runtime | Python 3.11+ |
| Actualizado | 2026-09-27 (ML/métricas ampliadas) |

---

## 1. Propósito

Sistema web para:

1. **Ingestar** lecturas de sensores de gases (Excel `dls_report` / CSV processed).
2. **Entrenar y promover** modelos de ML (riesgo + forecast de concentración 5–10 min).
3. **Predecir** concentración futura y riesgo por lectura; **generar alertas** tempranas.
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
| DB | PostgreSQL 15 | Compose puerto host `5433` (contenedor `5432`) |
| Auth | JWT (python-jose) + bcrypt (passlib) | Cookies HttpOnly |
| Frontend | Jinja2 + Bootstrap 5 + Inter + Chart.js | Sin SPA |
| Estilos | `app/static/css/theme.css` | Tokens teal/slate |
| ETL | pandas, openpyxl | Inbox + upload API |
| Jobs | APScheduler | Inbox ETL e inferencia opcional |
| ML | scikit-learn, XGBoost, **PyTorch**, MLflow | `ml_core/` + `model_registry` en DB |
| Reportes | ReportLab (PDF), openpyxl (Excel) | `storage/reports/` |
| Tests | pytest, httpx | `tests/unit`, `tests/integration` |

Dependencias: `requirements.txt` (no hay `pyproject.toml`). Torch en Linux/Docker: instalar CPU según comentario del requirements.

---

## 4. Arquitectura y estructura

```
plataforma-gases/
├── app/
│   ├── main.py                 # App, routers, schedulers, /health
│   ├── core/                   # config, database, security, logging
│   ├── shared/                 # dependencies, exceptions, pagination, gas_catalog, formatting
│   ├── modules/                # dominios (ver §6–§7)
│   ├── templates/              # Jinja2 por pantalla + partials
│   └── static/                 # css/, js/, img/
├── ml_core/                    # columns, data_io, features, Model Zoo, metrics
│   └── models/                 # registry, architectures, train_tabular/sequence, metrics
├── migrations/                 # Alembic versions/
├── scripts/                    # seed, superadmin, ETL, normalize, train/retrain
├── tests/
├── data/                       # raw/, processed/, inbox/  (no hay curated/)
├── storage/reports/
├── docker/                     # Dockerfile.app, Dockerfile.mlflow, Dockerfile.worker (placeholder, no está en Compose)
├── planes/                     # este contexto + planes 00–13
├── docker-compose.yml          # db:5433, mlflow:5000, app:8000
└── .env.example
```

### Convención por módulo

Plantilla objetivo en `app/modules/<nombre>/`:

- `models.py` — SQLAlchemy
- `schemas.py` — Pydantic
- `repository.py` — acceso a datos (si aplica)
- `service.py` — lógica de negocio
- `router.py` — HTTP API y/o HTML

**Estado real:** no todos los módulos tienen `repository.py`. Lo tienen: `auth`, `users`, `roles_permissions`, `sensors_ingestion`, `ml_training`. Lo omiten (lógica en `service`): `alerts`, `predictions`, `reports`, `dashboard`, `stakeholders`, `audit`. `auth` no tiene `models.py` (usa `users`). `dashboard` no persiste tablas propias.

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

## 5. Datos de campo y datasets

Fuente de verdad para entrenamiento/ingesta: `gas_readings` en PostgreSQL. Los archivos de `data/` son el origen y el respaldo.

### Dónde está cada cosa

| Ruta | Qué es | ¿Entra al ETL? |
|------|--------|----------------|
| `data/raw/dls_report_*.xlsx` | Excel iNet, hoja `Resumen`, cabecera fila 24 | Sí (`ml_core.data_io.load_dls_report`) |
| `data/raw/alarmReport_*.xlsx` | Reportes de alarma | No (no hay parser) |
| `data/raw/Historial del registro de datos.xlsx` | Bitácora de **sesiones** de un MX6 CO2 (33 filas, nov–dic 2024). No son lecturas | No |
| `data/processed/Procesamiento_de_Datos.csv` | Consolidado **real** | Sí (`--consolidado`) |
| `data/processed/Procesamiento_de_Datos_YYYY-MM.csv` | Mismo consolidado partido por mes | Origen del consolidado |
| `data/processed/Procesamiento_de_Datos_24m.csv` | Zoo aumentado a 24 meses | Sí (`--augmented-24m`, marca `is_synthetic`) |
| `data/processed/augmentation_manifest.json` | Trazabilidad source_month → target_month | Solo al marcar sintéticos |
| `data/inbox/` | Cola automática (.xlsx/.xls) | Sí, si `ETL_INBOX_ENABLED` |

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

### Dataset sintético 24 meses

~**176.738 filas**, ene-2024–dic-2025. Los meses faltantes se clonan desde los 9 meses reales (`source_month` → `target_month`). Filas inventadas: `is_synthetic=true`. **No incluye** mar-2023 (empieza en ene-2024).

Carga:

```bash
python scripts/load_processed_dataset.py --consolidado
python scripts/load_processed_dataset.py --augmented-24m
# o --all
```

### Catálogo de gases (`app/shared/gas_catalog.py`)

Códigos: `CH4`, `CO`, `H2S`, `CO2`, `O2`, `NO2`, `UNKNOWN`. Alias: `LEL(CH4)`/`LEL`/`Gas combustible` → CH4; se limpia prefijo `Sensor SN:`; `SIN_SITIO` → “Sin sitio asignado”.

---

## 6. Modelo de datos

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
| `alerts` | prediction_id, gas_reading_id, sensor_id, level, message, recommendation, status (`abierta`/`reconocida`/`resuelta`), acknowledged_by/at, **resolved_at**, resolution_note (no hay `resolved_by`) | FKs prediction, reading, sensor, user |
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

## 7. Roles, permisos y aterrizaje UI

### Permisos (`scripts/seed_roles_permissions.py`)

`users.manage`, `roles.manage`, `sensors.manage`, `models.train`, `models.promote`, `predictions.view`, `alerts.view`, `alerts.resolve`, `stakeholders.manage`, `reports.export`, `dashboard.view_all_sites`, `audit.view`.

### Roles

| Rol | Permisos (resumen) | Home UI |
|-----|-------------------|---------|
| `admin` | todos | Semáforo `/` |
| `ingeniero_datos` | sensors, models train/promote, predictions, alerts view, reports | Panel ingeniero `/?view=ingeniero` |
| `operador_mina` | alerts view/resolve, predictions.view | Semáforo `/` |
| `interesado` | alerts.view, reports.export | `/executive` |
| `auditor` | predictions, alerts, reports, dashboard.view_all_sites, audit.view | `/audit` |

Superadmin: `scripts/create_superadmin.py` + `SUPERADMIN_*` en env.

La navegación del sidebar se arma por **permisos**, no por rol hardcodeado. El **aterrizaje** (`home_path_for_user` / `GET /`) sí usa roles (interesado puro → ejecutivo; ingeniero puro → panel; auditor puro → auditoría).

---

## 8. Flujos de negocio

### 8.1 Autenticación

1. UI `/login` → `POST /auth/login` (email/password).
2. Access JWT en cookie `access_token` (claims: sub, roles, permissions).
3. Refresh opaco (hash SHA-256 en DB) en cookie `refresh_token`.
4. `get_current_user` + `require_permission(code)` en rutas protegidas.
5. `POST /auth/refresh` rota tokens; `POST /auth/logout` revoca y limpia cookies.
6. HTML sin sesión → redirect `/login`; sin permiso → `/403`.
7. Defaults: access 30 min, refresh 7 días, HS256.
8. Cambio de clave (logueado): `POST /profile/password`. **Recuperación** (olvidé mi clave) no existe.

### 8.2 Ingesta ETL

1. **Upload:** `POST /api/ingestion/upload` (Excel `dls_report`) → limpieza `ml_core.data_io` → persistencia.
2. **Inbox:** `data/inbox` (.xlsx/.xls); APScheduler si `ETL_INBOX_ENABLED=true`.
3. **Scripts:** `scripts/load_processed_dataset.py`, `scripts/run_etl_inbox.py`.
4. Por fila: get_or_create `Site`/`Sensor` con **nombres canónicos** (`gas_catalog`) → `GasReading` → `EtlRun`.
5. Tras ETL exitoso: `run_predictions_for_etl_run` (fallo ML no aborta el ETL).
6. Éxito inbox → `inbox/processed`; error → `inbox/failed`.
7. Backfill opcional: `scripts/normalize_sensors_display.py`.
8. El historial de sesiones MX6 y los `alarmReport_*` **no** se ingieren.

### 8.3 Modelos de IA — qué son y qué NO son

El sistema **no usa LLMs** (GPT, Claude, BERT, Hugging Face). El “Model Zoo” son **10 algoritmos clásicos / redes pequeñas** entrenados sobre `gas_readings` para dos problemas de tesis:

1. **Clasificación de riesgo:** ¿esta lectura (o su ventana) corresponde a un `evento_final` (alarma, STEL o percentil 95 del sensor)?
2. **Regresión / forecast:** ¿cuál será la concentración (`Leyendo`) en ~**7.5 min** (rango operativo 5–10 min)?
3. **Lead time:** ¿el clasificador avisa *antes* de que ocurra el evento (ventana 5–10 min)?

Catálogo canónico: `ml_core/models/registry.py`. Arquitecturas DL: `ml_core/models/architectures.py`. Orquestador: `ml_core/models/train_model.py`. Persistencia: tablas `training_jobs` + `model_registry`. Artefactos: **MLflow** experimento `plataforma-gases-training`. Inferencia en vivo: `app/modules/predictions/service.py`.

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

Puede haber más de un `production` si tienen **tasks distintas**. El runtime **ignora** un tabular production si existe un DL production: el forecast del home depende de eso.

---

### 8.4 Inferencia, semáforo y forecast (cómo el modelo vive en producción)

Archivo: `app/modules/predictions/service.py`. Una predicción por `gas_reading_id` (si ya existe, se reutiliza).

```
gas_readings (reales, no sintéticas)
        ↓ trigger
predict_for_reading → fila predictions
        ↓
evaluate_and_create_alert  (si ALERTA/CRITICO o hard-alarm)
        ↓
dispatch_alert_notifications
        ↓
UI: semáforo `/`, forecast-by-gas, /alerts, /executive
```

**Triggers**

| Trigger | Condición | Límite |
|---------|-----------|--------|
| Post-ETL | Tras ingesta exitosa (`sensors_ingestion`) | `PREDICTION_POST_ETL_LIMIT` (default 500; 0 = todas). Solo `is_synthetic=false` |
| Job APScheduler | `PREDICTION_JOB_ENABLED=true` | intervalo `PREDICTION_JOB_INTERVAL_SECONDS` (120) |
| On-the-fly | `forecast_concentration_for_reading` / home Chart.js | no persiste; solo si el production es sequence |

Si no hay modelo production, el ETL **no falla** (stats `skipped=1`).

**Camino tabular (sklearn/XGB)**

1. Ventana de ~25 lecturas del mismo sensor (`ROLLING_WINDOW+5`).
2. Recalcula las 5 features; vector 2D.
3. `predict_proba` → P(clase 1). Label = 1 si P ≥ 0.5.
4. No rellena `predicted_concentration` (salvo que en el futuro se use un regresor tabular en producción; hoy el home de forecast exige PyTorch).

**Camino sequence (PyTorch)**

1. Tensor `[1, lookback, 5]`, padding si faltan pasos.
2. Normaliza con `norm_mean/std` del `.pt`.
3. Sigmoid de logits → `probability`. Label = 1 si P ≥ `cls_threshold` guardado.
4. Cabeza reg: desnormaliza `yhat * reg_std + reg_mean` → `predicted_concentration`.
5. Si solo hay regresión (sin logits): P ≈ \|c\| / (\|c\|+1) (suave, no es probabilidad calibrada).
6. `horizon_minutes` se guarda solo si hay concentración.

**Riesgo operativo** (no son las métricas thesis; son umbrales de **probabilidad**):

| `risk_level` | Default | Env |
|--------------|---------|-----|
| NORMAL | P &lt; 0.3 | — |
| PRECAUCION | P ≥ 0.3 | `RISK_THRESHOLD_PRECAUTION` |
| ALERTA | P ≥ 0.6 | `RISK_THRESHOLD_ALERT` |
| CRITICO | P ≥ 0.85 | `RISK_THRESHOLD_CRITICAL` |

Función: `probability_to_risk_level`. La fila `predictions` guarda `probability`, `predicted_label`, `risk_level`, `predicted_concentration`, `horizon_minutes`, FKs a reading y `model_registry`.

**Alertas a partir del modelo** (`alerts/rules.py`): se crea alerta si `risk_level ∈ {ALERTA, CRITICO}` **o** hard-alarm (campo alarma / STEL / TWA). Si hay hard-alarm y el modelo dijo NORMAL/PRECAUCION, se **sube** el nivel de la alerta a ALERTA. Recomendación textual por gas.

**Forecast del home** (`GET /dashboard/api/forecast-by-gas`):

- Histórico real reciente (no sintético), agregado por gas canónico (prioridad CH4, CO, H2S).
- Trazo futuro a t+h **solo si** `has_sequence_production`.
- Concentración on-the-fly desde la última lectura por sensor (`forecast_concentration_for_reading`).
- Chart.js en `dashboard/operador.html` (poll ~10 s).

**Superficies que leen el modelo / sus salidas**

| Superficie | Qué muestra |
|------------|-------------|
| `/` operador | Semáforo por sensor + forecast por gas |
| `/?view=ingeniero` | Snapshot de jobs/modelos |
| `/ml/models` | Matriz zoo + gates thesis |
| `/ml/models/{id}` | Métricas, params, promote |
| `/ml/train` | Selector algoritmos / task / lookback / horizonte |
| `/ml/compare` | Comparativa + chart |
| `/alerts` | Alertas derivadas de predicción + reglas |
| `/executive` | KPIs de alertas (efecto del modelo, no las métricas crudas) |
| Reportes `desempeno_modelo` / `comparativa_modelos` | PDF/Excel de metrics JSONB |
| MLflow `:5000` | Runs y artefactos |

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
| GET | `/login` | HTML |
| POST | `/auth/login` | cookies |
| POST | `/auth/refresh` | rota refresh |
| POST | `/auth/logout` | revoca |
| GET | `/auth/me` | usuario actual |

### UI HTML (`dashboard/ui_router`)

| Ruta | Permiso típico | Template |
|------|----------------|----------|
| `/` | home por rol | `operador.html` (semáforo+forecast) o `ingeniero.html` |
| `/sites`, `/sites/{id}`, `/sensors/{id}` | `predictions.view` | `sites/*` |
| `/alerts`, `/alerts/{id}` | `alerts.view` | `alerts/*` |
| `/ingestion` | `sensors.manage` | `ingestion/panel.html` |
| `/ml/models`, `/ml/models/{id}`, `/ml/train`, **`/ml/compare`** | `models.train` | `ml/*` |
| `/executive` | ruta: `alerts.view`; ítem sidebar: `reports.export` o admin | `dashboard/ejecutivo.html` |
| `/reports` | `reports.export` | `reports/index.html` |
| `/stakeholders` | `stakeholders.manage` | `stakeholders/list.html` |
| `/users` | `users.manage` | `users/list.html` |
| `/roles` | `roles.manage` | `roles/list.html` |
| `/audit` | `audit.view` | `audit/list.html` |
| `/profile` | autenticado | `profile/index.html` |
| `POST /profile/password` | autenticado | cambio de clave |
| `/403` | — | `errors/403.html` |
| `/interesado/alertas` | — | redirect 302 → `/executive` |

### Dashboard API (polling)

Prefijo `/dashboard/api`: `semaforo`, `forecast-by-gas`, `series/{sensor_id}`, `alertas-activas`, `sites`, `executive`, `ingeniero`.

### APIs REST

| Prefijo | Uso |
|---------|-----|
| `/api/users` | CRUD + roles |
| `/api/roles`, `/api/permissions` | RBAC |
| `/api/ingestion` | upload, runs |
| `/api/ml` | **catalog**, train, jobs, models, compare, promote |
| `/api/predictions` | list/get |
| `/api/alerts` | list/get, acknowledge, resolve |
| `/api/stakeholders` | CRUD; suscripciones en `/api/stakeholders/{id}/subscriptions` y `DELETE /api/subscriptions/{id}` |
| `/api/audit` | list |
| `/api/reports` | generate + download |

Otros: `GET /health`, estáticos en `/static`.

---

## 10. UX / UI — consola profesional

### Identidad visual

| Token | Valor | Uso |
|-------|-------|-----|
| Primary | `#0F766E` (teal) | Botones, acentos, focus |
| Info | `#0284C8` | Charts / links secundarios |
| Canvas | `#F1F5F9` (slate claro) | Fondo main |
| Surface | `#FFFFFF` | Paneles |
| Sidebar | `#0F172A` (slate profundo) | Nav |
| Tipografía | Inter (import en `theme.css`) | UI completa |
| Radio / sombra | 12px / sombra suave | `.panel` |

Colores de riesgo (semántica conservada): NORMAL verde, PRECAUCION ámbar, ALERTA naranja, CRITICO rojo — badges en estilo *pill suave* (tint + texto).

### Primitivas de layout (`theme.css`)

- `.panel` / `.panel-flush` — superficie blanca con borde y padding
- `.page-header` — título + subtítulo + acciones
- `.filters-bar` — toolbar de filtros con gap amplio
- `.section-title` / `.section-desc` — jerarquía de sección
- `.kpi-card`, `.sensor-card` — métricas y semáforo
- Sidebar flex columna; grupos **Operación / Datos / Administración**
- Responsive: sidebar colapsable `<768px` (`.app-sidebar.is-open`)

### Partials reutilizables

`_kpi_card.html`, `_risk_badge.html`, `_alerts_table.html`, `_empty_state.html`, `_metric_gate.html`.

Legado: `stakeholders/interesado_alertas.html` (la ruta vieja redirige a `/executive`).

### Patrón de pantalla

```
page-header → (filters-bar opcional) → panel(s) con contenido
```

### Inventario de pantallas

| # | Pantalla | Ruta | Audiencia |
|---|----------|------|-----------|
| P1 | Login | `/login` | público |
| P2 | Home predictivo (forecast + semáforo) | `/` | operador, admin |
| P2b | Panel ingeniero | `/?view=ingeniero` | ingeniero_datos |
| P3 | Sitios / sensores | `/sites`, `/sensors/{id}` | predictions.view |
| P4–P5 | Alertas list/detail | `/alerts` | alerts.view |
| P6 | Ingesta ETL | `/ingestion` | sensors.manage |
| P7–P9 | Modelos / detalle / train / **compare** | `/ml/models`, `/ml/train`, `/ml/compare` | models.train |
| P10 | Resumen ejecutivo | `/executive` | interesado, admin (y quien tenga `reports.export` en nav) |
| P11 | Reportes | `/reports` | reports.export |
| P12 | Stakeholders | `/stakeholders` | stakeholders.manage |
| P13 | Usuarios / roles | `/users`, `/roles` | admin |
| P14 | Auditoría | `/audit` | auditor, admin |
| P15 | Perfil (incluye cambio de clave) | `/profile` | autenticado |

### Sidebar (agrupado)

```
[Marca] Plataforma Gases — “Monitoreo predictivo de gases · mina”
Operación:   Inicio · Sitios y sensores · Alertas
Datos:       Ingesta / ETL · Modelos · Reportes · Resumen ejecutivo
Admin:       Partes interesadas · Usuarios · Roles y permisos · Auditoría
[Footer]     Nombre / email (perfil)
```

Ítems visibles según permisos. Ejecutivo en nav: `reports.export` o rol `admin` (la ruta exige `alerts.view`).

### Micro-interacciones

- Hover suave en `.panel` / `.sensor-card`
- Active del sidebar con fondo sólido / barra
- `:focus-visible` accesible en controles

**Fuera de alcance UX actual:** iconos SVG masivos, librerías UI nuevas, cambios de lógica/API.

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
| `SUPERADMIN_*` | Solo script create_superadmin |

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

uvicorn app.main:app --reload
# http://localhost:8000/health · /login · /docs
```

| Servicio Compose | Puerto host |
|------------------|-------------|
| App | 8000 |
| Postgres | 5433 |
| MLflow | 5000 |

### Scripts útiles

| Script | Uso |
|--------|-----|
| `seed_roles_permissions.py` | Permisos y roles base |
| `create_superadmin.py` | Usuario admin inicial |
| `check_db.py` | Sanity check de conexión |
| `load_processed_dataset.py` | Carga consolidado y/o 24m |
| `run_etl_inbox.py` | Una pasada del inbox |
| `normalize_sensors_display.py` | Backfill nombres canónicos |
| `train_full_model_zoo.py` | Entrena tabulares + DL y promueve el mejor |
| `retrain_dl_and_promote.py` | Reentrena secuencias y promueve |
| `retrain_promote_dl_forecast.py` | Reentrena DL orientado a forecast |

Tests: `pytest`.

---

## 13. Reglas de trabajo (para agentes y humanos)

1. **No saltar fases pendientes** (09 GCP, 10 seguridad) sin que el checklist previo esté verde.
2. **Migraciones solo con Alembic.**
3. **Módulos nuevos** siguen la convención `models/schemas/repository/service/router` (repository solo si hay persistencia propia).
4. **UI:** reutilizar `.panel`, `.page-header`, `.filters-bar` y partials; no introducir frameworks CSS/JS nuevos sin decisión explícita.
5. **Secretos** solo por env / Secret Manager.
6. **Este archivo** es el contexto general; actualizarlo cuando cambie arquitectura, **datos**, modelo de datos, rutas o UX de forma material.
7. Los planes `01`–`13` en `planes/` son la bitácora de ejecución; ante conflicto, **priorizar el código real** y luego sincronizar este contexto.

---

## 14. Pendiente conocido

- **Plan 09:** Cloud Run, Cloud SQL, GCS, Scheduler, CI/CD. `docker/Dockerfile.worker` es placeholder (no hay worker en Compose; no hay Celery).
- **Plan 10:** rate limiting, hardening, pruebas de carga, auditoría de seguridad formal.
- WhatsApp: stub (no implementación productiva).
- Recuperación de contraseña (flujo “olvidé mi clave”): no implementada. El cambio de clave en `/profile` sí existe.
- Parser de `alarmReport_*.xlsx` y del historial de sesiones MX6: no implementado (no son lecturas).
- RMSE thesis ≤ 0.05: puede no alcanzarse con el consolidado real irregular; documentar al promover.

---

*Fin del contexto canónico. Para detalle de un plan concreto, ver `planes/0X_*.md` correspondiente.*
