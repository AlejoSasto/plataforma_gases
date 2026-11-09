# 25 — Plataforma lista con los datos reales actuales

**Reemplaza** la versión anterior del Plan 25, que no se implementó. Este plan es **solo de plataforma**; la corrección del documento de tesis va aparte.
**Absorbe** lo pendiente de los planes 23 (F1, F2, F3, F6, F8) y 24 (F2–F8). Si algo de esos planes contradice este, **manda este**.
**Datos:** los que ya están en la base de desarrollo: 13.894 lecturas reales, 50 sensores, 6 gases, marzo de 2023 a diciembre de 2025, detectores portátiles sin sitio. **No se espera** información nueva de la mina para terminar. Si llega, el plan ya la soporta (F9).
**Estado de partida** (bitácora al 2026-11-02):

| Ya hecho | Pendiente |
|----------|-----------|
| ETL v2, modelo de datos v2, usuarios y roles, interfaz Vigía, `verify.py`, base sin demo, camino viejo en `legacy/`, gráficas ancladas al último dato | Instrumentos, umbrales del decreto, TWA/STEL, benchmark real, pronósticos y avisos, pantallas de resultados, linaje visible, guardias de cierre |

---

## 0. Qué significa "plataforma lista"

La plataforma está lista cuando un evaluador, **sin ayuda**, entra con su usuario y puede comprobar estas siete cosas:

| # | Puede comprobar | Dónde |
|---|-----------------|-------|
| 1 | Qué datos reales hay, de qué equipos, con qué calidad y hasta qué fecha | Calidad de los datos, Equipos |
| 2 | Qué límites del Decreto 1886 aplica el sistema, con su artículo | Límites de seguridad |
| 3 | Qué modelos se compararon, cuál ganó y por qué, con cifras medidas fuera de muestra | Laboratorio → Resultados |
| 4 | Qué pronosticó el sistema contra lo que pasó, en cualquier periodo real | Laboratorio → Pronóstico contra realidad |
| 5 | Qué avisos habría dado en un turno real, con cuánta anticipación y si acertó | Revisar un turno |
| 6 | Qué tan confiable es el sistema, en lenguaje natural y con su fuente | Confiabilidad |
| 7 | De dónde sale cualquier aviso, hasta el archivo original | Detalle del aviso → De dónde sale |

Y además: `python scripts/build_real_platform.py --confirm` reconstruye todo desde cero, y `python scripts/verify.py --full` y `--dev-audit` quedan en verde.

---

## 1. Reglas que no se negocian

1. **Solo datos reales.** Nada sembrado, de ejemplo ni fabricado en la base de desarrollo o en la interfaz.
2. **Sin fuga.** Un pronóstico para el instante *t* viene de un modelo que no vio *t* (`train_end + embargo < issued_at`).
3. **Sin respaldos silenciosos.** Si un modelo no está instalado, falla y se reporta; nunca se sustituye por otro con su nombre.
4. **Umbrales con fuente.** Solo valores del Decreto 1886 con artículo. Lo que la norma no define queda **sin definir** y la interfaz lo dice; no se inventa.
5. **El bloque final queda reservado** (último bloque real) hasta su corrida única (F4.7).
6. **Lenguaje natural** en las vistas operativas; lenguaje técnico solo en el Laboratorio y en Calidad de los datos.
7. **Si falta un insumo, el sistema se detiene y lo dice.** No rellena.

---

## F0 — Higiene previa (horas)

| Paso | Qué | Prueba |
|------|-----|--------|
| 0.1 | Archivar todo modelo en `production` cuyo `algorithm` no esté en el zoo final (§F4.2): `scripts/archive_legacy_models.py --confirm` | `test_no_legacy_model_in_production` |
| 0.2 | Quitar la contraseña escrita en `CONTEXTO_SISTEMA.md` §7 y cambiarla en `.env`. Agregar el patrón `Pass123` a `common_passwords.txt` | `test_no_credentials_in_docs` |
| 0.3 | Reescribir `CONTEXTO_SISTEMA.md` §1, §5, §8.3–8.5 y §11 para que describan solo lo vigente. Lo retirado queda en una línea con referencia a `legacy/` | `test_context_doc_no_legacy_terms` |
| 0.4 | La prueba E2E de gráficas usa un **sensor real** y cuenta **puntos de la serie**, no paths de ejes | `test_charts_render.py` actualizado |

