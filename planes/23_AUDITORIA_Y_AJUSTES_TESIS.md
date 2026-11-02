# 23 — Auditoría del sistema frente a la tesis y ajustes obligatorios

**Fecha:** 2026-11-02. **Base:** `CONTEXTO_SISTEMA.md` (2026-11-02), `BITACORA_BUCLE.md`, `00_INDICE_Y_ROADMAP.md`, observaciones del jurado y texto del Decreto 1886 de 2015.
**Veredicto:** la plataforma está bien construida como software y el paquete 14–22 atiende la forma de las observaciones del jurado. **El núcleo científico todavía no se puede defender.** Hay cuatro problemas que la bitácora ya muestra pero que el índice marca como ✅:
1. no se ha corrido el benchmark con modelos reales;
2. el metano casi no tiene episodios;
3. los umbrales están mal planteados frente al decreto;
4. los datos vienen de detectores portátiles sin zona.

Además, en la plataforma **no se ven las gráficas** y **no hay un lugar donde ver qué hace la IA**: sus resultados, el modelo ganador ni los avisos que habría dado. Sin eso el sistema no demuestra nada ni a la empresa ni al jurado (fases F7 y F8).

Este plan va **antes** de cualquier trabajo nuevo de interfaz.

### Orden de ejecución

| Orden | Fase | Por qué en este orden |
|-------|------|-----------------------|
| 1 | **F7 Gráficas** (diagnóstico y arreglo) | Bloquea toda revisión visual; se arregla en horas |
| 2 | F5 Retirar el camino viejo | Evita mostrar modelos con fuga |
| 3 | F1 Datos reales y G1 | Decide qué se puede evaluar |
| 4 | F2 Umbrales del decreto | Define la verdad de referencia |
| 5 | F3 Experimento real | Produce los resultados |
| 6 | **F8 Ver lo que hace la IA** | Muestra los resultados de F3 en la plataforma |
| 7 | F4 Reencuadre de objetivos y F6 interfaz sin zonas | Cierre de la tesis |

> Prioridad sobre el paquete 14–22 cuando haya conflicto. Cada fase cierra con `python scripts/verify.py --plan 23` y una entrada en la bitácora.

---

## 0. Estado honesto (corregir el índice hoy)

Separar tres estados por plan: **código**, **experimento** y **validación humana**.

| Plan | Código | Experimento | Validación humana |
|------|--------|-------------|-------------------|
| 15 | ✅ | ⚠️ G0 calculado desde CSV, no desde DB; falta la longitud de segmentos (F1 de este plan) | ⬜ visto del director |
| 16 | ✅ | — | — |
| 17 | ✅ interfaz y adaptadores | ⬜ **benchmark con modelos reales no corrido** (bitácora: "pendiente instalar requirements-ml y pesos") | — |
| 18–22 | ✅ | — | ⬜ co-diseño y SUS |

Ningún resultado de `reports/thesis/` se cita en la tesis hasta cerrar la F3 de este plan.

---

## F1 — Lo que dicen de verdad los datos (bloqueante)

### Hallazgo A. El metano casi no tiene episodios

G0 reporta, con umbrales sin verificar: **CH₄ ≤ 1 episodio en todos los niveles**, CO 7 en "vigilar", H₂S 59 y O₂ 53. El gas central de la tesis no permite medir recall, precisión ni anticipación por evento. **Ningún algoritmo arregla esto.**

### Hallazgo B. Los datos son de detectores portátiles sin ubicación

`Sitio` viene vacío, así que los 50 sensores quedan en "Sin sitio asignado". Los `dls_report` de iNet son de equipos multigás que lleva el trabajador. Por eso:
- la serie mide la **exposición de quien porta el equipo**, que se mueve, y no la atmósfera de un punto fijo de la mina;
- las "zonas" de la interfaz, el alcance por zona del operador y el corte de la mina **no tienen respaldo en datos reales**;
- las covariables válidas son los **otros gases del mismo equipo** (mismo número de serie), no "la misma zona".

### Pasos

