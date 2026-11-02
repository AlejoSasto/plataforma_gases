# 20 — Pruebas, verificación y bucle de calidad

**Alcance:** transversal. Se implementa **primero la infraestructura de verificación** (F1–F2), antes de tocar los planes 15–19, y luego cada plan agrega sus pruebas.
**Definición de “perfecto”:** `python scripts/verify.py --full` termina en verde, sin pruebas desactivadas, y la “Definición de terminado” de cada plan está marcada con evidencia en la bitácora.

---

## F1 — Base de pruebas aislada (corrige el problema actual)

Hoy las pruebas escriben en la DB de desarrollo. Se cambia a:

1. Variable `TEST_DATABASE_URL` → base `proyecto_gases_test` (Compose crea las dos con un script de inicio).
2. `tests/conftest.py`:
   - al iniciar la sesión de pytest: `alembic upgrade head` sobre la DB de pruebas más las semillas (roles, gases, umbrales, ajustes);
   - por prueba: **transacción con rollback** (conexión anidada con `SAVEPOINT`), así ninguna prueba deja datos;
   - fábricas (`tests/factories.py`) para usuarios por rol, zonas, sensores, lecturas reales mínimas, eventos, pronósticos y avisos.
3. Datos de prueba: `tests/fixtures/real_sample.csv`, una **muestra real** pequeña extraída del consolidado (anonimizada si hace falta), más series simuladas solo para pruebas matemáticas (cobertura, purga).
4. Prohibido apuntar las pruebas a `DATABASE_URL`: `conftest` aborta si las dos URL coinciden.

## F2 — Verificador único `scripts/verify.py`

Un solo comando con salida legible y código de salida distinto de 0 si algo falla. También expuesto como `make verify`.