---

## F1 — Diagnóstico desde la base y parámetros automáticos (compuerta G1)

### Pasos
1. Ampliar `scripts/diagnose_real_data.py` para que lea **desde PostgreSQL** y calcule:
   - **instrumentos**: número de serie, gases por equipo, primera y última lectura;
   - **segmentos contiguos** por instrumento (corte cuando el hueco supera 3 × Δt), con duración p10, p50 y p90 en pasos;
   - **episodios** por gas y nivel con los umbrales de F3, con su duración y cuántos duran un solo paso;
   - **semántica de `Leyendo`**: comparación con STEL, TWA y `Número de Periodo`, con conclusión escrita (promedio, máximo o instantáneo);
   - **pruebas funcionales probables**: subida simultánea de varios gases del mismo equipo con caída de O₂ en 1–2 pasos.
2. **Decisiones automáticas G1**, escritas en `app_settings` y en el informe:

| Parámetro | Regla |
|-----------|-------|
| `lookback_steps` (w) | El mayor de {30, 60, 120} que sea ≤ p50 de segmento − 3 (k máx). Si ninguno cabe, w = max(12, p50 − 3) |
| `eligible_models` | Se excluyen los modelos cuya longitud de contexto mínima (consultada en su documentación al instalar) supere w; la razón queda escrita |
| `event_eval` por gas y nivel | `por_episodio` si hay ≥ 10 episodios; `solo_pronostico` si hay menos |
| `folds` | Bloques mensuales reales; se fusionan los contiguos hasta tener ≥ 500 pasos válidos de validación por gas prioritario; el último bloque es `final_test` |

3. Salidas: `reports/diagnostico/diagnostico_g1.md` y `.json`. La pantalla **Calidad de los datos** lee el JSON.

**Definición de terminado F1:** informe reproducible en dos corridas; parámetros G1 en `app_settings`; prueba unitaria de la regla de `lookback_steps` y de la fusión de bloques.

---

## F2 — Equipos reales (sin zonas inventadas)

1. Migración: tabla `instruments` (`serial` único, `model` si se infiere, `first_seen`, `last_seen`, `assigned_to` nulo, `site_id` nulo) y `sensors.instrument_id`. El ETL E3 la llena. Script de relleno para lo ya cargado.
2. `user_instrument_scopes` para el alcance del operador mientras no existan zonas reales.
3. La interfaz agrupa por **equipo** ("Detector 4521", con sus gases). "Zonas" se renombra a **Equipos**. La vista de zonas y el corte de la mina solo aparecen si hay al menos 3 sitios con coordenadas (F9).
4. Las covariables de los modelos son los **otros gases del mismo equipo**.

**Definición de terminado F2:** todo sensor tiene equipo; ninguna pantalla muestra zonas sin respaldo; prueba de alcance por equipo.

---

## F3 — Límites del Decreto 1886 y verdad de referencia

### 3.1 Esquema
Migración: `normative_thresholds` gana `metric` (`instantaneo` / `twa_8h` / `stel_15min`), `site_kind` (`frente` / `retorno_tajo` / `cualquiera`), `kind` (`normativo` / `politica_empresa`) y `article`.

### 3.2 Semilla (solo valores normativos)

| Gas | Nivel | Valor | Métrica | Artículo |
|-----|-------|-------|---------|----------|
| CH₄ | Vigilar | ≥ 0,5 % vol | instantáneo | Art. 162 (prohíbe voladura) y art. 53 par. 2 |
| CH₄ | Evacuar | ≥ 1,0 % vol (`site_kind=cualquiera`, el más estricto mientras no haya ubicación) | instantáneo | Art. 53 (máximo en frentes) y art. 183 (corte de energía) |
| O₂ | Evacuar | < 19,5 % vol (`direction=below`) | instantáneo | Art. 38 |
| O₂ | Evacuar | > 23,5 % vol | instantáneo | Art. 38 |
| CO | Actuar ya | ≥ 25 ppm | TWA 8 h | Art. 39 |
| H₂S | Actuar ya | ≥ 1 ppm | TWA 8 h | Art. 39 |
| H₂S | Actuar ya | ≥ 5 ppm | STEL 15 min | Art. 39 |
| CO₂ | Actuar ya | ≥ 5000 ppm / ≥ 30000 ppm | TWA 8 h / STEL 15 min | Art. 39 |
| NO₂ | Actuar ya | ≥ 0,2 ppm | TWA 8 h | Art. 39 |

