# Bitácora del bucle

## 2026-11-01 · Plan 15 · F0 · Diagnóstico y compuerta G0
- Archivos: `ml_core/diagnosis.py`, `scripts/diagnose_real_data.py`, `tests/unit/test_diagnose.py`, `reports/diagnostico/*`
- verify: ✅ `python scripts/verify.py --plan 15` (19 pruebas)
- Evidencia G0 (consolidado real, 13.894 filas):
  - Δt p50 CH₄ **5,77 min**, CO 2,54, H₂S 1,00 → se toma el máximo de prioritarios → banda **medium**
  - Horizontes: **6, 12 y 18 min** (1, 2 y 3 pasos). **No** se prometen 5 y 10 min del anteproyecto.
  - Acción: solicitar al proveedor el *datalog* crudo iNet por intervalo.
  - Episodios de inicio (umbrales `verified=false`): H₂S vigilar 59 (bootstrap); O₂ vigilar 53; CH₄ todos los niveles ≤1 (no métricas por evento); CO vigilar 7 (no métricas por evento).
- Decisiones: LIE CH₄ = 5,0 % vol; umbrales semilla Decreto 1886 sin verificar artículo.
- Pendiente humano: visto del director sobre G0 (Plan 15 F0 paso 3). Postgres no respondió en esta sesión: el diagnóstico se hizo desde CSV.

## 2026-11-01 · Plan 15 · F1 · Solo datos reales
- Archivos: `scripts/purge_synthetic.py`, `scripts/load_processed_dataset.py`, `ml_core/data/loader.py`, retiro de `ml_core/augmentation.py` → `legacy/`
- verify: ✅ guardia `test_no_synthetic_in_training`
- Decisiones: `--augmented-24m` eliminado. El CSV 24m puede seguir en `data/processed` pero el loader lo rechaza.
- Pendiente: correr `purge_synthetic.py --confirm` cuando Postgres esté arriba; UNIQUE (sensor, tiempo) en Plan 16.

## 2026-11-01 · Plan 15 · F2 · ETL v2 E1–E6
- Archivos: `app/modules/ingestion/pipeline/*`, `docs/etl/transformaciones.md`, `tests/unit/test_etl_pipeline.py`
- verify: ✅ conversión %LEL→%vol (10% LEL = 0,5 %vol); rejilla no inventa huecos largos
- Pendiente: tablas `etl_run_steps`, `data_quality_issues`, `reading_grid` (Plan 16). E5 ya persiste en `gas_readings` con SHA-256.

## 2026-11-01 · Plan 15 · F3–F5 · ProblemSpec, umbrales, walk-forward
- Archivos: `ml_core/forecasting/problem.py`, `ml_core/domain/*`, `ml_core/validation/walk_forward.py`, `scripts/seed_thresholds.py`
- verify: ✅ `test_walk_forward_no_overlap`, `test_no_shuffle_splitters`, `test_threshold_direction_below`, `test_events_are_onsets`
- Decisiones: umbrales viven en JSON (`reports/diagnostico/normative_thresholds_seed.json`) hasta `normative_thresholds` del Plan 16. `ProblemSpec.from_g0` lee horizontes 6/12/18.
- Pendiente: pantalla “Calidad de los datos” (Plan 18 F6).

## 2026-11-01 · Plan 16 · Modelo de datos v2
- Migraciones M1–M9: `b1c2d3e4f5a6` … `b9d0e1f2a3b4` (head). `predictions` se elimina en M9.
- Archivos: `app/modules/catalog/*`, `app/modules/forecasting/*`, ORM extendido en sensors/alerts/users/ml_training, `scripts/seed_catalog.py`, `scripts/rebuild_grid.py`, `scripts/rebuild_events.py`.
- Runtime: avisos por alarma dura (`kind=confirmado`); `/api/forecasts` sustituye `/api/predictions`. Inferencia ML queda para el Plan 17.
- Semillas: horizontes `[6,12,18]`, `grid_step_minutes=6` (G0). Umbrales `verified=false`.
- verify: `python scripts/verify.py --plan 16`
- Pendiente: `alembic upgrade head` y `seed_catalog` cuando Postgres en 5433 esté arriba; roundtrip upgrade/downgrade en Plan 20.

## 2026-11-01 · Plan 17 · Zoo transformer, decisión y evaluación
- Interfaz `Forecaster` + 10 adaptadores (`persistencia` … `ttm`). neuralforecast/chronos/timesfm opcionales: si no están, backend `torch-lite` o `fallback-conformal` documentado.
- Conformal propio (intervalo 90 %), decisión con persistencia/histéresis, avisos confirmados sin modelo, narrador con plantillas (sin LLM).
- `select_production_model()` lexicográfico; sin preferencia por familia. Promoción sigue siendo explícita.
- Inferencia: `ml_core/forecasting/serve.py` + job `app/modules/forecasting/cycle.py`.
- `python -m ml_core.experiments.run_benchmark` y `thesis_report` → `reports/thesis/`.
- verify: `python scripts/verify.py --plan 17`
- Pendiente: instalar `requirements-ml.txt` y pesos fundacionales en la imagen; benchmark completo sobre DB migrada; G0 sigue limitando horizontes a 6/12/18.

