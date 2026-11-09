# Índice — Plataforma de Monitoreo y Predicción de Gases

> **Estado actual (código):** [`CONTEXTO_SISTEMA.md`](CONTEXTO_SISTEMA.md).  
> **Destino (reformulación jurado):** [`14_REFORMULACION_INDICE.md`](14_REFORMULACION_INDICE.md) y planes **15–20**.  
> **Auditoría científica / ajustes:** [`23_AUDITORIA_Y_AJUSTES_TESIS.md`](23_AUDITORIA_Y_AJUSTES_TESIS.md) — **prioridad** sobre 14–22 cuando haya conflicto.  
> **Identidad visual:** [`21_SISTEMA_DE_DISENO_VIGIA.md`](21_SISTEMA_DE_DISENO_VIGIA.md) + [`22_MOCKUPS_Y_GUIA_DE_IMPLEMENTACION.md`](22_MOCKUPS_Y_GUIA_DE_IMPLEMENTACION.md) (kit en `mockups/vigia-design-kit/`).  
> **Paquete documental de diseño (lo ejecuta Claude):** [`documentacion/claude/27_PAQUETE_DISENO_INDICE.md`](../documentacion/claude/27_PAQUETE_DISENO_INDICE.md) y planes **28–35** en esa carpeta. No cambian la aplicación. Producen draw.io, Word, Excel, mockups y los manuales. `planes/` queda para la arquitectura y la ejecución del sistema.  
> Ante conflicto: **Plan 25 > Plan 23 > paquete 14–22**. El Plan 25 absorbe lo pendiente de 23 y de 24. El código describe lo que hay hoy. En el paquete 27–34, si un plan viejo contradice el código, gana el código.
> Marca de trabajo en UI: **Vigía · Gases en la mina**. Alembic head: `d2e3f4a5b6c7`.

Este archivo es el mapa de ejecución. Cada plan tiene objetivo, prerrequisitos, pasos, artefactos y definición de terminado. No se salta una **compuerta**.

---

## 1. Decisiones no negociables (paquete 14–20)

1. **Solo datos reales.** Se retira el 24 meses aumentado y el clonado de meses. Ningún entrenamiento, validación ni métrica usa `is_synthetic=true`.
2. **Sin fuga.** En el instante *t* solo hay datos ≤ *t*. Percentiles, medias, σ y normalización se ajustan solo con el bloque de entrenamiento de cada partición.
3. **El sistema pronostica, luego decide.** Núcleo: pronóstico **probabilístico** de concentración a *t+k*. La alerta compara ese pronóstico con umbrales del **Decreto 1886 de 2015**. Ya no se clasifica “si la lectura actual es alta”.
4. **Dos registros de lenguaje.** Vistas operativas: lenguaje natural, cero jerga de IA. Laboratorio de modelos: métricas técnicas (analista de datos y admin).
5. **Honestidad.** Si los datos reales no alcanzan una meta del anteproyecto, se muestra y se documenta como limitación. No se inflan métricas.
6. **Edge primero.** La plataforma corre completa sin internet en bocamina (Docker). La nube (Plan 09) es sincronización asíncrona.

Objetivos reformulados (OE1–OE4), mapa jurado → plan y prompt del bucle: [`14_REFORMULACION_INDICE.md`](14_REFORMULACION_INDICE.md) §2–§6.

---

## 2. Contexto de los datos

Fuente de campo: reportes **iNet / dls_report** (Excel, hoja `Resumen`, cabecera fila **24**). En runtime la verdad es PostgreSQL (`gas_readings`); `data/` es origen y respaldo. Detalle vigente: [`CONTEXTO_SISTEMA.md`](CONTEXTO_SISTEMA.md) §5. Destino (diagnóstico, G0, ETL v2, purga): [`15_DATOS_REALES_Y_FORMULACION.md`](15_DATOS_REALES_Y_FORMULACION.md).

### 2.1 Inventario (hoy)