- Los niveles que la norma no define (por ejemplo, "Actuar ya" del metano o "Vigilar" del CO) **no se siembran**. La pantalla Límites los muestra como "No definido por la norma. La empresa puede definirlo" y permite crearlos con `kind=politica_empresa` (permiso `thresholds.manage`, auditado).
- `verified=true` solo después de que una persona confirme cada artículo en Límites (queda en auditoría).

### 3.3 Series y episodios
1. E6 calcula por instrumento las series **causales** `twa_8h` y `stel_15min`. Si una ventana tiene menos del 75 % de cobertura, el valor queda faltante.
2. `rebuild_events.py` compara cada umbral con su `metric`, exige una duración mínima de 2 pasos para los instantáneos y **excluye** las pruebas funcionales probables (F1).
3. Avisos **confirmados** con la misma regla (lectura, TWA o STEL ya por encima).

**Definición de terminado F3:** pruebas de TWA y STEL móviles con casos calculados a mano, de `direction=below` y de exclusión de pruebas funcionales; episodios reconstruidos; la pantalla Límites muestra el artículo de cada valor.

---

## F4 — Benchmark real

### 4.1 Instalación sin respaldos
1. Instalar `requirements-ml.txt` con versiones fijas. Descargar los pesos en la construcción de la imagen (`scripts/fetch_foundation_weights.py`) para operar sin internet.
2. Quitar todo respaldo (`torch-lite`, `fallback-conformal`). Si falta la librería o el peso, el adaptador lanza `ModelUnavailableError`, el benchmark lo registra como "no disponible" y sigue con los demás.
3. `model_registry.params` guarda librería, versión, identificador y hash de los pesos.

### 4.2 Zoo final

| Clave | Modelo | Nota |
|-------|--------|------|
| `persistencia` | Último valor + intervalo conformal | Referencia obligatoria |
| `ets` | ETS (statsforecast) | Referencia estadística |
| `lgbm_q` | LightGBM cuantílico directo por horizonte; rasgos causales: rezagos, dC/dt, medias y desviaciones móviles, TWA y STEL, otros gases del equipo, hora y turno | Tabular fuerte, con SHAP |
| `lstm` | LSTM cuantílico (neuralforecast) | Comprometido en el anteproyecto |
| `tft` | Temporal Fusion Transformer (neuralforecast) | Transformer supervisado, con explicabilidad nativa |
| `chronos` | Chronos-Bolt (zero-shot); Chronos-2 con covariables del equipo si está disponible | Transformer fundacional |
| `timesfm` | TimesFM (zero-shot) | Fundacional de contraste |
| Ablación opcional | PatchTST, iTransformer, TTM | Solo si `eligible_models` (F1) los admite |

### 4.3 Evaluación
- Walk-forward con los `folds` de G1, purga de w + k_max y embargo de k_max.
- **Hiperparámetros:** búsqueda acotada (Optuna, 15 ensayos) **dentro** del entrenamiento de cada pliegue, solo para `lgbm_q`, `lstm` y `tft`. Los fundacionales no se ajustan.
- **Regla de aviso fija de antemano** (sin ajustar con pocos episodios): aviso si P(C ≥ θ) ≥ 0,5 en algún horizonte, con persistencia de 2 pasos e histéresis. Además se reporta la **curva** de recall frente a avisos innecesarios por turno.
- **Complemento por equipo no visto:** en el último pliegue se reservan equipos completos para medir generalización.
- **Métricas:**
  - pronóstico: MAE, RMSE, MASE, WIS, pinball, cobertura y ancho del intervalo;
  - eventos (solo donde `event_eval=por_episodio`): recall y precisión por episodio, anticipación p10 y p50 medida, avisos innecesarios por turno, IC por *bootstrap*;
  - operación: latencia por ciclo.

### 4.4 Persistencia de resultados
Migración: `benchmark_runs` (commit, hash de datos, semillas, parámetros G1, fecha, `is_final_test`) y `backtest_forecasts` (run, modelo, pliegue, sensor, `issued_at`, horizonte, q10/q50/q90/q95, `y_true`, `decided_level`, `train_end`). `model_evaluations` se calcula **desde** `backtest_forecasts`.

