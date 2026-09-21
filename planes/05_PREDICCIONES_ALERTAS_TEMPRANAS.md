# Plan 05 — Predicciones y Alertas Tempranas (F4)

> **Actualizado con Plan 12:** la inferencia debe cargar artefactos **sklearn/XGBoost o PyTorch** según `params.framework` / familia del modelo `production`, y puede usar ventanas secuenciales (lookback) además del vector tabular 2D. La métrica de **alerta anticipada (5–10 min)** se calcula en entrenamiento (`lead_time_*`) y se refleja en la UI de modelos.

## Objetivo
Ejecutar inferencia automática sobre cada nueva lectura ingresada y convertir resultados de riesgo en alertas persistentes, trazables y accionables (con recomendación), cumpliendo el objetivo 3 (detección temprana) y parte del objetivo 4 (alertas).

## Prerrequisitos
- Plan 03 (datos) y Plan 04 (modelo `production` disponible) validados.

## Paso a paso

### 1. Modelos (`app/modules/predictions/models.py`, `app/modules/alerts/models.py`)
```
predictions(id, gas_reading_id FK, model_registry_id FK, probability,
            predicted_label, risk_level, created_at)
alerts(id, prediction_id FK NULLABLE, gas_reading_id FK NULLABLE, sensor_id FK,
       level, message, recommendation, status, created_at,
       acknowledged_by FK users NULLABLE, acknowledged_at, resolved_at)
```
`risk_level` / `level`: `NORMAL`, `PRECAUCION`, `ALERTA`, `CRITICO`. `status` de alerta: `abierta`, `reconocida`, `resuelta`.
**Prueba:** migración aplica; índice en `alerts(status, created_at)`.

### 2. `predictions/service.py` — inferencia
- `predict_for_reading(db, gas_reading) -> Prediction`: construye el vector de features para esa lectura (reutilizando `ml_core/features`), llama a `get_active_model(scope)` (Plan 04) y calcula `probability` + `predicted_label`.
- Mapear probabilidad a `risk_level` con umbrales configurables (ej. `<0.3` NORMAL, `0.3–0.6` PRECAUCIÓN, `0.6–0.85` ALERTA, `>0.85` CRÍTICO) — documentar los umbrales en config, no hardcodeados en el código.
**Prueba:** unit test con lecturas sintéticas de cada rango confirma el `risk_level` esperado.

### 3. Disparo automático tras ETL
- En `sensors_ingestion/service.py` (Plan 03), al finalizar un `etl_run` exitoso, invocar `predictions.service.predict_for_reading` para cada fila nueva real (no sintética) — en background si el volumen es grande.
**Prueba:** subir un archivo con al menos una lectura que supere alarma/STEL y verificar que se genera una fila en `predictions` inmediatamente después del ETL.

### 4. `alerts/rules.py` — motor de reglas
- Combina señales duras (alarma=true, STEL/TWA superado) con la salida del modelo (`risk_level`).
- Regla mínima: si `risk_level` ∈ {ALERTA, CRÍTICO} **o** hay alarma dura → crear alerta.
- Generar `recommendation` con reglas simples por tipo de gas (ej. CO alto → "Verificar ventilación y fuentes de combustión"; O2 bajo → "Evacuar zona, revisar suministro de aire"). Mantener esto como tabla/config editable, no si-elif gigante.
**Prueba:** casos de prueba por gas (CO, CO2, NO2, H2S, LEL, O2) generan la recomendación esperada.

### 5. `alerts/service.py`
- `evaluate_and_create_alert(db, prediction, gas_reading) -> Alert | None`.
- `acknowledge_alert(db, alert_id, user)` → `status=reconocida`, guarda `acknowledged_by/at`.
- `resolve_alert(db, alert_id, user, resolution_note)` → `status=resuelta`, guarda `resolved_at`; registra en `audit_log`.
**Prueba:** ciclo completo abierta → reconocida → resuelta, con auditoría en cada transición.

### 6. Endpoints (`modules/alerts/router.py`)
- `GET /alerts` (filtros: estado, nivel, sitio, rango de fechas; protegido con `alerts.view`).
- `POST /alerts/{id}/acknowledge` (protegido con `alerts.resolve`).
- `POST /alerts/{id}/resolve` (protegido con `alerts.resolve`).
- `GET /alerts/{id}` — detalle con lectura, predicción y recomendación asociadas.
**Prueba:** un usuario `operador_mina` puede reconocer/resolver; un `interesado` solo puede ver (403 al intentar resolver).

### 7. Endpoints de predicciones (`modules/predictions/router.py`, `predictions.view`)
- `GET /predictions` (histórico, filtros por sensor/sitio/fecha).
- `GET /predictions/{id}`.
**Prueba:** filtrar predicciones de un sensor específico devuelve solo las suyas.

## Checklist de validación (Definition of Done)
- [ ] Toda lectura real nueva genera una predicción automáticamente tras el ETL.
- [ ] Los umbrales de riesgo están centralizados en configuración, no hardcodeados.
- [ ] Se generan alertas con nivel y recomendación coherente por tipo de gas.
- [ ] El ciclo de vida de una alerta (abierta/reconocida/resuelta) queda completamente auditado.
- [ ] Permisos diferenciados entre "ver" y "resolver" alertas funcionan correctamente.

**Siguiente paso:** `06_STAKEHOLDERS_NOTIFICACIONES.md`.