| Etapa | Herramienta | Criterio |
|-------|-------------|----------|
| 1. Formato y estilo | `ruff format --check`, `ruff check` | 0 errores |
| 2. Tipos (módulos nuevos) | `mypy` sobre `ml_core/forecasting`, `ml_core/validation`, `app/modules/access`, `app/modules/forecasting` | 0 errores |
| 3. Migraciones | `upgrade head → downgrade base → upgrade head` en la DB de pruebas | Sin errores; `alembic check` sin diferencias pendientes |
| 4. Unitarias | `pytest tests/unit` | 100 % pasan |
| 5. Integración | `pytest tests/integration` | 100 % pasan |
| 6. Cobertura | `pytest-cov` | ≥ 85 % global; ≥ 95 % en `forecasting/decision.py`, `validation/`, `access/` |
| 7. Guardias científicas | `tests/guards/` (ver F3) | 100 % pasan |
| 8. Lenguaje natural | `tests/ui/test_plain_language.py` | 0 términos prohibidos en vistas operativas |
| 9. E2E | Playwright (`tests/e2e/`) | 100 % pasan |
| 10. Accesibilidad | axe-core vía Playwright | 0 violaciones *serious*/*critical* en las pantallas clave |
| 11. Regresión visual | Capturas Playwright frente a las aprobadas | Diferencia ≤ 0,2 % (cambios intencionales: se re-aprueban con nota en la bitácora) |
| 12. Rendimiento | `tests/perf/` | Pronóstico de todos los sensores < 1 s; `/` < 300 ms (p95, local) |
| 13. Lento / ML completo | `pytest -m slow` (solo con `--full`) | Benchmark reducido de punta a punta |

Opciones: `--plan NN` (ejecuta las etapas relevantes y las pruebas marcadas `@pytest.mark.plan(NN)`), `--full`, `--fast` (etapas 1, 4 y 7).

## F3 — Guardias científicas (lo que el jurado podría cuestionar)

`tests/guards/`:

| Prueba | Qué garantiza |
|--------|---------------|
| `test_no_synthetic_in_training` | El cargador lanza error con cualquier fila sintética; la DB no tiene filas sintéticas |
| `test_features_are_causal` | Alterar datos posteriores a *t* **no cambia** ningún rasgo en *t* (perturbación del futuro) |
| `test_scalers_fit_on_train_only` | Los estadísticos de normalización coinciden con los del bloque de entrenamiento y no con la serie completa |
| `test_walk_forward_no_overlap` | Ningún índice de validación está en entrenamiento o calibración; brecha ≥ w + k_max; embargo aplicado |
| `test_no_shuffle_splitters` | Análisis del código: no se usan `KFold`, `StratifiedKFold` ni `train_test_split(shuffle=True)` en `ml_core/` |
| `test_events_are_onsets` | Los episodios ya en curso en *t* no cuentan como verdad positiva |
| `test_lead_time_is_measured` | La anticipación sale de las marcas de tiempo, no de una constante |
| `test_persistence_baseline_present` | Toda evaluación incluye la persistencia y calcula MASE |
| `test_conformal_coverage` | En la serie simulada, la cobertura de [q10, q90] = 90 % ± 2 pp |
| `test_final_test_untouched` | La prueba final solo existe con `is_final_test=true` y un único registro por modelo |
| `test_threshold_direction_below` | El oxígeno avisa **por debajo** del límite |

## F4 — Mapa de pruebas por plan

| Plan | Unitarias | Integración | E2E / UI |
|------|-----------|-------------|----------|
| 15 | Diagnóstico, etapas E1–E6, conversión % LEL, rejilla sin inventar, umbrales | ETL idempotente (doble carga), purga, linaje | Cargar datos (P13) |
| 16 | — | Migraciones ida y vuelta, semillas idempotentes, `rebuild_events` reproducible, sin referencias a `predictions` | — |
| 17 | Contrato de los 10 adaptadores, conformal, decisión (persistencia, histéresis), narrador (plantillas completas, sin prohibidos), métricas por evento con casos a mano | Benchmark reducido, job de inferencia idempotente, cierre de `alert_outcomes`, regla de selección | Laboratorio: comparar y promover |
| 18 | `copy.py` (formato es-CO, plantillas), macros | Render de cada pantalla por rol | Hoy, Avisos (“Ya lo vi” y cerrar), Sala, móvil, modo oscuro, accesibilidad, capturas |
| 19 | Política de contraseñas, TOTP con reloj simulado, tokens con hash | Matriz de permisos parametrizada, alcance por zona en API, bloqueo, límite de intentos, CSRF, rotación y reutilización | Invitación, recuperación, dos pasos, kiosco |

## F5 — Verificador de lenguaje natural

1. Se recorren todas las rutas HTML operativas (todas salvo `/laboratorio/*`, `/datos/calidad` y `/_componentes`) renderizadas con datos de fábrica, para cada rol operativo.
2. Se extrae el texto visible (sin `<script>` ni atributos técnicos) y se busca cada término de `FORBIDDEN_TERMS` como palabra completa, sin distinguir mayúsculas ni tildes.
3. También se revisan las cadenas de `copy.py` marcadas como operativas y los `plain_text` del narrador.
4. Un fallo muestra: ruta, rol, término y fragmento.

## F6 — Validación con usuarios (evidencia de OE4)

1. Prueba de aceptación con 3–5 personas de la mina (operador, supervisor y gerencia), con 5 tareas guiadas: “¿Está todo bien ahora?”, “¿Qué zona necesita atención y por qué?”, “Marca que viste el aviso”, “¿Qué tan seguido acierta el sistema?” y “Descarga el informe de la semana”.
2. Medición: éxito por tarea, tiempo, errores y el cuestionario **SUS** (System Usability Scale). Meta: SUS ≥ 75 y éxito ≥ 90 %.
3. Hallazgos → cambios → repetir con las tareas fallidas (bucle de usabilidad).
4. Registro en `docs/ux/aceptacion.md`, que es evidencia para la tesis.

## F7 — El bucle

```
┌────────────────────────────────────────────────────────────┐
│ 1. Tomar el siguiente paso pendiente del plan              │
│ 2. Implementar (cambio pequeño, un commit)                 │
│ 3. verify.py --plan NN                                     │
│      ├─ verde → 4                                          │
│      └─ rojo  → diagnosticar causa raíz → corregir → 3     │
│                 (máx. 5 intentos; si no: detener y escalar) │
│ 4. Registrar en BITACORA_BUCLE.md                          │
│ 5. ¿Fase terminada? → revisar su Definición de terminado   │
│      ├─ todo cumple → siguiente fase                       │
│      └─ falta algo  → volver a 1 con ese punto             │
│ 6. ¿Plan terminado? → verify.py --full → actualizar         │
│    CONTEXTO_SISTEMA.md y el índice                          │
└────────────────────────────────────────────────────────────┘
```

**Reglas del bucle**
- Prohibido para “pasar”: borrar o saltar pruebas, bajar los umbrales de cobertura o calidad, agregar `# noqa` o `type: ignore` sin justificación escrita, re-aprobar capturas sin revisar o desactivar el verificador de lenguaje.
- Si una prueba está mal planteada: se explica en la bitácora, se corrige la prueba en un commit separado `test(...)` y luego se continúa.
- Las métricas de los modelos **no** son una condición del bucle: un modelo que no alcanza las metas de la tesis es un **resultado**, no un error. El bucle exige que la métrica esté **bien calculada y reportada**, no que sea alta.

**Plantilla de `planes/BITACORA_BUCLE.md`**

```markdown
## 2026-11-__ · Plan 17 · F3 · Paso 2 — Adaptador TFT
- Archivos: ml_core/forecasting/adapters/neural.py, tests/unit/test_adapters_contract.py
- verify: ✅ (iteraciones: 2 — 1ª falló contrato de columnas de salida)
- Decisiones: cuantiles vía MQLoss; early stopping sobre bloque de calibración
- Pendiente / riesgos: tiempo de entrenamiento en CPU ~6 min por pliegue
```

## F8 — Integración continua (preparación del Plan 09)

`.github/workflows/verify.yml`: servicios Postgres 15, instalación con caché, `verify.py` sin `--full` en cada push y `--full` cada noche. Las capturas aprobadas se versionan en `tests/e2e/__snapshots__/`.

---

## Definición de terminado del Plan 20
- [x] DB de pruebas aislada con rollback; `conftest` aborta si se apunta a la DB de desarrollo.
- [x] `verify.py` con las 13 etapas y las opciones `--plan`, `--fast` y `--full`.
- [x] Guardias científicas completas y en verde.
- [x] Verificador de lenguaje natural operativo.
- [x] Playwright + axe + capturas configurados. Playwright 1.64.1 y Chromium 156 instalados en `.venv`; E2E reales contra `localhost:8000`.
- [x] Prueba de aceptación con usuarios documentada (SUS); campo con personas de la mina pendiente.
- [x] `verify.py --full` en verde al cierre de los planes 15–19.
