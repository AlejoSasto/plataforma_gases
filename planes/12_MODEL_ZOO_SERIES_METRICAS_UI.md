# Plan 12 — Model Zoo, series temporales, métricas thesis y UI profesional

> Extiende y supersede parcialmente el Plan 04. Implementa la **matriz unificada de modelos predictivos** de la tesis (tabulares + deep learning), pipeline dual 2D/3D, métricas con umbrales, UI de comparación/descarga e inferencia unificada.

## Objetivo

Pasar de 3 clasificadores tabulares (LR/RF/XGBoost) a un **Model Zoo completo** con:

- Tabulares: `decision_tree`, `random_forest`, `xgboost`, `svm`, `mlp` (+ `logistic_regression` baseline)
- Secuencias (PyTorch): `lstm`, `gru`, `transformer`, `cnn1d`
- Tareas: clasificación de riesgo + regresión de concentración a horizonte 5–10 min
- Métricas: Recall≥0.95, Precisión≥0.90, F1≥0.92, RMSE≤0.05, FN≤0.05, lead time 5–10 min
- UI: matriz con gates thesis, selector de algoritmos, reportes comparativos descargables

## Prerrequisitos

- Planes 01–08 y 11 validados (hay datos, auth, UI base, reportes).
- MLflow local disponible.
- `torch` instalado (CPU).

## Fases y Definition of Done

### Fase 1 — Data Engine
- [x] `build_features` (2D) y `build_sequences` (3D) desde `gas_readings`
- [x] Targets `y_reg` (t+h) y `y_alert_lead`
- [x] Config `ML_*` / `THESIS_*` en settings + `.env.example`
- [x] Tests de shapes / horizon

### Fase 2 — Model Zoo
- [x] Catálogo en `ml_core/models/registry.py`
- [x] Train tabular + sequence con selección `algorithms[]` y `task`
- [x] Artefactos MLflow (+ `.pt` para DL)
- [x] Registro en `model_registry` con metrics enriquecidas
- [x] Promote por `(scope, task)`

### Fase 3 — Métricas
- [x] `ml_core/models/metrics.py` con gates thesis
- [x] Reporte `comparativa_modelos` PDF/Excel

### Fase 4 — UI + docs
- [x] `/ml/models` matriz unificada + filtros
- [x] `/ml/train` selector multi-algoritmo
- [x] `/ml/compare` + descargas
- [x] `CONTEXTO_SISTEMA.md` / README actualizados

## Umbrales thesis (defaults)

| Métrica | Umbral |
|---------|--------|
| Recall | ≥ 0.95 |
| Precisión | ≥ 0.90 |
| F1 | ≥ 0.92 |
| FN rate | ≤ 0.05 |
| RMSE | ≤ 0.05 |
| Lead time | 5–10 min |

## Fuera de alcance

Planes 09 (GCP) y 10 (hardening), salvo deps locales.