### 4.5 Modelos por pliegue
Cada modelo entrenado en cada pliegue se guarda en `storage/models/{run}/{model}/{fold}/` con su `train_end`. Los usa la reproducción (F5).

### 4.6 Selección y promoción
`select_production_model()` aplica la regla del Plan 17 §8 sobre la media de pliegues y escribe `selection_report` (texto de por qué ganó, criterio por criterio). La promoción es **explícita** (`--promote` o el botón del Laboratorio, con auditoría). Si ningún modelo supera a la persistencia, lo dice, y la persistencia + conformal queda como modelo activo.

### 4.7 Prueba final
`run_benchmark --final-test` se corre **una vez**, con el modelo promovido congelado, y se marca `is_final_test=true`. Antes de eso, el último bloque solo tiene avisos confirmados.

**Definición de terminado F4:** corrida real completa con `run_manifest.json`; cero respaldos; `backtest_forecasts` lleno para todos los modelos disponibles; selección escrita; modelo promovido.

---

## F5 — Pronósticos y avisos desde los datos reales (reproducción histórica)

1. `python -m app.modules.forecasting.replay --run <run_id>` recorre la rejilla real en orden cronológico. En cada paso y para cada sensor activo:
   - toma la ventana causal;
   - pronostica con el modelo **del pliegue que corresponde** (primer bloque: solo fundacionales en zero-shot; bloque final: solo confirmados hasta F4.7);
   - calibra con ACI usando solo residuos pasados;
   - decide con la regla de F4.3 y los umbrales vigentes en ese instante;
   - genera el texto de "Por qué avisamos" con los factores reales;
   - crea o actualiza `forecasts`, `forecast_quantiles`, `forecast_explanations` y `alerts` (`origin=historico`), con un aviso por episodio.
2. Las notificaciones de los avisos históricos se registran como "habría notificado a…" y **no se envían**.
3. Los avisos históricos se cierran solos al volver a normal (`resolved_by=sistema`, `human_handled=false`).
4. El cierre llena `alert_outcomes`: acertado (con minutos de anticipación), innecesario o episodio no avisado.
5. Todo es idempotente (UQ) y se puede repetir.

**Definición de terminado F5:** reproducción completa del histórico real; guardias de no fuga y de bloque final en verde; cada episodio real clasificado.

---

## F6 — Comando único de reconstrucción

`python scripts/build_real_platform.py --confirm` (también `make real`), idempotente:

1. migraciones;
2. semillas (roles, gases, **límites F3**, ajustes);
3. superadmin desde `.env`;
4. ETL v2 sobre el consolidado real y el inbox (deduplicación SHA-256);
5. equipos (F2);
6. rejilla, TWA y STEL;
7. diagnóstico G1 (F1);
8. episodios (F3);
9. benchmark (F4);
10. selección (pide confirmación para promover, o `--promote`);
11. reproducción (F5);
12. resultados de avisos.

Al terminar escribe `reports/real_platform/build_report.md` con conteos por tabla, episodios por gas y nivel, modelos disponibles y no disponibles, modelo activo y resumen de resultados. Si un paso falla, se detiene en ese paso con el motivo.

---

## F7 — Pantallas

Todas usan los macros de Vigía, `charts.js` y datos reales. Cada una con estado vacío explicativo y prueba E2E de render.

### 7.1 Operación (lenguaje natural)

