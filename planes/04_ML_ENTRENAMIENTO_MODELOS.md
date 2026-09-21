# Plan 04 — Entrenamiento de Modelos ML (F3)

> **Extendido por Plan 12** (`12_MODEL_ZOO_SERIES_METRICAS_UI.md`): Model Zoo completo (tabulares + PyTorch), pipeline 2D/3D, métricas thesis y UI profesional. Este documento conserva el alcance original F3.

## Objetivo
Exponer el pipeline de features + entrenamiento (ya validado en `proyecto-gases`: LR/RF/XGBoost, F1≈0.90 y recall≈0.99 con XGBoost) como un módulo gestionado desde la plataforma, con registro versionado (`model_registry`) y trazabilidad en MLflow.

## Prerrequisitos
- Plan 03 validado (hay datos reales en `gas_readings`).
- Servidor MLflow disponible (local vía Docker Compose, ver paso 6).

## Paso a paso

### 1. Portar feature engineering (`ml_core/features/build_features.py`)
- Adaptar `FeatureBuilder` para leer desde `gas_readings` (vía SQLAlchemy o un `SELECT` a DataFrame con pandas) en vez de CSV.
- Mantener las features ya validadas: `Media_Movil` (ventana 20), `Cambio`, `Cambio_Brusco` (`Cambio > mean + 2·std`).
- Mantener la lógica de etiqueta `evento_final` (OR de: alarma, STEL, percentil alto).
**Prueba:** ejecutar `build_features(db)` sobre los datos migrados y comparar conteos de filas/etiquetas positivas contra los resultados históricos documentados (≈155k train / ≈20k test con split temporal de 3 meses).

### 2. Portar entrenamiento (`ml_core/models/train_model.py`)
- Mantener los 4 modelos actuales (LR, RF, XGBoost, LSTM opcional) y sus hiperparámetros ya calibrados.
- Registrar cada corrida en MLflow (`mlflow.start_run()`, log de params, métricas F1/recall/precision, artefacto del modelo).
- Función `train(dataset_version, params, triggered_by_user_id) -> TrainingResult` (métricas + `mlflow_run_id` + ruta del artefacto).
**Prueba:** correr `train(...)` manualmente y confirmar en la UI de MLflow que aparece la corrida con métricas ≥ los criterios del taller (recall ≥ 0.85, F1 ≥ 0.80).

### 3. Modelos de base de datos (`app/modules/ml_training/models.py`)
```
model_registry(id, name, version, algorithm, params JSONB, metrics JSONB,
               mlflow_run_id, artifact_uri, status, trained_by FK users, trained_at)
training_jobs(id, model_registry_id FK NULLABLE, status, dataset_version,
              started_at, finished_at, triggered_by FK users, params JSONB, log TEXT)
```
`status` de `model_registry`: `staging` | `production` | `archived`. Regla: **un solo modelo `production` activo por combinación sitio/gas** (o global, según alcance del taller).
**Prueba:** migración aplica; constraint o validación a nivel de servicio que impide dos modelos `production` simultáneos para el mismo alcance.

### 4. `service.py` — orquestación de entrenamiento
- `POST /ml/train` crea un `training_jobs` en estado `running`, ejecuta el pipeline (paso 1+2) — en background vía Celery si ya está disponible, o síncrono en esta fase si el dataset es manejable.
- Al terminar: inserta fila en `model_registry` con `status=staging`, actualiza `training_jobs.status=success|failed` y guarda métricas/log.
**Prueba:** disparar un entrenamiento vía API y verificar que aparece tanto en `training_jobs` como en `model_registry` con las métricas esperadas.

### 5. Endpoints (`modules/ml_training/router.py`, protegidos con `models.train` / `models.promote`)
- `POST /ml/train` — inicia entrenamiento.
- `GET /ml/jobs` — historial de entrenamientos (paginado, con estado).
- `GET /ml/models` — catálogo de modelos registrados con métricas.
- `POST /ml/models/{id}/promote` — pasa un modelo a `production` (y archiva el anterior activo del mismo alcance).
- `GET /ml/models/compare` — tabla comparativa de métricas (equivalente a la vista de comparación de Streamlit actual).
**Prueba:** flujo completo: entrenar → ver en catálogo → promover a producción → confirmar que el anterior queda `archived`.

### 6. MLflow en Docker Compose
```yaml
mlflow:
  build: { context: ., dockerfile: docker/Dockerfile.mlflow }
  command: mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root /mlartifacts --host 0.0.0.0
  ports: ["5000:5000"]
  volumes: ["mlflow_data:/mlartifacts"]
```
Mantener la restricción ya conocida del proyecto: `mlflow>=2.13,<3` (evitar MLflow 3.x por problemas de esquema).
**Prueba:** `curl localhost:5000` responde la UI de MLflow; las corridas del paso 2 son visibles ahí.

### 7. Selección del "modelo activo" para inferencia
- `service.py` de este módulo expone `get_active_model(scope)` que consulta `model_registry` por `status=production` y carga el artefacto (local o desde Cloud Storage en producción) usando `artifact_uri`.
**Prueba:** función retorna el objeto del modelo cargado y listo para `.predict()`/`.predict_proba()`.

## Checklist de validación (Definition of Done)
- [ ] Features y entrenamiento reproducen las métricas ya conocidas del proyecto (F1≈0.90, recall≈0.99 con XGBoost) sobre los datos migrados a PostgreSQL.
- [ ] Cada entrenamiento queda trazado en MLflow y en `model_registry`/`training_jobs`.
- [ ] Solo puede haber un modelo `production` activo por alcance.
- [ ] Endpoints protegidos por permisos (`models.train`, `models.promote`).
- [ ] `get_active_model()` carga correctamente el modelo marcado como producción.

**Siguiente paso:** `05_PREDICCIONES_ALERTAS_TEMPRANAS.md`.
