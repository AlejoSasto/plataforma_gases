# Plataforma Gases

Monolito FastAPI para monitoreo y predicción de gases (tesis).

## Requisitos

- Python 3.11+
- Docker / Docker Compose

## Arranque local (sin Docker para la app)

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # o usa el .env ya creado
```

`DATABASE_URL` en `.env` usa `localhost:5433` para uvicorn/Alembic en el host
(Compose publica Postgres en 5433 para no chocar con un Postgres local en 5432).
Dentro de Compose, la app usa host `db` y puerto `5432` (ver `docker-compose.yml`).

```bash
uvicorn app.main:app --reload
# GET http://localhost:8000/health
```

## Arranque con Docker

```bash
docker compose up -d --build
curl http://localhost:8000/health
```

## Base de datos / migraciones

```bash
# Con Postgres levantado (compose db o local):
alembic upgrade head
python scripts/check_db.py
```

## Convenciones de módulo

Cada dominio vive en `app/modules/<nombre>/` con: `models.py`, `schemas.py`,
`repository.py`, `service.py`, `router.py`.

## Plan actual

Planes 01–08, 11 y **12 (Model Zoo)** implementados.
Siguiente: Plan 09 Despliegue GCP / CI-CD · Plan 10 Seguridad.

### Auth (Plan 02)

```bash
alembic upgrade head
python scripts/seed_roles_permissions.py
# Windows PowerShell:
$env:SUPERADMIN_EMAIL="admin@example.com"
$env:SUPERADMIN_PASSWORD="cambia-esta-password"
python scripts/create_superadmin.py
# Login UI: http://localhost:8000/login
```

### Ingesta ETL (Plan 03)

```bash
alembic upgrade head
# Subir Excel vía Swagger /docs → POST /api/ingestion/upload (permiso sensors.manage)
# O cargar CSV processed:
python scripts/load_processed_dataset.py --consolidado
python scripts/load_processed_dataset.py --augmented-24m
# Inbox automático:
# ETL_INBOX_ENABLED=true  (o una pasada: python scripts/run_etl_inbox.py)
```

### ML Training / Model Zoo (Planes 04 + 12)

```bash
docker compose up -d mlflow   # UI http://localhost:5000
pip install -r requirements.txt   # incluye torch (CPU)
alembic upgrade head
# UI: /ml/models (matriz thesis) · /ml/train (selector) · /ml/compare
# API: POST /api/ml/train  { algorithms, task, lookback_steps, horizon_minutes, params }
#      GET  /api/ml/catalog · /api/ml/models/compare
#      POST /api/ml/models/{id}/promote
# Algoritmos: decision_tree, random_forest, xgboost, svm, mlp, logistic_regression,
#             lstm, gru, transformer, cnn1d
# Umbrales thesis: Recall≥0.95, Precisión≥0.90, F1≥0.92, FN≤5%, RMSE≤0.05, lead 5–10 min
# Contexto: planes/CONTEXTO_SISTEMA.md · Plan 12: planes/12_MODEL_ZOO_SERIES_METRICAS_UI.md
```

### Predicciones / Alertas (Plan 05)

```bash
# Requiere modelo en production (Plan 04/12) — sklearn/xgboost o PyTorch según family
# Tras ETL exitoso se generan predicciones (límite PREDICTION_POST_ETL_LIMIT)
# GET /api/predictions (predictions.view)
# GET /api/alerts ; POST /api/alerts/{id}/acknowledge|resolve
```

### Stakeholders / Notificaciones (Plan 06)

```bash
# CRUD API: /api/stakeholders + /api/subscriptions (stakeholders.manage)
# NOTIFICATIONS_DRY_RUN=true por defecto (sin SMTP real)
# UI: /stakeholders · Resumen: /executive
```

### Dashboard / UI (Planes 07 y 11)

```bash
python scripts/seed_roles_permissions.py   # incluye audit.view
# Login: http://localhost:8000/login
# Home por rol: /  (operador semáforo · ingeniero panel · interesado → /executive)
# APIs polling: /dashboard/api/semaforo · /series/{id} · /alertas-activas
# Pantallas: /alerts /sites /ingestion /ml/models /ml/compare /users /roles /audit /profile /reports
```

### Reportes (Plan 08 + 12)

```bash
alembic upgrade head
python scripts/seed_roles_permissions.py   # ingeniero_datos también tiene reports.export
# UI: /reports  ·  API: POST /api/reports/alertas|ejecutivo|modelo/{id}|comparativa
# Descarga: GET /api/reports/{id}/download
# Archivos en storage/reports/ (REPORTS_DIR)
pytest
```