| Pantalla | Contenido | Fuente |
|----------|-----------|--------|
| **Hoy** | Encabezado "Estado según las últimas lecturas recibidas (fecha)". Estado por equipo y gas, ahora y lo que viene, y gráfico "Ahora y lo que viene" del equipo más comprometido. Avisos abiertos: solo `en_vivo`; si no hay, lo explica y enlaza a Revisar un turno. Bloque **Actividad del sistema** | `forecasts`, `reading_grid`, `alerts` |
| **Avisos** | Pestañas Abiertos, Vistos y Cerrados; filtro de **origen** (en vivo / histórico); marca visible en los históricos | `alerts` |
| **Detalle del aviso** | Frase principal, lecturas (ahora, esperado, límite), por qué avisamos, qué hacer, seguimiento, resultado (acertó, minutos de anticipación). Bloque **De dónde sale este aviso** para analista, auditor y admin | `alerts`, `alert_outcomes`, linaje |
| **Equipos** | Lista de equipos con sus gases, último dato y estado; detalle con historial | `instruments`, `sensors` |
| **Historial** | Rango, equipo y gas; serie real con periodos de aviso sombreados; descarga CSV | `reading_grid`, `alerts` |
| **Revisar un turno** | Selector de fecha y turno reales; reproducción paso a paso con lecturas, lo esperado, avisos y lo que pasó; línea de tiempo con acertó, innecesario o no avisó. Encabezado fijo: "Revisión de datos reales del …" | `backtest_forecasts`, `alerts` históricos, `threshold_events` |
| **Confiabilidad** | Las tres preguntas en frase, con la fuente de cada cifra ("Calculado con N situaciones reales de … entre … y …"). Gases sin episodios suficientes: "Todavía no hay suficientes situaciones reales de … para medir esto" | `alert_outcomes` del run promovido |
| **Límites de seguridad** | Tabla por gas con valor, métrica explicada en simple ("promedio de 8 horas"), artículo y estado (verificado o por verificar); niveles no definidos por la norma | `normative_thresholds` |

### 7.2 Técnico (Laboratorio y Calidad)

| Pantalla | Contenido |
|----------|-----------|
| **Calidad de los datos** | Informe G1: equipos, segmentos, huecos, problemas de calidad, pruebas funcionales, semántica de `Leyendo`, parámetros elegidos y por qué |
| **Resultados → Corridas** | Lista de `benchmark_runs` con manifiesto |
| **Resultados → Tablero** | Tabla comparativa por gas, horizonte y nivel con IC, tamaño efectivo y colores frente a las metas; MASE frente a persistencia; modelos no disponibles y la razón |
| **Por qué ganó** | `selection_report`, criterio por criterio; botón Promover |
| **Pronóstico contra realidad** | Equipo y periodo; medido, pronóstico fuera de muestra con banda, límites, episodios coloreados (avisado, no avisado, innecesario) |
| **Curva de decisión** | Recall frente a avisos innecesarios por turno |
| **Calibración** | Cobertura real frente a nominal por horizonte |
| **Qué mira el modelo** | SHAP (LightGBM), selección de variables (TFT), gradientes integrados (LSTM) |
| **Ficha del modelo** | Librería, versión, pesos, ventana, horizontes, datos y limitaciones |

Cada figura técnica tiene descarga PNG o SVG y CSV.

### 7.3 Barra superior y riel
- La barra superior muestra "Datos hasta el …" (último dato real) o "Datos al día" si hay datos en vivo.
- El Laboratorio muestra el modelo activo con su fecha de promoción, y en rojo si no supera a la persistencia.

---

## F8 — Evidencia exportable

`python scripts/export_thesis_evidence.py --run <run_id>` genera en `reports/thesis/`:
- tablas en Markdown, LaTeX y CSV;
- figuras (las mismas del Laboratorio);
- episodios, avisos y resultados;
- linaje en CSV;
- `run_manifest.json`.

Todo sale de la base: **ninguna cifra se escribe a mano**.

---

## F9 — Preparada para datos nuevos

- Cargar datos nuevos (inbox o Cargar datos) dispara ETL → rejilla → pronóstico con el modelo activo → avisos `en_vivo` → notificaciones reales si `NOTIFICATIONS_DRY_RUN=false`.
- `scripts/load_instrument_map.py` carga el mapeo equipo → labor y activa zonas, el corte de la mina y `site_kind` (con lo que el metano pasa a 1,0 % o 1,5 % según el sitio).
- Agregar un bloque nuevo de datos permite volver a correr el benchmark con un pliegue más.

---

## F10 — Pruebas y guardias de cierre

