# Índice — Plataforma de Monitoreo y Predicción de Gases (Monolito FastAPI)

> **Contexto canónico del sistema (todo en un solo lugar):** [`CONTEXTO_SISTEMA.md`](CONTEXTO_SISTEMA.md) — arquitectura, modelo de datos, flujos, rutas, roles, UX/UI y arranque local. Usar ese archivo como fuente de verdad para agentes y onboarding; este índice solo ordena los planes de ejecución.

> Los planes numerados son la bitácora de implementación en **fases secuenciales**. Cada plan tiene: objetivo, prerrequisitos, pasos numerados, artefactos a crear/editar, y un checklist de validación ("Definition of Done") antes de pasar al siguiente.

## Orden de ejecución

| # | Archivo | Fase | Qué entrega |
|---|---------|------|-------------|
| 1 | `01_INFRAESTRUCTURA_BASE.md` | F0 | Esqueleto del proyecto, Docker Compose, PostgreSQL, Alembic, configuración |
| 2 | `02_AUTENTICACION_USUARIOS_ROLES_PERMISOS.md` | F1 | Login/JWT, CRUD usuarios, RBAC (roles y permisos) |
| 3 | `03_INGESTA_ETL_SENSORES.md` | F2 | Carga de Excel/CSV a PostgreSQL, tabla `etl_runs`, trazabilidad |
| 4 | `04_ML_ENTRENAMIENTO_MODELOS.md` | F3 | Integración de `ml_core` (features + entrenamiento) con `model_registry` + MLflow |
| 5 | `05_PREDICCIONES_ALERTAS_TEMPRANAS.md` | F4 | Inferencia automática, motor de reglas, tabla `alerts` |
| 6 | `06_STAKEHOLDERS_NOTIFICACIONES.md` | F5 | Registro de partes interesadas, suscripciones, envío de notificaciones |
| 7 | `07_DASHBOARD_UI.md` | F6 | Vistas Jinja2 + Bootstrap5 por rol, gráficos, semáforo en tiempo real |
| 8 | `08_REPORTES.md` | F7 | Generación y descarga de reportes PDF/Excel |
| 9 | `09_DESPLIEGUE_GCP_CICD.md` | F8 | Cloud Run, Cloud SQL, Cloud Storage, Scheduler, CI/CD |
| 10 | `10_SEGURIDAD_TESTING_HARDENING.md` | F9 | Rate limiting, hardening, pruebas de carga, auditoría de seguridad |
| 11 | `11_UX_UI_MAPEO_PANTALLAS.md` | Complementa F6 | Mapeo de pantallas, navegación por rol, wireframes y flujos de usuario |
| 12 | `12_MODEL_ZOO_SERIES_METRICAS_UI.md` | Extiende F3/F4/F6 | Model Zoo tabular+DL, pipeline 2D/3D, métricas thesis, UI comparativa |
| 13 | `13_MVP_FORECAST_HOME_UX.md` | Cierra gap thesis | Forecast operativo 5–10 min, home Chart.js por gas, catálogo nombres, MVP UX |

## Reglas generales para todos los planes

1. **No saltar fases.** Cada plan asume que el checklist de validación del anterior quedó en verde.
2. **Migraciones siempre vía Alembic.** Nunca `Base.metadata.create_all()` en entornos compartidos.
3. **Cada módulo nuevo** vive en `app/modules/<nombre>/` con `router.py`, `service.py`, `repository.py`, `models.py`, `schemas.py` (ver `01_INFRAESTRUCTURA_BASE.md`, sección de convenciones).
4. **Nomenclatura de commits sugerida:** `feat(<módulo>): <paso realizado>`, para poder rastrear qué paso de qué plan corresponde a qué commit.
5. **Variables sensibles** (passwords, JWT secret, credenciales GCP) siempre por variable de entorno / Secret Manager, nunca en el código ni en estos documentos.
6. **Cada plan termina con pruebas manuales y/o automáticas concretas** — no se considera "hecho" un paso hasta que su prueba pasa.

## Mapa de dependencias entre módulos

```
core (config, db, security)
  └── auth ──────────────┐
  └── users/roles ────────┼── requeridos por TODOS los módulos siguientes (permisos)
  └── sensors_ingestion ──┼── requerido por ml_training y predictions
  └── ml_training ────────┼── requerido por predictions
  └── predictions ────────┼── requerido por alerts
  └── alerts ─────────────┼── requerido por stakeholders (notificaciones) y dashboard
  └── stakeholders ───────┤
  └── dashboard ──────────┤ (consume todo lo anterior, no expone lógica de negocio propia)
  └── reports ────────────┘ (consume alerts, predictions, ml_training)
```

## Estado del proyecto (actualizar manualmente)

| Plan | Estado | Fecha |
|------|--------|-------|
| 01 Infraestructura base | ✅ Completado | 2026-09-20 |
| 02 Auth/Usuarios/Roles | ✅ Completado | 2026-09-20 |
| 03 Ingesta/ETL | ✅ Completado | 2026-09-20 |
| 04 ML/Entrenamiento | ✅ Completado | 2026-09-20 |
| 05 Predicciones/Alertas | ✅ Completado | 2026-09-20 |
| 06 Stakeholders | ✅ Completado | 2026-09-20 |
| 07 Dashboard | ✅ Completado | 2026-09-20 |
| 08 Reportes | ✅ Completado | 2026-09-20 |
| 09 Despliegue GCP | ⬜ Pendiente | |
| 10 Seguridad/Testing | ⬜ Pendiente | |
| 11 UX/UI (mapeo pantallas) | ✅ Completado | 2026-09-20 |
| 12 Model Zoo / series / métricas UI | ✅ Completado | 2026-09-21 |
| 13 MVP forecast home + UX | ✅ Completado | 2026-09-21 |
