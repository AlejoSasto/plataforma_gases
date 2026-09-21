# Plan 03 — Ingesta y ETL de Sensores (F2)

## Objetivo
Migrar la fuente de verdad de archivos Excel/CSV a PostgreSQL, reutilizando la lógica de limpieza que ya existe en `proyecto-gases`, con trazabilidad completa de cada corrida de ETL (cumple el objetivo 2 del documento: "documentando cada transformación").

## Prerrequisitos
- Plan 01 y 02 validados.
- Código fuente de `proyecto-gases` disponible (especialmente `src/data_io.py`, `src/gases_augmentation.py`, esquema canónico de 15 columnas).

## Paso a paso

### 1. Copiar el pipeline actual como librería interna
- Crear `ml_core/` en el nuevo repo.
- Copiar (sin reescribir aún) `data_io.py`, `gases_augmentation.py`, `EXPECTED_COLUMNS` y utilidades relacionadas.
- Ajustar imports para que sean un paquete instalable (`ml_core/__init__.py`).
**Prueba:** `python -c "from ml_core.data_io import load_processed"` no falla (aunque su implementación cambie luego).

### 2. Modelos (`app/modules/sensors_ingestion/models.py`)
```
sites(id, name, description)
sensors(id, site_id FK, code, gas_type, unit)
gas_readings(id, sensor_id FK, leyendo, unidad, stel_max, twa_max, alarma,
             temperatura, tiempo_inicio, tiempo_fin, is_synthetic BOOL,
             source_file, created_at)
etl_runs(id, started_at, finished_at, status, rows_ingested, rows_rejected,
         source_files JSONB, log JSONB)
```
**Prueba:** migración Alembic aplica sin error; índices en `gas_readings(sensor_id, tiempo_inicio)`.

### 3. `repository.py` — acceso a datos
- `bulk_insert_readings(db, readings: list[dict])` (usar `bulk_insert_mappings` o `COPY` para volúmenes grandes, dado el histórico de ~176k filas del dataset de 24 meses).
- `get_or_create_site`, `get_or_create_sensor`.
- `create_etl_run`, `update_etl_run(status, rows_ingested, rows_rejected, log)`.
**Prueba:** insertar 1000 filas sintéticas de prueba y medir tiempo (< unos segundos).

### 4. `service.py` — orquestación del ETL
Reescribir la lógica de `data_io.py`/`gases_augmentation.py` para que, en vez de escribir CSV, devuelva un DataFrame limpio y esta capa lo persista en `gas_readings`. Pasos internos:
1. Leer archivo(s) Excel (`dls_report_*.xlsx`, hoja *Resumen*, cabecera en fila 24 — igual que el proyecto actual).
2. Validar columnas contra `EXPECTED_COLUMNS` (15 columnas); filas que no cumplan van a `rows_rejected` con motivo en el log.
3. Normalizar tipos (fechas, numéricos), resolver `site`/`sensor` (crear si no existen).
4. Insertar en `gas_readings` (`is_synthetic=false` para datos reales).
5. Registrar resumen estructurado en `etl_runs.log`: columnas normalizadas, filas imputadas, rangos de fecha procesados, advertencias.
**Prueba:** correr el servicio contra 2-3 archivos Excel reales de muestra; verificar que `gas_readings` recibe las filas esperadas y `etl_runs.log` documenta cada transformación aplicada.

### 5. Endpoint manual de ingesta (`modules/sensors_ingestion/router.py`, protegido con `sensors.manage`)
- `POST /ingestion/upload` — recibe uno o más archivos (`UploadFile`), ejecuta el servicio de forma síncrona (fase inicial) y devuelve el resumen del `etl_run`.
- `GET /ingestion/runs` — historial paginado de corridas ETL con su estado.
- `GET /ingestion/runs/{id}` — detalle completo (incluye el log de transformaciones).
**Prueba:** subir un archivo vía Swagger UI (`/docs`) y confirmar la respuesta con `rows_ingested > 0`.

### 6. Automatización (background, sin bloquear la API)
- Introducir Celery + Redis (o `APScheduler` si se prefiere evitar un servicio más en esta fase) para:
  - Job periódico que revisa una carpeta/bucket de entrada y dispara el ETL automáticamente.
  - Alternativa más simple para el taller: mantener el endpoint manual + un cron simple que llame al mismo servicio.
**Prueba:** al dejar un archivo nuevo en la carpeta/bucket de entrada, dentro del intervalo configurado aparece una fila nueva en `etl_runs` con `status=success`.

### 7. Aumentación temporal (24 meses) — opcional en esta fase
- Si se desea conservar el dataset aumentado a 24 meses para entrenar (como en el proyecto actual), portar `gases_augmentation.py` para que:
  - Lea desde `gas_readings` en vez de CSV.
  - Escriba los registros sintéticos también en `gas_readings` con `is_synthetic=true` y referencia al `augmentation_manifest` (guardar el manifest como JSONB en `etl_runs.log` o en una tabla `augmentation_manifest` separada).
**Prueba:** conteo de filas reales vs. sintéticas coincide con lo esperado (`SELECT is_synthetic, count(*) FROM gas_readings GROUP BY 1;`).

### 8. Auditoría
- Registrar en `audit_log` cada ingesta manual (`user_id`, `etl_run_id`, cantidad de filas).

## Checklist de validación (Definition of Done)
- [ ] Subir un Excel real reproduce el mismo resultado (filas válidas/ inválidas) que el pipeline original de `proyecto-gases`.
- [ ] `etl_runs.log` documenta explícitamente cada transformación (no solo "éxito/fracaso").
- [ ] Los datos sintéticos quedan marcados (`is_synthetic=true`) y son filtrables.
- [ ] El endpoint de ingesta está protegido por permiso (`sensors.manage`) y auditado.
- [ ] Inserciones masivas (decenas de miles de filas) no exceden un tiempo razonable (< 1 min para el dataset de 24 meses).

**Siguiente paso:** `04_ML_ENTRENAMIENTO_MODELOS.md`.