## 2026-11-01 · Plan 18 · UX/UI en lenguaje natural
- Stack: tokens CSS propios, IBM Plex Sans/Mono, Apache ECharts, Lucide, htmx. Se retiran Bootstrap, Chart.js, Inter y `theme.css`.
- `app/shared/copy.py` es la fuente de textos operativos; verificador de lenguaje y contraste AA (≥ 4,5:1) en pruebas `plan18`.
- Rutas en español (`/avisos`, `/zonas`, `/ingresar`, `/laboratorio`, `/sala`…) con 301 desde las rutas viejas. Sala de control en modo oscuro (kiosco autenticado hasta Plan 19).
- Macros en `templates/components/macros.html`; catálogo vivo `/_componentes` (solo `ENVIRONMENT=local`).
- verify: ✅ `python scripts/verify.py --plan 18` (10 pruebas)
- Pendiente humano: sesión de co-diseño con operadores (`docs/ux/codiseno.md`); capturas de regresión visual y axe completo (Plan 20); kiosco de dispositivo en Plan 19.

## 2026-11-01 · Plan 19 · Usuarios, roles y acceso
- Seis roles en español (`admin`, `supervisor_seguridad`, `operador`, `gerencia`, `analista`, `auditor`) con matriz celda a celda y alcance por zona (`scoped_site_ids`). Un operador sin zonas no ve nada.
- Login `/ingresar`: bloqueo 5/15 min, CSRF double-submit, JWT 15 min / refresh 8 h con rotación y reutilización, contraseñas NIST 12+ (`common_passwords.txt`).
- Invitación 72 h, recuperación 30 min, cambio forzado, TOTP + códigos de respaldo, outbox `storage/outbox/` si no hay SMTP.
- Kiosco `/sala?kiosk=` con token hasheado y revocación inmediata. Equipo `/equipo`, pantallas `/pantallas`, Mi cuenta con sesiones.
- Migración Alembic `c1d2e3f4a5b6`. Seed/migración de roles: `scripts/seed_roles_permissions.py`, `scripts/migrate_roles_v2.py`.
- verify: ✅ `python scripts/verify.py --plan 19` (118 pruebas)
- Pendiente: G0 visto del director; `purge_synthetic.py --confirm`; Plan 20.

## 2026-11-01 · Plan 20 · Pruebas y bucle de calidad
- DB aislada `proyecto_gases_test` (`TEST_DATABASE_URL`). `conftest` aborta si coincide con desarrollo. Rollback por SAVEPOINT. Fábricas en `tests/factories.py`. Muestra real `tests/fixtures/real_sample.csv`.
- `scripts/verify.py` con 13 etapas; `--plan`, `--fast` (1, 4, 7) y `--full`. `Makefile` y `.github/workflows/verify.yml`.
- Guardias nuevas: rasgos causales, scaler solo-train, prueba final intocable; sintéticos también se checan en DB.
- Lenguaje en HTML renderizado (`tests/ui/`). E2E/axe/visual sobre pantallas clave (Playwright opcional). Rendimiento: persistencia < 1 s y p95 de `/`.
- Aceptación SUS documentada en `docs/ux/aceptacion.md` (campo con usuarios reales pendiente).
- verify: `python scripts/verify.py --plan 20` → 41 passed, 1 skipped (Playwright). `--fast` OK. `--full` OK (13 etapas): unitarias 179; integración 36 passed / 1 skipped; cobertura 97,68 % en decision/validation/access; `alembic check` sin operaciones pendientes.
- Pendiente humano: 3–5 sesiones de aceptación en mina (SUS); G0 visto del director.
- 2026-11-01 noche: `seed_catalog` en DEV (6 gases, 12 umbrales, ajustes G0). `rebuild_grid --persist` → 114 111 filas en `reading_grid`. Smoke HTML admin: `/health`, `/ingresar` y P2–P17 en 200.

## 2026-11-01 · Cierre operativo (contenedores, login, Playwright)

- Compose: `plataforma-gases-app-1` **healthy** `:8000`, `db` **healthy** `:5433`, `mlflow` Up `:5000`.
- `GET /login` → 301 `/ingresar`. Login `test.admin@example.com` entra a **Hoy** (banner «2 zonas requieren atención», horizontes 6 min).
- Playwright 1.64.1 + Chromium 156 instalados en `.venv`. E2E: `tests/e2e/test_login_playwright.py` y `tests/e2e/test_aceptacion_tareas.py` (contra `E2E_BASE_URL`, skip si la app no responde).
- Ensayo técnico de las 5 tareas de `docs/ux/aceptacion.md` (no SUS). Plantilla de firma G0: `docs/g0_visto_director.md` (vacía a propósito).
- Pendiente humano (no se puede firmar aquí): 3–5 sesiones reales en mina + visto del director en G0.

## 2026-11-02 · Login seguro + identidad Vigía (Planes 10 tramo auth, 18, 21–22)

- **Causa del fallo de login:** CSP `script-src 'self'` bloqueaba el JS inline; el form hacía GET y dejaba `password=` en la URL. `POST /ingresar` solo re-pintaba.
- **Auth:** `POST /ingresar` autentica (cookies HttpOnly); GET con query hace 302 limpio; CSRF en plantilla + middleware ASGI (no consume el body); auth pages con `Referrer-Policy: no-referrer` y `Cache-Control: no-store`; `login.js` estático; scripts de páginas en `app/static/js/pages/`.
- **Vigía:** tokens del kit → `app/static/css/tokens.css`; Archivo + Plex Mono locales; sprite Lucide; ECharts/htmx en `vendor/`; ilustraciones SVG; riel antracita; marca **Vigía · Gases en la mina**; CSP sin CDN.
- Docs: `planes/21_*.md`, `planes/22_*.md`; reglas `.cursor/rules/vigia-*.mdc`; kit en `mockups/vigia-design-kit/`.
- verify: ✅ `--plan 18`, `--plan 19`. E2E login + aceptación: 8 passed.
- Pendiente UI: corte esquemático de mina en Hoy; revisión visual vs `screenshots/`. Pendiente humano: SUS + G0 director.