| Prueba | Garantiza |
|--------|-----------|
| `test_no_silent_fallback` | Ningún adaptador sustituye un modelo faltante |
| `test_forecast_model_never_saw_target` | `train_end + embargo < issued_at` en todos los pronósticos y en `backtest_forecasts` |
| `test_final_block_reserved` | Sin avisos anticipados en el bloque final antes de su corrida |
| `test_thresholds_have_article` | Todo umbral `normativo` tiene artículo |
| `test_twa_stel_rolling` | TWA y STEL móviles correctos con casos a mano |
| `test_events_exclude_bump_tests` | Las pruebas funcionales no son episodios |
| `test_every_alert_has_lineage` | Todo aviso llega hasta su archivo de origen |
| `test_replay_idempotent` | Dos reproducciones, mismos conteos |
| `test_historic_alerts_not_open` y `test_no_email_for_historic` | Los históricos no se presentan como abiertos ni envían correo |
| `test_reliability_counts_match_outcomes` | Confiabilidad coincide con `alert_outcomes` |
| `test_metrics_from_backtest` | `model_evaluations` se recalcula igual desde `backtest_forecasts` |
| `test_build_real_platform_idempotent` | El comando único deja los mismos conteos en dos corridas (`slow`) |
| `test_no_demo_strings` y `test_no_credentials_in_docs` | Cero demo y cero contraseñas en documentos |
| E2E con datos reales | Las pantallas de F7 dibujan series con puntos, sin errores de consola, con el verificador de lenguaje en verde |

Todo entra en `scripts/verify.py --plan 25`. `--dev-audit` corre en solo lectura sobre la base de desarrollo.

---

## F11 — Documentación

- `CONTEXTO_SISTEMA.md`: actualizar modelo de datos, flujo, pantallas, comandos y el estado real.
- `00_INDICE_Y_ROADMAP.md`: el Plan 25 reemplaza las partes pendientes de 23 y 24, con los estados código / experimento / validación humana.
- `README.md`: sección "Reconstruir la plataforma con datos reales" con el comando único.

---

## Lo que queda fuera de este plan (depende de personas)

- Visto del director sobre G0 y G1.
- Confirmación de cada artículo en Límites (`verified=true`).
- Umbrales de política de la empresa, si la mina los define.
- Pruebas de usabilidad SUS con 3 a 5 usuarios.
- Datos del monitoreo fijo y mapeo de equipos de la mina (F9 ya los soporta).

---

## Prompt para Cursor

```text
Eres el agente de implementación de Vigía. Ejecuta planes/25_PLATAFORMA_LISTA_CON_DATOS_REALES.md
fase por fase (F0 → F11), en bucle:
1. Implementa el siguiente paso.
2. python scripts/verify.py --plan 25
3. Si falla: causa raíz, corrige, repite (máx. 5 intentos; si no, detente y escribe en la bitácora qué bloquea).
4. Registra en planes/BITACORA_BUCLE.md: paso, archivos, resultado, decisiones.
5. Al cerrar cada fase, revisa su definición de terminado punto por punto.
Contexto: CONTEXTO_SISTEMA.md, 14, 15, 17, 21, 22 y este plan (manda este ante conflicto).
Reglas: solo datos reales; sin fuga (train_end + embargo < issued_at); sin respaldos silenciosos;
umbrales solo con artículo del Decreto 1886 (lo no definido queda sin definir); bloque final
reservado; lenguaje natural en vistas operativas; recursos locales; nunca escribir contraseñas en archivos.
Prohibido desactivar o saltar pruebas para pasar.
Al terminar F6 ejecuta python scripts/build_real_platform.py --confirm y pega el build_report.md
en la bitácora. Al terminar F10 ejecuta python scripts/verify.py --full y --dev-audit.
```

---

## Definición de terminado del Plan 25
- [ ] F0: higiene cerrada (modelo viejo archivado, sin contraseñas en documentos, contexto al día, E2E con sensor real).
- [ ] F1: G1 desde la base, con parámetros automáticos documentados.
- [ ] F2: equipos reales; sin zonas inventadas.
- [ ] F3: límites del decreto con artículo y métrica; TWA y STEL; episodios sin pruebas funcionales.
- [ ] F4: benchmark real sin respaldos; `backtest_forecasts`; selección escrita; modelo promovido.
- [ ] F5: avisos y resultados generados desde los datos reales, sin fuga.
- [ ] F6: `build_real_platform.py` idempotente con informe.
- [ ] F7: todas las pantallas con datos reales y prueba E2E de render.
- [ ] F8: evidencia exportada desde la base.
- [ ] F10: `verify.py --full` y `--dev-audit` en verde.
- [ ] Las siete comprobaciones de §0 hechas por una persona que no participó en el desarrollo.