| Ubicación | Contenido | ¿Entra al ETL hoy? | Destino 15–20 |
|-----------|-----------|--------------------|---------------|
| `data/raw/dls_report_*.xlsx` | **56** Excel de lecturas (incluye copias `(1)`/`(2)`) | Sí (upload / inbox) | Se queda. Deduplicar por huella SHA-256 |
| `data/raw/alarmReport_*.xlsx` | **2** reportes de alarma | No (sin parser) | Sigue fuera |
| `data/raw/Historial del registro de datos.xlsx` | Bitácora de **sesiones** MX6 CO2 (no son lecturas) | No | Sigue fuera |
| `data/processed/Procesamiento_de_Datos.csv` | Consolidado **real**: ~**13.894** filas, **50** sensores, **6** gases | Sí (`--consolidado`) | **Única** carga masiva permitida |
| `data/processed/Procesamiento_de_Datos_YYYY-MM.csv` | Mismo consolidado en **9** meses | Origen del CSV único | Se queda como respaldo |
| `data/processed/Procesamiento de Datos.xlsx` | Copia Excel del consolidado | No | Se queda; el loader usa CSV |
| `data/processed/Procesamiento_de_Datos_24m.csv` | Aumentado 24 meses: ~**176.738** filas | Sí (`--augmented-24m`) | **Se retira** (Plan 15 F1) |
| `data/processed/augmentation_manifest.json` | `source_month` → `target_month` | Marca sintéticos | **Se retira** |
| `ml_core/augmentation.py` | Clonado de meses | Código | **Se retira** |
| `data/inbox/` | Cola `.xlsx/.xls` + `processed/` / `failed/` | Sí, si `ETL_INBOX_ENABLED` | Se queda; ETL v2 por etapas |
| `data/curated/` | Vacío | No | Legado |

Rango real: **2023-03-31 → 2025-12-11**. Mes más denso: 2024-11 (8.937 filas). Huecos: abr-2023–ago-2024, oct-2024, ene–jul 2025. `Sitio` suele ir vacío → el ETL crea “Sin sitio asignado”.

Gases canónicos hoy (`app/shared/gas_catalog.py`): **CH4**, CO, H2S, CO2, O2, NO2 (`LEL(CH4)` / gas combustible → CH4). Prioridad thesis: **CH4, CO, H2S**. Unidades: `%vol`, `ppm`, `%lel`. Destino: catálogo en DB `gas_types` + `normative_thresholds` (Plan 16).

Carga actual (hasta ejecutar 15 F1):

```bash
python scripts/load_processed_dataset.py --consolidado
# NO usar --augmented-24m en trabajo nuevo
```

Notebooks (`notebooks/`) generaron los CSV; **no** son runtime. Pipeline actual: `ml_core` + `sensors_ingestion`. Destino: `app/modules/ingestion/pipeline/` (etapas E1–E6).

**Compuerta G0 (decidida 2026-11-01; plantilla de visto en `docs/g0_visto_director.md`, firma del director pendiente):** Δt p50 máximo de CH₄/CO/H₂S = **5,77 min** (CH₄). Banda **medium**. Horizontes **6, 12 y 18 min**. No se sostienen 5 y 10 min del anteproyecto con este consolidado; hay que pedir el datalog crudo iNet. Detalle: `reports/diagnostico/diagnostico_datos.md`.

### 2.2 Esquema de archivo (15 columnas) → PostgreSQL hoy

Canónico: `ml_core/columns.py`.

| Columna archivo | Hoy en DB | Destino v2 |
|-----------------|-----------|------------|
| Sensor | `sensors.code` (limpia `Sensor SN:`) | + `display_name`, `kind` fijo/portátil |
| Gas | `sensors.gas_type` | FK `gas_types.code` |
| Sitio | `sites.name` | + alcance por usuario (`user_site_scopes`) |
| Leyendo | `gas_readings.leyendo` | + `value_canonical` / `unit_canonical` |
| Unidad | `unidad` | Unidad canónica por gas (E3) |
| STEL Máx / TWA máximo | `stel_max` / `twa_max` | Complemento; la decisión usa `normative_thresholds` |
| Alarma | `alarma` | Sigue como señal de instrumento, no como etiqueta de entrenamiento |
| Temperatura | `temperatura` | Covariable causal |
| Tiempo de Inicio / fin | `tiempo_inicio` / `tiempo_fin` | + `UNIQUE (sensor_id, tiempo_inicio)` |
| Descripción, Periodo, Factores | **No se persisten** | Siguen fuera; calidad en `data_quality_issues` |

