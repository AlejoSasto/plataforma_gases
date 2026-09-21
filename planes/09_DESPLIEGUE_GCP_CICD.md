# Plan 09 — Despliegue en GCP y CI/CD (F8)

## Objetivo
Llevar la plataforma completa (validada localmente en los planes 01–08) a un entorno productivo escalable en GCP, reutilizando el patrón de Cloud Run Job + Scheduler que ya está documentado y probado en `proyecto-gases` para el ETL.

## Prerrequisitos
- Planes 01–08 validados localmente con Docker Compose.
- Proyecto GCP existente o nuevo (ej. reutilizar `gases-mina` o crear uno específico para la plataforma).
- `gcloud` CLI autenticado.

## Paso a paso

### 1. Inventario de servicios a crear
| Servicio local (Compose) | Equivalente GCP |
|---|---|
| `app` | Cloud Run (servicio web) |
| `worker` (Celery/ETL/training) | Cloud Run Jobs (igual patrón que el ETL actual) |
| `db` (Postgres) | Cloud SQL for PostgreSQL |
| Volumen de artefactos/reportes | Cloud Storage (buckets `raw/`, `processed/`, `curated/`, `mlruns/`, `artifacts/`, `reports/`) |
| `mlflow` | Cloud Run (servicio) con backend store en Cloud SQL y artifact root en Cloud Storage |
| `redis` | Memorystore for Redis (o mantener Redis solo si el volumen de jobs lo justifica) |
| Cron del ETL | Cloud Scheduler (mismo patrón ya usado: `*/5 * * * *` o ajustado a necesidad real) |

### 2. Cloud SQL
- Crear instancia Postgres 15, base `proyecto_gases`.
- Configurar Cloud SQL Auth Proxy (o conexión Unix socket desde Cloud Run) — **no** exponer IP pública sin restricciones.
- Migrar credenciales (usuario/password) a **Secret Manager**, nunca en variables de entorno planas del servicio.
**Prueba:** desde Cloud Shell, conectar con `psql` vía el proxy y confirmar acceso a `proyecto_gases`.

### 3. Secret Manager
- Secretos a crear: `db-password`, `jwt-secret`, `smtp-credentials` (si se implementó notificación por email en Plan 06).
- Dar acceso (`roles/secretmanager.secretAccessor`) solo a las cuentas de servicio que lo necesiten (principio de menor privilegio).
**Prueba:** `gcloud secrets versions access latest --secret=db-password` funciona solo para la cuenta autorizada.

### 4. Cloud Storage
- Crear buckets según el inventario del paso 1.
- Ajustar `ml_core` y `reports/generator.py` para leer/escribir usando `google-cloud-storage` cuando `ENVIRONMENT=prod` (mantener filesystem local cuando `ENVIRONMENT=local`), vía una capa de abstracción simple (`storage_backend.py` con `save()`/`load()`).
**Prueba:** al correr en Cloud Run, un archivo generado (reporte o artefacto de modelo) aparece en el bucket correspondiente.

### 5. Imagen y build
- `Dockerfile.app` y `Dockerfile.worker` ya existen (Plan 01/03). Ajustar para producción: `ENVIRONMENT=prod`, sin `--reload`, con `gunicorn` + varios workers según CPU asignada.
- `cloudbuild.yaml`: build de ambas imágenes, push a **Artifact Registry**.
**Prueba:** `gcloud builds submit --config cloudbuild.yaml` termina exitosamente y las imágenes aparecen en Artifact Registry.

### 6. Cloud Run — servicio `app`
```bash
gcloud run deploy plataforma-gases-app \
  --image=REGION-docker.pkg.dev/PROJECT/REPO/app:latest \
  --region=us-central1 \
  --set-env-vars="ENVIRONMENT=prod" \
  --set-secrets="DB_PASSWORD=db-password:latest,JWT_SECRET=jwt-secret:latest" \
  --add-cloudsql-instances=PROJECT:REGION:INSTANCE \
  --min-instances=0 --max-instances=10
```
**Prueba:** `curl https://<url-cloud-run>/health` responde 200; login funciona igual que en local.

### 7. Cloud Run Jobs — `worker` (ETL / entrenamiento)
- Reutilizar el patrón ya documentado en `proyecto-gases` (`scripts/setup_gcp_etl_job.sh`, IAM, `run.invoker`) adaptado al nuevo entrypoint (`scripts/run_etl_cloud.py` equivalente que llama al `sensors_ingestion.service` en vez de los notebooks).
**Prueba:** `gcloud run jobs execute plataforma-gases-etl-job --region=us-central1` corre sin error y crea filas nuevas en `etl_runs`/`gas_readings`.

### 8. Cloud Scheduler
- Job que dispara `plataforma-gases-etl-job` con la periodicidad definida (evaluar bajar de `*/5 * * * *` a algo menos agresivo si no hay ingestión continua real, como ya está anotado en el backlog de optimización del proyecto actual).
**Prueba:** tras esperar un ciclo, `gcloud scheduler jobs describe ...` muestra la última ejecución exitosa.

### 9. MLflow en la nube
- Desplegar como servicio Cloud Run separado, backend store apuntando a una base/esquema en el mismo Cloud SQL, artifact root al bucket `mlruns/`.
**Prueba:** un entrenamiento disparado desde `app` en producción queda visible en la UI de MLflow desplegada.

### 10. CI/CD (GitHub Actions o Cloud Build triggers)
- Pipeline: en cada push a `main` → tests (`pytest`) → build imágenes → push a Artifact Registry → `gcloud run deploy` (app) y actualización del Job (worker).
- Migraciones: paso explícito `alembic upgrade head` contra Cloud SQL antes de enrutar tráfico a la nueva revisión (evitar aplicar migraciones dentro del contenedor en cada arranque).
**Prueba:** un cambio de código trivial (ej. texto en una vista) se refleja en producción tras el pipeline, sin intervención manual.

### 11. Observabilidad
- Confirmar que logs de `app` y `worker` llegan a Cloud Logging en formato estructurado (heredado de Plan 01).
- Configurar alertas de Cloud Monitoring sobre la infraestructura (latencia, errores 5xx, fallos del Job) — distintas de las alertas de negocio del Plan 05.
**Prueba:** forzar un error 500 de prueba y verificar que aparece en Cloud Logging/Monitoring.

## Checklist de validación (Definition of Done)
- [ ] `app` corre en Cloud Run y responde `/health` correctamente.
- [ ] El Job de ETL/entrenamiento corre vía Cloud Run Jobs + Scheduler, igual que el patrón ya validado en `proyecto-gases`.
- [ ] Credenciales y secretos viven en Secret Manager, no en el código ni en variables planas.
- [ ] Artefactos de modelos, datasets y reportes se leen/escriben desde Cloud Storage en producción.
- [ ] Migraciones de base de datos se aplican de forma controlada como paso del pipeline, no automáticamente al iniciar cada contenedor.
- [ ] Pipeline de CI/CD despliega sin pasos manuales tras un push a `main`.

**Siguiente paso:** `10_SEGURIDAD_TESTING_HARDENING.md`.