1. Ampliar `scripts/diagnose_real_data.py` para que lea **desde PostgreSQL** (no CSV) y agregue:
   - agrupación por **número de serie del instrumento** (`sensors.code` sin el sufijo de gas): cuántos instrumentos, qué gases mide cada uno;
   - **segmentos contiguos** por instrumento (cortes cuando el hueco supera 3 × Δt): número, duración p10, p50 y p90 en pasos y en horas;
   - **duración de cada episodio** (en pasos) y cuántos episodios duran un solo paso;
   - semántica de `Leyendo`: comparar con STEL y TWA del mismo periodo y con `Número de Periodo` para establecer si es promedio, máximo o instantáneo. Documentar la conclusión.
2. Regla nueva de calidad en E4: **`prueba_funcional_probable`**. Se marca cuando varios gases del mismo instrumento suben a la vez y el O₂ baja dentro de 1–2 pasos, con valores cercanos a los del cilindro de calibración de la mina. Pedir la hoja del cilindro (las mezclas de 4 gases usadas habitualmente rondan 50 % LIE de CH₄, 100 ppm de CO, 25 ppm de H₂S y 18 % de O₂, pero se usa el dato real de la mina). Estos episodios se **excluyen** de la verdad de referencia.
3. Recalcular los episodios con los umbrales corregidos de F2 y **sin** pruebas funcionales.
4. **Solicitudes formales a la mina** (dejar constancia en `docs/solicitudes_datos.md`):
   - datos del **sistema de monitoreo continuo fijo** de metano y oxígeno. El Decreto 1886 lo exige en minas de Categoría III (art. 47) y la medición debe ser permanente (art. 60);
   - categoría de la mina según el art. 58;
   - export de *datalog* crudo de iNet por intervalo;
   - mapeo de número de serie a cargo o labor, si existe;
   - hoja del cilindro de calibración.

### Compuerta G1 (nueva)

| Situación tras F1 | Decisión |
|-------------------|----------|
| Llegan datos fijos de CH₄ con ≥ 10 episodios reales | Se evalúa el CH₄ por evento. La tesis recupera su enfoque original |
| Solo hay portátiles y CH₄ < 10 episodios | **Reencuadre de OE3** (ver F4): el CH₄ se evalúa por calidad de pronóstico y la evaluación por evento se hace con H₂S, O₂ y CO. El metano queda declarado como limitación |
| La p50 de segmento contiguo es menor que w + k | Reducir la ventana w a ≤ p50 − k y retirar los modelos que necesitan contextos largos (F3) |

**Definición de terminado F1:** informe reproducible con instrumentos, segmentos, duraciones, semántica de `Leyendo` y pruebas funcionales; solicitudes enviadas; decisión G1 en la bitácora con visto del director.

---

## F2 — Umbrales: corregir contra el Decreto 1886

La semilla actual (`CH₄ 0,5/1,0/1,5`, `CO 25/50/100`, `H₂S 1/5/10`) mezcla valores normativos con valores inventados. Además compara **valores instantáneos con límites que son promedios ponderados**.

### Lo que dice el decreto (verificado)

| Gas | Norma | Tipo de límite |
|-----|-------|----------------|
| CH₄ | Art. 58: Categoría III si en algún sitio > 0,3 %. Art. 162: no se vuela con ≥ 0,5 %. Art. 53: máximo 1,0 % en frentes y retornos principales; 1,5 % en retornos de tajos y de frentes de preparación. Por encima del máximo nadie entra ni permanece. Con > 2 % solo entra personal de salvamento. Art. 183: se corta la corriente al alcanzar los valores del art. 53 | **Instantáneo y dependiente del tipo de sitio** |
| O₂ | Art. 38: no apto con < 19,5 % (ni con > 23,5 %) | Instantáneo |
| CO | Art. 39: TLV-TWA 25 ppm (sin STEL) | **Promedio ponderado de 8 h** |
| H₂S | Art. 39: TWA 1 ppm, STEL 5 ppm | **TWA 8 h y STEL 15 min** |
| CO₂ | Art. 39: TWA 5000 ppm, STEL 30000 ppm | TWA y STEL |
| NO₂ | Art. 39: TWA 0,2 ppm | TWA |

### Pasos

1. Nueva semilla, con `source_reference` exacta y `verified=true` solo en lo normativo:

| Gas | Vigilar | Actuar ya | Evacuar | Magnitud comparada |
|-----|---------|-----------|---------|--------------------|
| CH₄ | 0,5 % (art. 162) | **umbral interno de la mina** entre 0,5 % y el máximo del sitio; `kind=politica_empresa`, `verified=false` hasta que lo firme el responsable técnico | máximo del sitio según art. 53: 1,0 % en frentes, 1,5 % en retornos de tajos; sin ubicación se usa 1,0 % | lectura instantánea |
| O₂ | < 19,5 % (art. 38) | política de la empresa | política de la empresa | instantánea, `direction=below` |
| CO | TWA móvil 8 h ≥ 25 ppm (art. 39) | política de la empresa | política de la empresa | **TWA móvil 8 h** |
| H₂S | TWA móvil 8 h ≥ 1 ppm | STEL móvil 15 min ≥ 5 ppm (art. 39) | política de la empresa | **TWA o STEL móvil** |

2. Agregar a `normative_thresholds`: `metric` (`instantaneo` / `twa_8h` / `stel_15min`), `site_kind` (`frente` / `retorno_tajo` / `cualquiera`) y `kind` (`normativo` / `politica_empresa`). Migración con `downgrade`.
3. En E6, calcular las series **causales** `twa_8h` y `stel_15min` por instrumento. Si una ventana tiene menos del 75 % de cobertura, el valor queda faltante: no se imputa.
4. Rehacer `threshold_events` comparando cada umbral con su `metric`. Exigir una **duración mínima** de 2 pasos para instantáneos (configurable), con lo que se descarta ruido de un solo punto.
5. Los niveles marcados `politica_empresa` se muestran en la interfaz de Límites como "definido por la empresa", y en la tesis no se presentan como norma.

**Definición de terminado F2:** pruebas para TWA y STEL móviles (casos calculados a mano), dirección `below` y `site_kind`; los episodios se recalculan; la tabla de umbrales de la tesis cita artículos exactos.

---

## F3 — Experimento real: modelos que corresponden a estos datos

### Pasos

1. **Prohibir los respaldos silenciosos.** Si `neuralforecast`, `chronos` o `timesfm` no están instalados, el adaptador **falla**: no cae a `torch-lite` ni a `fallback-conformal` con el nombre del modelo real. Registrar en `model_registry.params`: librería, versión, identificador de pesos y su hash. Agregar la guardia `test_no_silent_fallback`.
2. Instalar `requirements-ml.txt` y descargar los pesos en la imagen (`scripts/fetch_foundation_weights.py`). Verificar la API y la **longitud de contexto mínima** de cada fundacional antes de usarlo.
3. Zoo ajustado a los datos (ver la tabla del §5). Los modelos que necesitan contextos más largos que los segmentos reales pasan a ablación o se retiran, **con la razón escrita**.
4. Evaluación:
   - **Temporal:** walk-forward por bloques mensuales con purga y embargo (lo que ya existe). Reportar el **tamaño efectivo** por pliegue, gas y nivel: pasos válidos y episodios.
   - **Por instrumento no visto:** además de la temporal, se reservan instrumentos completos (por número de serie) en el último bloque. Mide si el modelo global generaliza a un equipo nuevo.
   - **π por nivel:** con pocos episodios, **no se ajusta**. Se fija de antemano (aviso si q90 ≥ θ, o si P(C ≥ θ) ≥ 0,5) y se reporta la **curva** de recall frente a falsas alarmas por turno, con IC por *bootstrap*. Ajustar π con 5–10 episodios sería sobreajustar.
   - Métricas de pronóstico: MAE, MASE frente a persistencia, pinball promedio y **WIS** (weighted interval score), cobertura y ancho. Todo por gas y horizonte.
5. Correr el benchmark completo sobre la DB y guardar la **corrida congelada**: hash del commit, hash de los datos y semillas, en `reports/thesis/run_manifest.json`.
6. La prueba final intocable (último bloque real) se corre **una sola vez**, al final.

**Definición de terminado F3:** benchmark corrido de punta a punta con los modelos reales; manifiesto reproducible; ningún adaptador con respaldo silencioso; tablas por gas, horizonte y nivel con tamaño efectivo e IC.

---

## F4 — Reencuadre de objetivos si G1 sale sin metano evaluable