---

## 3. Modelo de datos

### 3.1 Estado actual (código / Alembic head `c1d2e3f4a5b6`)

El **v2 del Plan 16** (más acceso v3 del Plan 19) **ya está en código**. Detalle de campos: [`CONTEXTO_SISTEMA.md`](CONTEXTO_SISTEMA.md) §6. La tabla `predictions` se eliminó en `b9d0e1f2a3b4`.

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
     └── alerts ── alert_notifications ── stakeholders …
            └── alert_outcomes

SALIDAS
reports · audit_log
```

| Dominio | Tablas hoy | Notas |
|---------|------------|-------|
| Identidad | users, roles, scopes, invitaciones, reset, kiosco, refresh | 6 roles Plan 19; TOTP; CSRF |
| Catálogo | `gas_types`, `normative_thresholds`, `app_settings` | Horizontes G0 6/12/18; umbrales `verified=false` |
| Ingesta | sites, sensors, etl_runs/steps, gas_readings, quality | CHECK `is_synthetic=false` |
| Rejilla / eventos | `reading_grid`, `threshold_events` | Entrada de modelos y verdad de referencia |
| ML | `model_registry`, `model_evaluations`, `training_jobs` | Zoo Plan 17 |
| Pronóstico | `forecasts`, `forecast_quantiles`, `forecast_explanations` | Reemplaza `predictions` |
| Alertas | `alerts`, `alert_outcomes`, notificaciones | anticipado / confirmado |
| Salidas | `reports`, `audit_log` | PDF/Excel |

Flujo actual: **Excel/CSV → E1–E6 → `gas_readings` / `reading_grid` → `forecasts` (cuantiles) → decisión normativa → `alerts`**.

---

## 4. Orden de ejecución vigente (paquete 14–20)

```
15 F0 Diagnóstico ──► COMPUERTA G0 (horizonte posible con estos datos)
        │
15 F1–F6 Datos reales + ETL v2 ──► 16 Modelo de datos v2 (migraciones)
        │
17 Modelos (baselines → transformers → decisión → explicación)
        │
19 Usuarios y acceso ──► 18 UX/UI lenguaje natural (consume 16, 17, 19)
        │
21–22 Identidad Vigía (tokens, mockups) ──► cascarón en `app/`
        │