Texto propuesto para el **OE3**. Cambiarlo en todas las secciones del documento (lo pide la observación 4 del jurado):

> **OE3.** Desarrollar y evaluar, con validación temporal sin fuga de información, modelos de pronóstico probabilístico de concentraciones de gases basados en arquitecturas *transformer* y modelos fundacionales de series de tiempo, frente a modelos de referencia, y valorar su capacidad para anticipar la superación de límites del Decreto 1886 de 2015 en los gases con episodios suficientes en los datos reales del caso de estudio.

Metas de la tesis, reescritas como metas medibles con estos datos:

| Antes | Ahora |
|-------|-------|
| Recall ≥ 95 %, precisión ≥ 90 %, F1 ≥ 0,92 | Por gas con ≥ 10 episodios: recall por evento y falsas alarmas por turno **con IC**, frente a la persistencia y a la regla actual del instrumento. La meta del anteproyecto se reporta como **referencia**, no como compuerta |
| RMSE ≤ 0,05 fracción molar | CH₄: MAE y RMSE en % vol a cada horizonte y **MASE < 1**. Cobertura del intervalo del 90 % ± 5 pp |
| Anticipación 5–10 min | Anticipación medida por episodio a 6, 12 y 18 min (G0) |

Agregar a la tesis una sección de **amenazas a la validez**:
- detectores portátiles (exposición personal, no punto fijo);
- muestreo irregular de unos 6 min;
- 9 meses no contiguos, con el 64 % de los datos en nov-2024;
- metano sin episodios;
- umbrales de política de la empresa;
- semántica de `Leyendo`.

---

## F5 — Retirar el camino viejo (sigue vivo y tiene fugas)

`CONTEXTO_SISTEMA.md` §8.3–8.5 documenta **como vigente** el zoo tabular viejo. Mientras exista, cualquiera puede entrenar en el Laboratorio un modelo con fuga y mostrarlo al jurado. Lo que sigue vivo:
- `evento_final` con p95 global;
- `Cambio_Brusco` con σ global;
- `best_result` basado en `meets_thesis`;
- `get_production_model` con preferencia por modelos de secuencia;
- `lead_time_minutes_mean = 7.5`;
- `RISK_THRESHOLD_*` de 0,3 / 0,6 / 0,85 sobre probabilidades sin calibrar.

### Pasos

1. Mover `ml_core/models/`, `ml_core/features/build_features.py`, `targets.py` y `sequences.py` a `legacy/`, fuera del paquete. Eliminar `scripts/train_full_model_zoo.py` y los `retrain_*`.
2. `/laboratorio/entrenar` usa solo el zoo de `ml_core/forecasting`. Se elimina el selector de tarea clasificación o regresión.
3. Confirmar que `alerts/rules.py` y `forecasting/cycle.py` deciden con `normative_thresholds` y la regla del Plan 17 §5, **no** con `RISK_THRESHOLD_*`. Borrar `RISK_THRESHOLD_*`, `THESIS_*` (las metas pasan a `app_settings.thesis_targets`) y `ML_LEAD_MINUTES_*` de `.env.example` y de `config.py`.
4. Agregar las guardias `test_no_legacy_imports` (`app/` y `ml_core/forecasting` no importan `legacy`) y `test_no_probability_risk_thresholds`.
5. Reescribir §1, §5 (la tabla todavía dice que el 24m entra al ETL), §8.3–8.5 y §11 de `CONTEXTO_SISTEMA.md` para que describan solo lo vigente.

---

## F6 — Interfaz coherente con datos sin zonas

1. Si un sensor no tiene `site_kind` ni ubicación, la interfaz agrupa por **equipo** ("Detector 4521, Metano y CO"), no por "zona".
2. El corte de la mina solo aparece si hay al menos 3 sitios con `map_x` y `map_y`. Si no, se muestra la lista.
3. El alcance del operador se asigna por equipos mientras no haya zonas reales.
4. Las capturas de los mockups (zonas "Frente 3 Sur") no se usan como evidencia en la tesis: son ilustrativas.

---

## F7 — Las gráficas no se muestran (diagnóstico y arreglo)

### Causas probables, de la más a la menos probable