20 Pruebas + bucle de calidad (al final de CADA plan, no solo al cierre)
```

| # | Archivo | Qué entrega | Tesis / jurado |
|---|---------|-------------|----------------|
| 14 | `14_REFORMULACION_INDICE.md` | Mapa, objetivos, prompt del bucle | Coherencia (obs. 4) |
| 15 | `15_DATOS_REALES_Y_FORMULACION.md` | Diagnóstico, G0, purga sintéticos, ETL v2, formulación, walk-forward | OE1, OE2 · 2A, 2B, 6 |
| 16 | `16_MODELO_DE_DATOS_V2.md` | Migraciones: catálogo, rejilla, forecasts, umbrales, outcomes | OE2–OE4 |
| 17 | `17_MODELOS_TRANSFORMER_Y_EVALUACION.md` | Pronóstico probabilístico transformer vs referencias | OE3 · 2A–2D, 6 |
| 18 | `18_UX_UI_LENGUAJE_NATURAL.md` | Pantallas ES, copy, contraste; se completa con 21–22 | OE4 · 2D |
| 19 | `19_USUARIOS_ROLES_Y_ACCESO.md` | Roles, sitios, invitaciones, kiosco, CSRF | OE4 |
| 20 | `20_PRUEBAS_Y_BUCLE_DE_CALIDAD.md` | `scripts/verify.py`, cobertura, lint de lenguaje | Transversal |
| 21 | `21_SISTEMA_DE_DISENO_VIGIA.md` | Tokens, tipografía Archivo, riel, ilustraciones SVG | OE4 · identidad |
| 22 | `22_MOCKUPS_Y_GUIA_DE_IMPLEMENTACION.md` | Mockups → Jinja2, macros, CSP self-only | OE4 · implementación |
| 23 | `23_AUDITORIA_Y_AJUSTES_TESIS.md` | Gráficas, umbrales decreto, experimento real, ver la IA, retirar legado | Núcleo científico + OE3 |
| 24 | `24_OPERACION_CON_DATOS_REALES.md` | Cero demo; instrumentos; replay histórico; linaje | OE1–OE4 · operación |
| 09 | `09_DESPLIEGUE_GCP_CICD.md` | Edge local + sync asíncrona (ajustar alcance) | 3A, 3B |
| 10 | `10_SEGURIDAD_TESTING_HARDENING.md` | Hardening; tramo login/CSP ya en código | — |

- No saltar **G0**. Cada plan cierra con `python scripts/verify.py --plan <NN>` en verde (Plan 20).
- Commits: `feat(<módulo>): <plan>.<fase>.<paso> <descripción>`.

### Qué se retira (cuando toque el plan)

| Se retira | Reemplazo |
|-----------|-----------|
| Dataset 24m, `--augmented-24m`, `augmentation.py` | Solo reales; fundacionales si hay escasez |
| Etiqueta `evento_final` (alarma / STEL / p95 en *t*) | Evento de inicio en [t+k₁, t+k₂] con umbral normativo |
| Rasgos con estadística global del sensor | Ventanas causales; stats solo de train |
| SVM, árbol simple, GRU, Transformer vanilla, CNN1D, MLP sklearn | Zoo del Plan 17 |
| `P ≈ \|c\|/(\|c\|+1)` | Probabilidad de superar umbral vía cuantiles |
| `lead_time_minutes_mean = 7.5` constante | Anticipación medida por evento |
| Preferencia fija por modelos sequence en inferencia | Selección por métricas (Plan 17) |
| Tabla `predictions` | `forecasts` + `forecast_quantiles` |
| Inter, Chart.js, Bootstrap, CDN | Vigía: Archivo + Plex Mono local, ECharts local, sprite Lucide (Planes 18 + 21–22) |
| Login con clave en URL / JS inline | POST `/ingresar` + CSRF + scripts estáticos (Plan 10 tramo auth + CSP) |

---

## 5. Base ya construida (planes 01–13 — historial)

Vigentes como cimiento: **01, 02, 03, 06, 08**.  
Supersedidos en lo que contradigan al paquete 14–20: **04, 05, 07, 11, 12, 13**.  
Pendientes de alinear: **09, 10**.

| # | Archivo | Fase | Entregó | Estado |
|---|---------|------|---------|--------|
| 1 | `01_INFRAESTRUCTURA_BASE.md` | F0 | Esqueleto, Compose, PostgreSQL, Alembic | ✅ 2026-09-20 |
| 2 | `02_AUTENTICACION_USUARIOS_ROLES_PERMISOS.md` | F1 | Login JWT, CRUD, RBAC | ✅ 2026-09-20 · se extiende en 19 |
| 3 | `03_INGESTA_ETL_SENSORES.md` | F2 | Excel/CSV → `etl_runs` | ✅ 2026-09-20 · se sustituye por ETL v2 (15) |
| 4 | `04_ML_ENTRENAMIENTO_MODELOS.md` | F3 | `ml_core` + `model_registry` + MLflow | ✅ historial · destino 17 |
| 5 | `05_PREDICCIONES_ALERTAS_TEMPRANAS.md` | F4 | Inferencia + `alerts` | ✅ historial · destino 16–17 |
| 6 | `06_STAKEHOLDERS_NOTIFICACIONES.md` | F5 | Interesados, suscripciones, notificaciones | ✅ vigente |
| 7 | `07_DASHBOARD_UI.md` | F6 | Jinja2 + Bootstrap + semáforo | ✅ historial · destino 18 |
| 8 | `08_REPORTES.md` | F7 | PDF/Excel | ✅ vigente (textos → lenguaje natural en 18) |
| 9 | `09_DESPLIEGUE_GCP_CICD.md` | F8 | Cloud Run, Cloud SQL, GCS, CI/CD | ⬜ ajustar (edge-first) |
| 10 | `10_SEGURIDAD_TESTING_HARDENING.md` | F9 | Rate limit, hardening, carga | ⬜ se alinea con 19–20 |
| 11 | `11_UX_UI_MAPEO_PANTALLAS.md` | F6 | Mapeo de pantallas | ✅ historial · destino 18 |
| 12 | `12_MODEL_ZOO_SERIES_METRICAS_UI.md` | F3/F4 | Zoo tabular+DL, gates thesis | ✅ historial · destino 17 |
| 13 | `13_MVP_FORECAST_HOME_UX.md` | — | Forecast home Chart.js | ✅ historial · destino 17–18 |

`PLAN_EJECUCION_03_INGESTA_ETL.md` es playbook histórico del Plan 03; no es un plan extra.

---

## 6. Reglas de trabajo

1. **No saltar compuertas.** G0 bloquea horizontes y todo lo de abajo.
2. **Migraciones solo con Alembic**, con `downgrade` (Plan 16 / 20).
3. Módulos en `app/modules/<nombre>/` (`models`, `schemas`, `repository` si hay persistencia, `service`, `router`).
4. Commits: `feat(<módulo>): <plan>.<fase>.<paso> <descripción>`.
5. Secretos solo por env / Secret Manager.
6. Cada paso cierra con `python scripts/verify.py --plan <NN>`. Bitácora: `planes/BITACORA_BUCLE.md`.
7. Nada de datos sintéticos en trabajo nuevo; nada de estadística global en rasgos; vistas operativas en lenguaje natural.
8. Al cerrar un plan: actualizar [`CONTEXTO_SISTEMA.md`](CONTEXTO_SISTEMA.md) y la tabla de estado de abajo.

Prompt maestro del bucle: [`14_REFORMULACION_INDICE.md`](14_REFORMULACION_INDICE.md) §6.

### Mapa de módulos (hoy → destino)

```
hoy:     sensors_ingestion → ml_training → predictions → alerts → dashboard/reports
destino: ingestion (E1–E6) → forecasting (Plan 17) → forecasts/decision → alerts → UI 18
```

---

## 7. Estado (actualizar a mano)

Separar **código** (implementado), **experimento** (corrida real / datos) y **validación humana**. Un ✅ solo en código **no** autoriza citar métricas en la tesis.

### Paquete de reformulación (vigente)

| Plan | Código | Experimento | Validación humana | Fecha |
|------|--------|-------------|-------------------|-------|
| 14 Reformulación índice | ✅ Documento | — | — | 2026-11-01 |
| 15 Datos reales y formulación | ✅ F0–F6; G0 6/12/18 | ⚠️ G0 desde CSV, no DB; falta longitud de segmentos (Plan 23 F1) | ⬜ visto del director | 2026-11-01 |
| 16 Modelo de datos v2 | ✅ M1–M9 + `c1d2e3f4a5b6` | — | — | 2026-11-01 |
| 17 Modelos transformer | ✅ Zoo + conformal + decisión | ⬜ **benchmark con modelos reales no corrido** | — | 2026-11-01 |
| 18 UX/UI lenguaje natural | ✅ Pantallas ES, copy, contraste | — | ⬜ co-diseño / SUS | 2026-11-01 |
| 19 Usuarios, roles y acceso | ✅ Roles v2, CSRF, TOTP, kiosco | — | — | 2026-11-01 |
| 20 Pruebas y bucle | ✅ DB test, verify, E2E | — | ⬜ sesiones SUS en mina | 2026-11-01 |
| 21 Sistema de diseño Vigía | ✅ Tokens + doc | — | — | 2026-11-02 |
| 22 Mockups e implementación | ✅ Kit en `app/` | — | ⬜ revisión captura a captura | 2026-11-02 |
| Login seguro (tramo Plan 10) | ✅ POST `/ingresar`, CSRF ASGI | — | — | 2026-11-02 |
| **23** Auditoría y ajustes tesis | 🔄 F7+F5 código; faltan F1→F2→F3→F8→F4/F6 | ⬜ | ⬜ | 2026-11-02 |
| **24** Operación con datos reales | 🔄 F1 limpia (audit/purge); faltan F2–F8 | ⬜ | ⬜ | 2026-11-02 |
| 09 Despliegue (edge-first) | ⬜ | — | — | |
| 10 Seguridad / hardening (resto) | ⬜ k6, pip-audit, HSTS prod, backups | — | — | |

> Ningún resultado de `reports/thesis/` se cita en la tesis hasta cerrar Plan 23 F3.