| # | Causa | Cómo confirmarla | Arreglo |
|---|-------|------------------|---------|
| 1 | **Los datos son históricos y el gráfico pide "la última hora"**. El último dato real es del 2025-12-11, así que una consulta como `ts >= now() - 60 min` devuelve vacío y no hay nada que dibujar | Abrir `/api/pronostico/...` o `/dashboard/api/forecast-by-gas` en el navegador: `measured: []` | Toda consulta de "ahora" usa como referencia la **hora del último dato** del sensor (`reference_time = max(ts)`), no el reloj. La UI lo dice: "Datos hasta el 11 de diciembre de 2025, 16:40". Ver también el modo **Revisar un turno** de F8 |
| 2 | **No hay pronósticos que dibujar.** Sin modelo promovido (el benchmark real no se ha corrido) y sin datos nuevos, `forecasts` está vacía | `SELECT count(*) FROM forecasts;` y `SELECT status FROM model_registry` | F3 y luego un **ciclo de pronóstico sobre el histórico**: `python -m app.modules.forecasting.cycle --backfill --from 2024-09-01` escribe pronósticos para cada paso histórico. Sin modelo, el gráfico muestra solo lo medido y la nota `copy.NO_FORECAST` |
| 3 | **El contenedor del gráfico mide 0 px de alto.** ECharts no dibuja en un `div` sin altura | DevTools: el `div[data-chart]` mide 0 px | Alturas fijas en CSS (`.chart { height: 320px }`) y `ResizeObserver` → `chart.resize()` |
| 4 | **htmx reemplaza el fragmento y nadie vuelve a crear el gráfico.** La primera carga funciona y luego desaparece, o los fragmentos nunca lo muestran | Se ve un segundo y se borra al refrescar | En `charts.js`: `document.body.addEventListener("htmx:afterSwap", e => initCharts(e.detail.target))`; antes de reemplazar, `echarts.getInstanceByDom(el)?.dispose()` |
| 5 | **CSP bloquea scripts** (`default-src 'self'`): `onload=`, `<script>` inline con código o datos inyectados en JS | Consola: `Refused to execute inline script` | Datos en `<script type="application/json" id="...">` (no se ejecuta, la CSP lo permite) o por `fetch`; cero `on*=` en templates |
| 6 | **Recurso que no carga**: `/static/vendor/echarts.min.js` da 404, el orden de scripts está mal, o Gunicorn no recargó el código | Pestaña Red: 404, o `echarts is not defined` | `docker compose restart app`; cargar `echarts.min.js` **antes** de `charts.js`, ambos con `defer` |
| 7 | **Colores vacíos.** Las variables CSS se leen antes de cargar `tokens.css` y la serie se pinta transparente | El gráfico tiene ejes pero no líneas | Leer los tokens dentro de `initCharts()` cuando el DOM está listo, y tener un color de respaldo |

### Pasos

1. Diagnóstico con evidencia: capturar la consola y la pestaña Red en `/`, `/avisos/{id}`, `/zonas/{id}`, `/historial`, `/confiabilidad`, `/laboratorio/comparar` y `/sala`. Anotar en la bitácora cuál de las 7 causas aplica a cada una.
2. `app/static/js/charts.js` con una sola entrada `initCharts(root)` que se llama al cargar y tras cada `htmx:afterSwap`. Debe:
   - destruir la instancia previa;
   - ante datos vacíos, pintar un **estado vacío explicativo**, nunca un recuadro en blanco ("Este sensor no tiene lecturas en este periodo");
   - ante error de red, pintar "No pudimos cargar el gráfico. Intenta de nuevo" con botón de reintento.
3. Servicio `reference_time(sensor_id)` en `forecasting/service.py`. Todos los endpoints de series lo usan y devuelven `reference_time` y `data_until` en el JSON.
4. Contrato de API probado (`tests/integration/test_chart_endpoints.py`): con fábricas de lecturas históricas (fechas de 2025), cada endpoint devuelve series **no vacías** y `reference_time` igual al último dato.
5. Prueba E2E `tests/e2e/test_charts_render.py` (Playwright). En cada pantalla con gráfico:
   - cada `[data-chart]` contiene un `svg` con al menos una `path` de la serie;
   - **cero errores en consola**, incluidos los de CSP;
   - en estado vacío aparece el texto explicativo.
6. Agregar la prueba E2E a la etapa 9 de `verify.py`. Ya no se puede marcar "gráficas listas" sin que la prueba pase.

**Definición de terminado F7:** las 7 pantallas muestran gráficas con datos reales del histórico; prueba E2E de render en verde; sin errores de consola; estados vacíos y de error explicativos.

---

## F8 — Dónde ver lo que hace la IA y cuál es el mejor modelo

Hoy los resultados quedan en `model_evaluations` (solo agregados), en `reports/thesis/` y en MLflow. **Nada de eso se ve en la plataforma**, y con agregados no se puede mostrar qué habría avisado el sistema en un momento concreto.

### 8.1 Guardar los pronósticos del backtest (requisito de todo lo demás)

Tabla nueva `backtest_forecasts` (migración con `downgrade`):

| Campo | Notas |
|-------|-------|
| run_id | FK a `benchmark_runs` (nueva: commit, hash de datos, semillas, fecha, `is_final_test`) |
| model_id, fold_index | |
| sensor_id, issued_at, horizon_min | |
| q10, q50, q90, q95 | Pronóstico fuera de muestra (el modelo no vio ese periodo) |
| y_true | Valor real observado en `issued_at + horizon` |
| decided_level | Nivel que habría emitido el sistema |
| UQ | (run_id, model_id, sensor_id, issued_at, horizon_min) |

`run_benchmark` escribe aquí **todas** las predicciones de validación. Las métricas de `model_evaluations` se recalculan desde esta tabla, así la cifra y el gráfico salen del mismo dato.

### 8.2 Laboratorio: resultados técnicos (analista y admin)

Rutas nuevas bajo `/laboratorio/resultados`. Aquí sí se usa lenguaje técnico.

| Pantalla | Contenido |
|----------|-----------|
| **Corridas** `/laboratorio/resultados` | Lista de corridas del benchmark: fecha, commit, datos usados, modelos, estado. Botón "Ver resultados" |
| **Tablero de la corrida** `/laboratorio/resultados/{run}` | Filtros por gas, horizonte y nivel. **Tabla comparativa** (MASE, MAE, WIS, cobertura, recall y precisión por evento, falsas alarmas por turno, anticipación p50 y p10, latencia), cada valor con IC y verde o rojo frente a la meta. Columna con el **tamaño efectivo** (pasos y episodios). Gráfico de MASE frente a persistencia |
| **Por qué ganó este modelo** | La regla de selección del Plan 17 §8 aplicada paso a paso: qué modelos quedaron fuera en cada criterio y por qué. Termina en el botón "Promover a producción" (permiso `models.promote`, queda en auditoría) |
| **Pronóstico contra realidad** `/laboratorio/resultados/{run}/modelo/{id}` | Selector de sensor y periodo. Gráfico con lo medido, el pronóstico fuera de muestra con su banda, las líneas de umbral y los **episodios reales marcados**: verde si se avisó a tiempo, rojo si no se avisó, gris si fue una falsa alarma |
| **Curva de decisión** | Recall por evento frente a falsas alarmas por turno, al variar la regla de aviso. Marca el punto elegido |
| **Calibración** | Cobertura real frente a la nominal por horizonte (debe acercarse a la diagonal) |
| **Qué mira el modelo** | Importancia de factores: SHAP para LightGBM, selección de variables para TFT, gradientes integrados para LSTM. Agregada y por episodio |
| **Ficha del modelo** | Familia, librería y versión, pesos, ventana, horizontes, datos de entrenamiento, limitaciones conocidas. Sirve de anexo para la tesis |

Exportación: cada pantalla tiene "Descargar figura (PNG/SVG)" y "Descargar datos (CSV)". Esas figuras son las de la tesis y del artículo.

### 8.3 Operación: lo mismo, en lenguaje natural

| Pantalla | Para quién | Contenido |
|----------|------------|-----------|
| **Revisar un turno** `/revisar` (nueva) | Supervisor, gerencia, auditor | Se elige una fecha y un turno **reales** del histórico. El sistema reproduce paso a paso lo que habría mostrado: lecturas, lo que esperaba, los avisos que habría dado y **qué pasó después**. Una línea de tiempo marca cada aviso como "acertó, avisó N minutos antes", "aviso innecesario" o "no avisó". Encabezado fijo: "Revisión de datos reales del 14 de noviembre de 2024. No es una situación actual". Es la demostración principal para la empresa y para el jurado |
| **Confiabilidad** `/confiabilidad` | Gerencia y supervisor | Se alimenta de `backtest_forecasts` (corrida promovida) y de `alert_outcomes` (operación real). Indica de dónde sale cada cifra: "Calculado revisando 9 meses de datos reales" |
| **Actividad del sistema** (bloque en Hoy y en Confiabilidad) | Todos | En frases: "El sistema revisó 48 sensores hace 2 minutos", "Último aviso anticipado: hace 3 h", "Datos hasta el 11 de diciembre de 2025". Si no hay pronóstico activo: "Por ahora mostramos solo lo que marcan los sensores" |

El verificador de lenguaje (Plan 20 F5) se aplica a `/revisar` y a Confiabilidad. El término "modelo" sigue prohibido en estas vistas; aquí se dice "el sistema".

### 8.4 El mejor modelo en producción, visible y trazable

1. En el riel, para analista y admin: el Laboratorio muestra una insignia con el nombre del modelo activo y la fecha de su promoción.
2. `model_registry` en producción guarda `run_id` y `selection_report`, el texto de "por qué ganó". La ficha del modelo lo enlaza.
3. Si el modelo activo no supera la persistencia en la corrida vigente, el Laboratorio lo muestra en rojo: "El modelo activo no mejora a la persistencia en CH₄ a 12 min".

### Pasos

1. Migración `benchmark_runs` + `backtest_forecasts`, y escritura desde `run_benchmark`.
2. Endpoints JSON para cada gráfico de 8.2 y 8.3, con pruebas de contrato.
3. Pantallas 8.2 (técnicas) y 8.3 (operativas) con los macros de Vigía y `charts.js`.
4. Pruebas E2E de render (F7) para todas las pantallas nuevas.
5. Capturas de las pantallas para el capítulo de resultados de la tesis.

**Definición de terminado F8:** con una corrida real del benchmark, un analista puede ver en la plataforma qué modelo ganó, por qué, cómo pronosticó cada episodio y qué miraba. Un supervisor puede revisar cualquier turno real y ver qué habría avisado el sistema y si acertó. Todo sale de `backtest_forecasts`, sin datos inventados.

---

## Prompt para Cursor (F7 y F8)

```text
Ejecuta planes/23_AUDITORIA_Y_AJUSTES_TESIS.md, fases F7 y luego F8, en bucle
(paso → python scripts/verify.py --plan 23 → corregir → bitácora).
F7: primero diagnostica con evidencia (consola y red de cada pantalla) cuál de las 7 causas
aplica; no cambies código antes de registrar el diagnóstico en planes/BITACORA_BUCLE.md.
No des por arreglado un gráfico sin la prueba E2E tests/e2e/test_charts_render.py en verde.
F8: los resultados deben salir de backtest_forecasts; prohibido dibujar con datos inventados.
Vistas operativas en lenguaje natural (verificador de lenguaje en verde). Recursos locales, sin CDN.
```

---

## Definición de terminado del Plan 23
- [ ] Índice con los tres estados por plan.
- [ ] Informe F1 (instrumentos, segmentos, semántica de `Leyendo`, pruebas funcionales) y decisión G1 con visto del director.
- [ ] Solicitudes de datos enviadas y registradas.
- [ ] Umbrales con artículo exacto, métrica (instantáneo, TWA, STEL), tipo de sitio y tipo de norma; episodios recalculados.
- [ ] Benchmark real con manifiesto; cero respaldos silenciosos.
- [ ] OE3 y metas reescritas en todas las secciones de la tesis, con amenazas a la validez.
- [ ] Camino viejo en `legacy/`, con guardias en verde.
- [ ] Gráficas visibles con datos reales en todas las pantallas; prueba E2E de render y consola sin errores.
- [ ] `backtest_forecasts` con la corrida real; resultados del Laboratorio, "Revisar un turno" y Confiabilidad alimentados desde ahí.
- [ ] Modelo activo visible y trazable a su corrida y a su "por qué ganó".
- [ ] `python scripts/verify.py --full` en verde.
