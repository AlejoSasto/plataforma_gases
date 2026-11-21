# Estado integral del proyecto Vigía

Documento de lectura única. Reúne alcance, cumplimiento, limitaciones, arquitectura, modelo de datos y resultados que hoy están repartidos en `planes/`, `documentacion/claude/`, `docs/` y `reports/`.

| Campo | Valor |
|---|---|
| Sistema | Vigía · Gases en la mina |
| Nombre formal | Plataforma de monitoreo y predicción de gases |
| Caso | Mina subterránea de carbón en Colombia. Umbrales de referencia: Decreto 1886 de 2015 |
| Fecha de esta síntesis | 2026-11-20 |
| Qué es | Un inventario escrito a partir de archivos del repositorio. No sustituye una consulta en vivo a PostgreSQL ni a MLflow |
| Qué no es | El marco teórico que todavía no está escrito en el repositorio, el volcado de las celdas de los notebooks, ni una consulta en vivo a la base. El diccionario de columnas, las herramientas del asistente, la regla de decisión, el manual y la especificación de los diagramas sí están en este archivo, desde la sección 17 |

Registro de este archivo: técnico. Se usan los nombres del código (`forecast`, cuantil, MASE, `lookback`, ETL, `kind=anticipado`). La capa `app/shared/copy.py` traduce esos nombres a la interfaz (pronóstico → «lo que viene», q50 → «se espera alrededor de», q10–q90 → «podría estar entre»). Esa traducción se documenta como mapeo, no como definición del sistema.

Si un número de este texto y un reporte no coinciden, gana el reporte. Si un reporte y el código no coinciden, gana el código. `planes/CONTEXTO_SISTEMA.md` sigue siendo el mapa de trabajo del código; varias de sus secciones quedaron atrás de las migraciones y del zoo vigente. Esas diferencias se marcan aquí.

## 1. Qué es y qué hace

Monolito FastAPI 0.1.0 + Jinja2 + PostgreSQL 15. Los jobs de inbox ETL y de inferencia corren con APScheduler en el mismo proceso. No hay microservicios, broker ni stream del instrumento.

Contrato funcional:

1. ETL E1–E6 de Excel `dls_report` (hoja `Resumen`, cabecera en la fila 24) o del CSV consolidado hacia `gas_readings` y `reading_grid`.
2. Zoo de pronóstico probabilístico en `ml_core/forecasting/adapters/`. Si falta la librería o el peso, el adaptador lanza `ModelUnavailableError` y no sustituye otro modelo.
3. Pronóstico multihorizonte H ∈ {6, 12, 18} min con cuantiles q10, q50, q90, q95. La decisión compara P(cruce) contra π y contra `normative_thresholds`. El aviso `confirmado` no pasa por el modelo.
4. Persistencia de `forecasts`, `forecast_quantiles`, `forecast_explanations`, `alerts` y `alert_outcomes`.
5. `audit_log` de autenticación, promoción, umbrales, carga y kiosco.
6. Asistente opcional con function calling. `ASSISTANT_PROVIDER=off` por defecto. `grounding.py` rechaza una cifra que no esté en la evidencia de las herramientas. No clasifica el riesgo de entrada al frente.

Fuera de alcance:

- Telemetría continua. La entrada es archivo.
- `alarmReport_*.xlsx` y el historial de sesiones MX6: no hay parser.
- Generación libre del texto de un aviso. `plain_message` sale de plantillas en `ml_core/forecasting/explain/`, no de un LLM.
- Promoción automática. Hace falta `POST /api/ml/models/{id}/promote` con permiso `models.promote`.
- Despliegue cloud. El Plan 09 (Cloud Run / Cloud SQL) no está implementado. El objetivo descrito es edge con Docker Compose.

## 2. Alcance de los datos

Fuente de las lecturas de trabajo: `gas_readings` en PostgreSQL, con `is_synthetic = false`. El archivo de origen y de respaldo es `data/processed/Procesamiento_de_Datos.csv`.

Diagnóstico del 2026-11-08 (`reports/diagnostico/diagnostico_datos.md`), leído desde la base:

| Dato | Valor |
|---|---|
| Filas reales | 13 894 |
| Pares sensor-gas | 50 |
| Gases | CH4, CO, CO2, H2S, NO2, O2 |
| Desde | 2023-03-31 14:37:09 UTC |
| Hasta | 2025-12-11 14:17:44 UTC |
| Duplicados exactos | 0 |
| Casi duplicados en 60 s con el mismo valor | 10 |
| LIE de CH4 usado al pasar de %LEL a %vol | 5,0 %vol |

Filas por mes, según `planes/CONTEXTO_SISTEMA.md` §5 (el diagnóstico no repite este total mensual):

| Mes | Filas |
|---:|---:|
| 2023-03 | 40 |
| 2024-09 | 513 |
| 2024-11 | 8 937 |
| 2024-12 | 18 |
| 2025-08 | 236 |
| 2025-09 | 322 |
| 2025-10 | 184 |
| 2025-11 | 2 344 |
| 2025-12 | 1 300 |

Huecos de calendario: abril de 2023 a agosto de 2024, octubre de 2024, y enero a julio de 2025. La columna Sitio del CSV suele ir vacía; el ETL crea «Sin sitio asignado».

Archivos que no entran al ETL: los dos `alarmReport_*.xlsx`, `Historial del registro de datos.xlsx` (sesiones de un MX6, no lecturas) y `Procesamiento_de_Datos_24m.csv` (serie aumentada, retirada). El cargador solo acepta el consolidado real: `python scripts/load_processed_dataset.py --consolidado`.

El servicio `app` de Docker Compose no monta `data/`. La carga masiva corre en el host.

## 3. Compuerta G0: a qué horizonte se puede mirar

Fuente: `reports/diagnostico/g0_decision.json` y `docs/g0_visto_director.md`.

| Dato | Valor |
|---|---|
| Δt p50 de CH4 | 5,7708 min |
| Δt p50 de CO | 2,5375 min |
| Δt p50 de H2S | 1,0 min |
| Δt usado para la banda | 5,7708 min (el máximo entre CH4, CO y H2S) |
| Banda | `medium` (2 < Δt ≤ 10 min) |
| Horizontes | 6, 12 y 18 minutos (1, 2 y 3 pasos) |
| Lo que ya no se promete | 5 y 10 minutos del anteproyecto |

La decisión técnica está registrada. La firma del director no está: la tabla de `docs/g0_visto_director.md` sigue en blanco. La nota del diagnóstico pide el export del datalog iNet por intervalo. Sin ese archivo la rejilla no se vuelve más densa.

## 4. Compuerta G1: qué modelos caben

Fuente: `reports/diagnostico/diagnostico_g1.md`, generado el 2026-11-08. La regla está en `ml_core/domain/g1.py`.

Segmentación en `ml_core/diagnosis_g1.py`: por instrumento, un segmento se corta si Δt > 3 × mediana de los Δt de ese serial. Duración en pasos de rejilla: p10 = 1, p50 = 2, p90 = 13.

`choose_lookback_steps(p50, k_max=3)` toma el máximo de {30, 60, 120} que cumpla w ≤ p50 − k_max. Ninguno cumple. El fallback es `max(12, p50 − k_max)` = **w = 12**. `k_max = 3` porque los horizontes son 1, 2 y 3 pasos de 6 min.

| Modelo | Contexto mínimo | En esta ventana |
|---|---:|---|
| persistencia | 1 | Cabe |
| ets | 8 | Cabe |
| lgbm_q | 30 | Excluido |
| lstm | 30 | Excluido |
| timesfm | 32 | Excluido |
| ttm | 32 | Excluido; además queda fuera de la ablación |
| tft | 48 | Excluido |
| patchtst | 48 | Excluido; fuera de la ablación |
| itransformer | 48 | Excluido; fuera de la ablación |
| chronos | 64 | Excluido |
| chronos2 | 64 | Excluido |

`Leyendo` se modela como observación instantánea. No hay serie STEL ni TWA medida por el instrumento contra la cual contrastar; `reading_grid.twa_8h` y `stel_15min` son agregados calculados por la rejilla, no campos del detector.

Pliegues que arma el diagnóstico. El último bloque no se usa para elegir modelo:

| Papel | Meses | Pasos válidos |
|---|---|---:|
| Validación | 2023-03, 2024-09 | 553 |
| Validación | 2024-11 | 8 937 |
| Validación | 2024-12, 2025-08, 2025-09 | 576 |
| Validación | 2025-10, 2025-11 | 2 528 |
| Prueba final, reservada | 2025-12 | 1 300 |

## 5. Resultados que sí están escritos

### 5.1 Pronóstico

Fuente: `reports/thesis/benchmark.json`. Un pliegue, `fold-0`. `is_final_test` es falso. No hay filas de LSTM, TFT, LightGBM ni fundacionales.

| Modelo | Familia | Backend | MAE | RMSE | MASE | Pinball | Cobertura q10–q90 | Ancho q10–q90 | Latencia |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| persistencia | baseline | native | 0,01945 | 0,02345 | 1 | 0,00605 | 0,6667 | 0,04797 | 2,66 ms |
| ets | baseline | holt-native | 0,01673 | 0,02139 | 0,8601 | 0,00544 | 0,7083 | 0,04797 | 3,63 ms |

Lectura permitida por `documentacion/claude/32_DOCUMENTACION_DE_RESULTADOS.md`: en este pliegue y esta corrida, ETS baja el MASE por debajo de 1. La cobertura de ambos queda por debajo del 90 % nominal. Con un solo pliegue y sin el resto del zoo no se elige modelo de producción.

`reports/thesis/ablaciones.md` solo registra esos dos backends. La ablación de ventana, covariables, ajuste fino, alcance y pérdida no está en la corrida.

El script `python -m ml_core.experiments.run_benchmark` escribe ese JSON. Si existe `data/processed/dls_report_consolidado.csv`, usa las primeras 800 filas. Si no existe, usa una serie sintética de 240 puntos. Por eso este JSON no debe leerse como la evaluación de las 13 894 lecturas.

### 5.2 Reconstrucción del 2026-11-08

Fuente: `reports/real_platform/build_report.md` y `planes/BITACORA_BUCLE.md`.

Pasos completados: migraciones, semillas, superadmin, ETL, eventos, equipos, diagnóstico y benchmark. El benchmark de esa reconstrucción escribió 4 089 filas de pronóstico de persistencia, corrida 1. ETS, LightGBM, LSTM, TFT, Chronos y TimesFM no se ejecutaron: no están instalados o no caben en la ventana. Promoción pedida: no. El bloque de diciembre de 2025 no se corrió.

`ml_core/experiments/real_benchmark.py` solo arma el backtest de persistencia. Aunque un modelo pase el sondeo, esa función no calcula su MAE ni su MASE.

### 5.3 Por qué el resto no tiene métrica, aunque se instalen las librerías

En el código actual, `fit` de estos adaptadores termina en `ModelUnavailableError` y no entrena una red sustituta:

| Adaptador | Qué dice al fallar |
|---|---|
| lstm, tft, patchtst, itransformer | Falta `neuralforecast`, o está instalado y no hay entrenamiento nativo cableado |
| chronos, chronos2 | Falta `chronos-forecasting`, o no hay pesos locales |
| timesfm | Falta `timesfm`, o no hay pesos locales. La dependencia está comentada en `requirements-ml.txt` |
| ttm | Falta `granite-tsfm`, o no hay pesos locales |

`lgbm_q` sí ajusta un regresor cuantílico si LightGBM está instalado. La compuerta G1 igual lo excluye, porque pide 30 pasos y la ventana es 12.

Existe un entrenador pequeño en CPU en `ml_core/forecasting/adapters/_torch_quantile.py` (LSTM, atención y un mixer). Los adaptadores públicos no lo usan para publicar un número con el nombre LSTM, TFT o Chronos.

`evaluate_model` en `ml_core/experiments/run_benchmark.py` no atrapa `ModelUnavailableError`. Pedir `lstm` en `--models` corta la corrida. El mismo archivo se salta todo pliegue marcado como prueba final, también cuando se pasa `--final-test`.

### 5.4 Episodios y métricas de aviso

Dos informes cuentan episodios con reglas distintas. No se suman.

Diagnóstico de base, `reports/diagnostico/diagnostico_datos.md`. Umbrales de semilla con `verified=false`. La política `por_episodio` exige al menos 10 inicios; por debajo de eso el modo es `no_event_metrics` o, en otros informes, un intervalo ancho.

| gas_code | level | direction | θ | n inicios | event_eval |
|---|---|---|---:|---:|---|
| CH4 | vigilar | above | 0,5 | 1 | no_event_metrics |
| CH4 | evacuar | above | 1,0 | 1 | no_event_metrics |
| O2 | evacuar | below | 19,5 | 53 | bootstrap_ic |
| O2 | evacuar | above | 23,5 | 2 | no_event_metrics |
| CO | actuar | above | 25 | 7 | no_event_metrics |
| H2S | actuar | above | 1,0 | 59 | bootstrap_ic |
| H2S | actuar | above | 5,0 | 7 | no_event_metrics |
| CO2 | actuar | above | 5 000 | 23 | wide_ic_warning |
| CO2 | actuar | above | 30 000 | 13 | wide_ic_warning |
| NO2 | actuar | above | 0,2 | 23 | wide_ic_warning |

`reports/eda/resumen.md` publica otro corte (vigilar, actuar y evacuar por gas) y no debe citarse como si fuera la misma tabla. En metano ese resumen también muestra un solo inicio por nivel.

`reports/thesis/` no contiene recall por evento, lead time (p50/p10) ni falsas alarmas por turno. Esas métricas viven en `alert_outcomes` (`outcome`, `lead_minutes`) y solo se agregan en `/confiabilidad` si hay filas. Con n < 10 episodios la política es `no_event_metrics`: no se publica recall.

### 5.5 ETL de la corrida documentada

Fuente: `docs/etl/transformaciones.md`, sobre `Procesamiento_de_Datos.csv`, sin persistir en esa nota.

| Etapa | Entran | Salen | Rechazadas | Qué pasó |
|---|---:|---:|---:|---|
| E1 Extraer | 13 894 | 13 894 | 0 | CSV de 15 columnas |
| E2 Validar | 13 894 | 13 894 | 0 | Ningún rechazo |
| E3 Estandarizar | 13 894 | 13 894 | 0 | 4 714 conversiones de unidad; 0 unidades desconocidas |
| E4 Calidad | 13 894 | 13 894 | 0 | 4 837 marcas: 2 337 fuera de rango físico, 2 335 huecos, 133 saltos imposibles, 32 valores congelados. La fila no se borra por la marca |
| E6 Rejilla | 13 894 | 821 205 | 0 | Paso de 1 minuto: 31 imputados y 821 152 faltantes |

E5 carga de forma idempotente por la huella del archivo y por el par sensor-tiempo. E6 rellena hacia adelante como máximo 3 pasos y deja el hueco largo como faltante. No interpola hacia el futuro. La rejilla es mucho más larga que las lecturas porque el minuto vacío cuenta como paso. Eso no aumenta la información.

### 5.6 Asistente

Fuente: `reports/assistant/eval_2026-11-09.md`.

| Prueba | Resultado |
|---|---|
| Preguntas | 60 |
| Herramienta correcta con el proveedor determinista | 60 / 60 |
| Emergencias | 2 / 2 |
| Fuera de tema | 2 / 2 |

Gemini no se midió. No hay autorización escrita en `docs/solicitudes_datos.md` para enviar datos de la mina a un proveedor externo. Por defecto `ASSISTANT_PROVIDER=off`.

### 5.7 Umbrales

La semilla está en `reports/diagnostico/normative_thresholds_seed.json`. Todos los registros de esa semilla tienen `verified=false`. Hasta que una persona los confirme, la pantalla de Límites dice que faltan por verificar. Cambiar un límite se hace en Ajustes, queda en la bitácora y no lo hace el asistente.

Valores de esa semilla, sin tratarlos como límite ya firmado:

| gas_code | level | direction | value | unit | metric |
|---|---|---|---:|---|---|
| CH4 | vigilar | above | 0,5 | %vol | instantaneo |
| CH4 | evacuar | above | 1,0 | %vol | instantaneo |
| O2 | evacuar | below | 19,5 | %vol | instantaneo |
| O2 | evacuar | above | 23,5 | %vol | instantaneo |
| CO | actuar | above | 25 | ppm | twa_8h |
| H2S | actuar | above | 1 | ppm | twa_8h |
| H2S | actuar | above | 5 | ppm | stel_15min |
| CO2 | actuar | above | 5 000 | ppm | twa_8h |
| CO2 | actuar | above | 30 000 | ppm | stel_15min |
| NO2 | actuar | above | 0,2 | ppm | twa_8h |

## 6. Qué está cumplido y qué no

Estados tomados de `planes/CONTEXTO_SISTEMA.md` §2, corregidos con el veredicto del Plan 23 y con la bitácora. «Código presente» no significa «resultado de tesis defendible».

| Plan | Código | Resultado o cierre |
|---|---|---|
| 01 Infraestructura | Cumplido | Base del monolito |
| 02 Auth, usuarios, roles | Cumplido | Login posterior endurecido el 2026-11-02 |
| 03 Ingesta ETL | Cumplido | E1–E6 sobre el consolidado real |
| 04 y 05 Entrenamiento y alertas de la primera generación | Código histórico | El camino tabular y de secuencias anterior está en `legacy/`. No es el zoo vigente |
| 06 Contactos y notificaciones | Cumplido en código | WhatsApp es un stub. Sin SMTP real, el aviso queda en `storage/outbox/` si `NOTIFICATIONS_DRY_RUN=true` |
| 07, 11, 12, 13 Pantallas y zoo de la primera generación | Hechos y luego superados | Ganan los planes 17 a 22 cuando hay conflicto |
| 08 Informes | Cumplido en código | PDF y Excel desde los agregados de la base |
| 09 Despliegue en nube | No cumplido | Sigue el borde. No hay Cloud Run ni Cloud SQL |
| 10 Seguridad | Parcial | Login, CSP, CSRF y cookies están. Faltan k6, pip-audit, HSTS de producción y respaldos |
| 14 Índice de reformulación | Documento | Mapa del jurado |
| 15 Datos reales | Código y G0 técnico | Falta la firma del director. El datalog por intervalo no llegó |
| 16 Modelo de datos v2 | Cumplido | `predictions` retirada. Pronóstico en `forecasts` y `forecast_quantiles` |
| 17 Zoo y evaluación | Adaptadores, conformal y decisión en código | El benchmark con los modelos reales no está corrido. El JSON solo tiene persistencia y ETS |
| 18 Lenguaje natural | Cumplido en pantallas | Textos de operación en `app/shared/copy.py` |
| 19 Roles y acceso | Cumplido | Seis roles, TOTP, kiosco, alcance por zona |
| 20 Pruebas | El arnés existe | `verify --full` no consta como verde en la bitácora del Plan 25. El E2E de gráficas del Plan 25 falló porque faltaba el navegador de Playwright |
| 21 y 22 Identidad Vigía | Aplicados en la app | Falta el corte esquemático de la mina en Hoy y la revisión visual contra las capturas |
| 23 Auditoría científica | Varias fases en código (camino viejo retirado, pantallas de resultados) | La definición de terminado del plan sigue con todas las casillas abiertas: visto G1, solicitudes de datos, umbrales confirmados, benchmark real, prueba final, modelo activo trazable, `verify --full` |
| 25 Datos reales en la plataforma | F0–F7 y la reconstrucción F6 | F10 bloqueado por Playwright. La reproducción histórica todavía no escribe todos los avisos en `alerts` |
| 26 Asistente | Herramientas, manual e índice | Gemini sin medir. Falta autorización de la empresa, capturas reales del manual y el rol de base `vigia_assistant_ro` |

Definición de terminado del Plan 23, todavía abierta en el propio plan: índice con tres estados por plan; informe F1 con visto del director; solicitudes de datos registradas; umbrales con artículo, métrica y tipo de sitio confirmados; benchmark real sin respaldos silenciosos; objetivos reescritos; camino viejo en `legacy/`; gráficas con prueba E2E; `backtest_forecasts` alimentando Laboratorio, Turno y Confiabilidad; modelo activo con el motivo de la selección; `python scripts/verify.py --full` en verde.

## 7. Arquitectura

### 7.1 Contexto

Personas: operador de sala, supervisor de seguridad, gerencia, analista, auditor, administrador y la pantalla de sala.

Vigía lee archivos de campo. Puede consultar a Gemini solo si el proveedor está configurado, hay clave y hay red. Puede dejar avisos en correo o en `storage/outbox/`. El asistente es un módulo del monolito: no emite avisos ni órdenes de evacuación, no escribe SQL y no recibe la base en el prompt. Las cifras salen de herramientas que llaman a los servicios ya existentes.

### 7.2 Contenedores de desarrollo

`docker-compose.yml`:

| Servicio | Puerto en el host | Notas |
|---|---|---|
| App | 8000 | Gunicorn. Un cambio de Python montado exige `docker compose restart app` |
| PostgreSQL 15 | 5433 → 5432 | Base `proyecto_gases`. Pruebas: `proyecto_gases_test` |
| MLflow | 5000 | Seguimiento. `mlruns/` es local |

El navegador solo habla con FastAPI. Recursos de interfaz en `app/static/`: Archivo, IBM Plex Mono solo en Laboratorio y Calidad, ECharts 5, htmx, sprite Lucide. Sin CDN.

### 7.3 Módulos

Registrados en `app/main.py`: auth, interfaz (`ui_router`), API del tablero, users, roles, ingestion, ml_training, forecasting, catalog, alerts, assistant, stakeholders, audit, reports.

Cadena de datos: `sensors_ingestion` → `ml_training` → `forecasting` → `alerts` → `stakeholders`. El tablero, los informes y la auditoría leen esa cadena. `ml_core/forecasting` es la librería que el módulo de pronóstico invoca. `assistant` no tiene SQL propio.

Cada módulo de negocio apunta a `models.py`, `schemas.py`, `repository.py` si hay acceso a datos, `service.py` y `router.py`. Auth usa los modelos de users. Dashboard no tiene modelos propios. Audit no tiene schemas ni repository en el inventario de `CONTEXTO_SISTEMA.md` §4. Assistant no está en esa tabla de inventario; sí está registrado en `app/main.py` desde el Plan 26.

Al arrancar, la aplicación hidrata el catálogo de gases, reconstruye el índice del manual, y enciende el scheduler del inbox y el del pronóstico.

### 7.4 Zoo vigente y zoo retirado

Vigente, en `ml_core/forecasting/adapters/`:

| Clave | Familia | Papel |
|---|---|---|
| persistencia | baseline | Último valor. Denominador del MASE. Siempre entra a la comparación |
| ets | baseline | Suavizamiento exponencial |
| lgbm_q | tabular | LightGBM cuantílico |
| lstm | recurrente | Comprometido en el anteproyecto. El `fit` actual no entrena |
| tft | transformer | Candidato supervisado del Plan 17. El `fit` actual no entrena |
| patchtst | transformer | Ablación. El `fit` actual no entrena |
| itransformer | transformer | Ablación. El `fit` actual no entrena |
| chronos | fundacional | Chronos-Bolt. Sin pesos locales |
| chronos2 | fundacional | Chronos. Sin pesos locales |
| timesfm | fundacional | Sin pesos locales |
| ttm | fundacional | Tiny Time Mixer. Sin pesos locales |

Reglas del Plan 17 que el código declara:

- Quien no baje de MASE 1 frente a la persistencia no se promueve.
- Cada modelo entrega cuantiles. Si el modelo es puntual, el intervalo se completa por conformal.
- Un aviso confirmado nace de la regla dura cuando la lectura ya cruzó el límite, sin pasar por el modelo.
- El aviso anticipado usa el pronóstico, con persistencia de la decisión e histéresis.
- La promoción es explícita y queda en `audit_log`.
- Sin modelo en producción, la interfaz dice que solo muestra lo que marcan los sensores.
- El último bloque real no entra al ajuste. `train_end + embargo < issued_at`.

`planes/CONTEXTO_SISTEMA.md` §8.3.1 todavía lista otro catálogo de diez algoritmos (regresión logística, árbol, bosque, XGBoost, SVM, MLP, LSTM, GRU, transformer, CNN 1D) con tareas de clasificación y regresión, horizonte por defecto de 7,5 minutos y etiqueta `evento_final`. Ese es el camino anterior. La bitácora del 2026-11-02 lo movió a `legacy/` y el servicio de entrenamiento vigente rechaza clasificación y regresión a favor de `task=forecast`. No se usan esas filas como resultado actual.

Horizontes del problema vigente: 6, 12 y 18 minutos. Cuantiles persistidos: q10, q50, q90 y q95. En la pantalla, q50 se lee «se espera alrededor de» y la banda q10–q90 se lee «podría estar entre».

### 7.5 Semántica de `/` (Hoy)

`banner_level` es el máximo de `status_key` sobre las tarjetas visibles, con orden `evacuar` > `actuar` > `vigilar` > `normal`. El conteo de atención es el número de `site_id` distintos cuyo estado está en {`vigilar`, `actuar`, `evacuar`}. Scope vacío → `banner_level = sin_datos`.

`risk_level` de cada sensor, en `dashboard/service.py`: aviso abierto (`abierta` o `reconocida`) si existe; si no, `forecast.status_level`; si no, `NORMAL`. El valor «Ahora» es `gas_readings.leyendo` de `max(tiempo_inicio)`, no el reloj de pared. q50 del último `forecast` se presenta como expectativa; si no hay forecast, `copy.NO_MODEL`.

El gráfico `chart_now_and_next` parte en `reference_time` (último dato del sensor). Serie `measured`: última hora relativa a esa referencia. Serie `expected`: q50 por horizonte. Banda: q10–q90. Líneas horizontales: umbrales del gas. `data_until` anterior a hoy marca la vista como histórica.

Máquina de estados del aviso, independiente del nivel de gas: `abierta` → `reconocida` (`acknowledge`, no cierra) → `resuelta` (`resolve` + `resolution_note`).

## 8. Modelo de datos

Esquema v2. La revisión más nueva en `migrations/versions/` es `e3f4a5b6c7d8` (`assistant_turns` y `assistant_feedback`), y revisa `d2e3f4a5b6c7`. `CONTEXTO_SISTEMA.md` §3 y §15 se quedaron en revisiones anteriores (`c1d2e3f4a5b6` y `d2e3f4a5b6c7`). La cabeza real de una base es la que devuelva `alembic current` en esa base, no este párrafo.

Cadena de archivos de migración:

`0001_init` → `f2b543b2597b` auth → `3d0bc22f046c` sensores → `3984deaeebee` entrenamiento → `33a39369ffe4` alertas → `c2be2667ab48` contactos → `51e28c39eed2` informes → `a1b2c3d4e5f6` campos de pronóstico → `b1c2d3e4f5a6` catálogo → `b2c3d4e5f6a7` calidad → `b3c4d5e6f7a8` prohibición de sintéticos → `b4c5d6e7f8a9` rejilla y eventos → `b5c6d7e8f9a0` evaluaciones → `b6c7d8e9f0a1` explicaciones → `b7c8d9e0f1a2` desenlace de avisos → `b8c9d0e1f2a3` acceso v2 → `b9d0e1f2a3b4` retira `predictions` → `c1d2e3f4a5b6` acceso v3 → `d2e3f4a5b6c7` equipos, umbrales, `benchmark_runs` y `backtest_forecasts` → `e3f4a5b6c7d8` turnos del asistente.

Nunca se crea el esquema con `Base.metadata.create_all()`.

### 8.1 Tablas

Acceso: `users`, `user_roles`, `roles`, `role_permissions`, `permissions`, `user_site_scopes`, `refresh_tokens`, `password_reset_tokens`, `user_invitations`, `kiosk_devices`.

Catálogo: `gas_types`, `normative_thresholds`, `app_settings`.

Datos: `sites`, `sensors`, `etl_runs`, `etl_run_steps`, `gas_readings`, `data_quality_issues`, `reading_grid`, `threshold_events`.

Modelos: `model_registry`, `model_evaluations`, `training_jobs`, y desde el Plan 25 `benchmark_runs` y `backtest_forecasts`.

Pronóstico y avisos: `forecasts`, `forecast_quantiles`, `forecast_explanations`, `alerts`, `alert_outcomes`, `alert_notifications`, `stakeholders`, `stakeholder_user`, `stakeholder_subscriptions`.

Salidas: `reports`, `audit_log`.

Asistente: `assistant_turns`, `assistant_feedback`.

Vista: `missed_events_v`, episodios de `threshold_events` sin un aviso previo acertado.

### 8.2 Campos que importan para no confundir tablas

| Tabla | Qué guarda |
|---|---|
| `users` | Correo único, hash, nombre, activo, intentos, bloqueo, último ingreso, cambio obligatorio, campos TOTP |
| `user_site_scopes` | Zonas de una persona. Sin filas y con un rol que lo permita, ve todos los sitios. Un operador sin zonas no ve lecturas |
| `gas_types` | Código, nombre, unidad canónica, LIE, máximo físico, tasa máxima por minuto, prioridad |
| `normative_thresholds` | Gas, nivel, dirección, valor, métrica, tipo de sitio, artículo, verificado, vigencia. La unicidad en el código es gas + nivel + métrica + dirección + tipo de sitio + `valid_from` |
| `sensors` | Sitio, código, gas, unidad. Único el par código + gas |
| `gas_readings` | Lectura, valor canónico, calidad, inicio. Único el par sensor + inicio. Check `is_synthetic = false` |
| `reading_grid` | Clave sensor + instante, valor, si fue imputado, si falta. Es la entrada de los modelos |
| `forecasts` | Sensor, modelo, instante de emisión, nivel, posibilidad de cruce, confianza. Único sensor + modelo + instante |
| `forecast_quantiles` | Horizonte y q10, q50, q90, q95 |
| `alerts` | Puede colgar de un pronóstico o de una lectura. `kind` es `anticipado` o `confirmado`. Estado `abierta`, `reconocida` o `resuelta` |
| `alert_outcomes` | Si el aviso fue a tiempo, el episodio asociado y los minutos de anticipación |
| `model_registry` | Nombre, versión, algoritmo, familia, especificación, calibración, puntaje de selección, estado, alcance |
| `assistant_turns` | Pregunta, herramientas, respuesta, proveedor, latencia, si la cifra estaba anclada a evidencia |

En PostgreSQL no se guardan, de las 15 columnas del CSV, Descripción, Número de Periodo, Factor de Respuesta ni Factor. Sí se guardan leyendo, unidad, STEL, TWA, alarma, temperatura, tiempos, sintético y archivo de origen.

Códigos de gas: CH4, CO, H2S, CO2, O2, NO2, UNKNOWN. Alias de metano: LEL, LEL(CH4), gas combustible, METANO. Prioridad de la tesis en el catálogo: CH4, CO, H2S.

## 9. Personas, permisos y entrada

Permisos canónicos, sembrados por `scripts/seed_roles_permissions.py`: `status.view`, `alerts.view`, `alerts.acknowledge`, `alerts.resolve`, `history.view`, `reliability.view`, `reports.export`, `thresholds.manage`, `stakeholders.manage`, `data.upload`, `data.quality.view`, `models.train`, `models.promote`, `users.manage`, `roles.manage`, `kiosk.manage`, `audit.view`.

Siguen en la base, como alias: `predictions.view`, `sensors.manage`, `dashboard.view_all_sites`.

| Rol visible | Código | Entra en | Ve |
|---|---|---|---|
| Administrador | `admin` | `/` | Todos los permisos |
| Supervisor de seguridad | `supervisor_seguridad` | `/` | Estado, avisos, límites, contactos, informes, sala |
| Operador de sala | `operador` | `/` | Estado, avisos e historial de sus zonas. Puede marcar y cerrar avisos |
| Gerencia | `gerencia` | `/resumen` | Resumen, confiabilidad, informes de lectura |
| Analista de datos | `analista` | panel de analista | Cargar datos, calidad, laboratorio, promover |
| Auditor | `auditor` | `/bitacora` | Lectura, calidad y bitácora |

Quien entrena no aprueba umbrales, salvo el administrador. El menú se arma por permisos. El aterrizaje de `/` sí mira el rol.

Acceso de desarrollo: `admin@vigia.local` y la contraseña de `SUPERADMIN_PASSWORD` en `.env`. El valor no se copia a documentos. En la base de desarrollo no deben quedar correos `@example.com`. Esos correos son de la base de pruebas.

Sesión: access JWT de 15 minutos en cookie `access_token`; refresh opaco de 8 horas en `refresh_token`, con rotación. Cinco fallos bloquean 15 minutos. Contraseña de 12 o más caracteres, fuera de la lista de comunes. Invitación de 72 horas. Recuperación de 30 minutos. TOTP opcional. El kiosco entra por `/sala?kiosk=` con el token hasheado. `GET` con la clave en la URL redirige a `/ingresar` limpio. `POST /ingresar` exige CSRF.

## 10. Rutas que ve una persona

Las rutas en inglés redirigen a las españolas.

| Ruta | Qué es |
|---|---|
| `/ingresar` | Entrada |
| `/` | Hoy |
| `/avisos`, `/avisos/{id}` | Lista y ficha |
| `/zonas`, `/sensores/{id}` | Equipos |
| `/historial` | Serie de un periodo |
| `/turno` | Línea de tiempo de un día |
| `/informes` | PDF y Excel |
| `/confiabilidad` | Tres cifras, solo si hay avisos evaluados |
| `/resumen` | Gerencia |
| `/datos/cargar`, `/datos/calidad` | Carga y marcas de calidad |
| `/ajustes/limites` | Límites |
| `/laboratorio` y subrutas | Área técnica |
| `/equipo`, `/roles` | Personas |
| `/contactos` | A quién avisar |
| `/bitacora` | Quién hizo qué |
| `/mi-cuenta` | Clave, TOTP, sesiones |
| `/pantallas`, `/sala` | Preparar y ver la sala |
| `/ayuda` | Manual dentro de la plataforma |
| `/health` | Sin sesión |
| `/docs` | OpenAPI |

APIs de trabajo, además de la interfaz: `/auth/*`, `/api/users`, `/api/roles`, `/api/ingestion/upload`, `/api/ml/train` y `/api/ml/models/{id}/promote`, `/api/forecasts`, `/api/alerts/{id}/acknowledge` y `/resolve`, `/api/stakeholders`, `/api/reports`, `/api/audit`, `/dashboard/api/*`. Borrar un usuario es baja lógica.

## 11. Capa de presentación

Marca: Vigía. Los strings de UI salen solo de `app/shared/copy.py`. El estado interno `{normal, vigilar, actuar, evacuar, sin_datos}` se renderiza como {Normal, Vigilar, Actuar ya, Evacuar, Sin datos} con ícono y token `--st-*`. Esos tokens no se usan en botones.

`FORBIDDEN_TERMS` bloquea en HTML operativo: modelo, algoritmo, predicción, probabilidad, cuantil, recall, precisión, F1, RMSE, MAE, MASE, ETL, LSTM, TFT y el resto de la tupla. `/laboratorio/*` y `/datos/calidad` quedan fuera de esa regla y muestran el banner de área técnica. Formato numérico es-CO, timezone `America/Bogota`.

`/sala` es la misma proyección que `/` (fragmento Hoy) a escala de kiosco. No escribe estado ni avisos.

Mapeo de presentación del pronóstico: q50 → «se espera alrededor de»; intervalo [q10, q90] → «podría estar entre»; P(cruce) → posibilidad alta / media / baja (`copy.possibility`, corte π = 0,55 y π/2).

## 12. Arranque

Requisitos: Python 3.11+ y Docker.

Con Docker, desde la raíz, después de copiar `.env.example` a `.env`:

```bash
docker compose up -d --build
```

La interfaz queda en `http://localhost:8000/ingresar`. Salud: `http://localhost:8000/health`.

En el host, con la base del compose: `alembic upgrade head`, `python scripts/seed_roles_permissions.py`, `python scripts/seed_catalog.py`, `python scripts/create_superadmin.py`, `python scripts/load_processed_dataset.py --consolidado`, y `uvicorn app.main:app --reload`. `DATABASE_URL` del host usa `localhost:5433`. Dentro de Compose la app habla con `db:5432`.

Reconstruir la plataforma de datos reales, idempotente: `python scripts/build_real_platform.py --confirm`.

Variables que importan: `DATABASE_URL`, `TEST_DATABASE_URL`, `JWT_SECRET`, `MLFLOW_TRACKING_URI`, `ASSISTANT_PROVIDER` (`gemini`, `ollama` o `off`), `NOTIFICATIONS_DRY_RUN`, `SUPERADMIN_EMAIL`, `SUPERADMIN_PASSWORD`, `ETL_INBOX_ENABLED`.

## 13. Pruebas

`tests/conftest.py` apunta a `TEST_DATABASE_URL` y aborta si esa URL es la de desarrollo. Cada prueba corre en una transacción que se revierte. Comando de conjunto: `python scripts/verify.py` con `--fast`, `--full` o `--plan N`. Hay `pytest.ini` en la raíz. `CONTEXTO_SISTEMA.md` §3 dice que no existe; el archivo sí está.

Marcadores: `plan15` a `plan26`, `e2e`, `slow`, `live_llm`. La prueba de Gemini no entra en `verify --plan 26`.

Carpetas: `tests/unit`, `tests/integration`, `tests/guards` (causalidad, sintéticos, walk-forward, conformal), `tests/ui`, `tests/e2e`, `tests/perf`. El CI está en `.github/workflows/verify.yml`.

La bitácora anota verdes parciales (`--plan 18`, `--plan 19`, `--plan 26` con 16 pruebas, lenguaje del Plan 18). No anota un `--full` verde después de la reconstrucción con datos reales. El cierre E2E del Plan 25 quedó bloqueado por la ausencia de `chromium_headless_shell`.

## 14. Lo que falta, en una lista

Datos

- Export del datalog por intervalo. Sin él la mediana del tramo sigue en 2 pasos y la ventana en 12.
- Firma del director en G0 y el visto de G1.
- Confirmación humana de cada límite (`verified=true`) con el artículo, la métrica y el tipo de sitio.
- Sitios reales en el CSV. Hoy muchos quedan en «Sin sitio asignado».
- Parser de `alarmReport` y del historial MX6. No están y no forman parte del alcance actual.

Modelos

- Entrenamiento nativo de LSTM, TFT, PatchTST e iTransformer, o pesos cargables.
- Pesos locales de Chronos, TimesFM y TTM, y el código que los use en `predict_quantiles`.
- Una corrida de validación sobre la serie completa, no sobre 800 filas ni sobre la serie sintética de respaldo.
- Métricas del zoo más allá de persistencia y ETS.
- La prueba final de diciembre de 2025, solo después de cerrar la validación.
- Promoción explícita, si algún modelo baja de MASE 1 y cumple la cobertura. Hoy no se pidió.
- Ablaciones de ventana, covariables, ajuste fino, alcance y pérdida.
- Métricas de aviso por episodio donde haya al menos 10 inicios, con intervalo. En metano no se pueden calcular.
- Que la reproducción histórica escriba los avisos en `alerts`, para que Turno y Confiabilidad no dependan de una corrida vacía.

Producto

- Corte de la mina en Hoy.
- Capturas alineadas con el kit y sesiones SUS en mina.
- `verify --full` en verde, incluido el E2E de gráficas.
- Despliegue de nube del Plan 09.
- k6, pip-audit, HSTS de producción y respaldos.
- Medición de Gemini, solo con autorización escrita, o un modelo local.
- Rol de base `vigia_assistant_ro`.
- Capturas reales dentro del manual.
- El Word y el Excel de resultados que encarga el Plan 32 (`docs/diseno/word/03_resultados.docx`). No están en el repositorio.

## 15. Dónde sigue cada tema

| Tema | Archivo que manda |
|---|---|
| Mapa de código y convenciones de trabajo | `planes/CONTEXTO_SISTEMA.md` |
| Orden de planes | `planes/00_INDICE_Y_ROADMAP.md` |
| Qué se ejecutó, con fecha | `planes/BITACORA_BUCLE.md` |
| Contrato de la documentación de diseño | `documentacion/claude/27_PAQUETE_DISENO_INDICE.md` |
| Diagramas | `documentacion/claude/28_DIAGRAMAS_ARQUITECTURA_Y_FLUJOS.md` |
| Requisitos | `documentacion/claude/29_REQUISITOS_HISTORIAS_Y_CASOS_DE_USO.md` |
| Diccionario de datos | `documentacion/claude/30_MODELO_Y_DICCIONARIO_DE_DATOS.md` |
| Diseño del pronóstico | `documentacion/claude/31_DISENO_SOLUCION_IA.md` y `planes/17_MODELOS_TRANSFORMER_Y_EVALUACION.md` |
| Cómo citar resultados | `documentacion/claude/32_DOCUMENTACION_DE_RESULTADOS.md` |
| Manual de quien opera | `docs/manual/` |
| Manual de quien programa | `documentacion/claude/34_MANUAL_DEL_PROGRAMADOR.md` |
| Inventario de lecturas | `reports/diagnostico/diagnostico_datos.md` |
| Ventana y modelos excluidos | `reports/diagnostico/diagnostico_g1.md` |
| Horizontes | `reports/diagnostico/g0_decision.json` |
| Métricas escritas | `reports/thesis/benchmark.json` |
| Reconstrucción | `reports/real_platform/build_report.md` |
| Asistente | `reports/assistant/eval_2026-11-09.md` |
| Lo que el Plan 23 todavía exige | `planes/23_AUDITORIA_Y_AJUSTES_TESIS.md` |
| Arranque corto | `README.md` y `CLAUDE.md` |

## 17. Diccionario de columnas

Cada fila sale de `app/modules/*/models.py`. No es un volcado de la base: es el esquema que el código declara. `sites` no tiene coordenadas de mapa; el corte de la mina sigue pendiente y no hay columnas `map_x` ni `map_y`.

### Acceso

| Tabla | Columnas |
|---|---|
| `users` | `id`, `email` único, `password_hash`, `full_name`, `is_active`, `failed_login_count`, `locked_until`, `last_login_at`, `must_change_password`, `password_changed_at`, `totp_secret_enc`, `totp_enabled`, `totp_backup_hashes`, `created_at`, `updated_at` |
| `user_roles` | `user_id`, `role_id` |
| `roles` | `id`, `name` único, `description` |
| `permissions` | `id`, `code` único, `description` |
| `role_permissions` | `role_id`, `permission_id` |
| `user_site_scopes` | `id`, `user_id`, `site_id` |
| `user_instrument_scopes` | `id`, `user_id`, `instrument_id` |
| `refresh_tokens` | `id`, `user_id`, `token_hash` único, `expires_at`, `revoked_at`, `user_agent`, `ip`, `last_used_at` |
| `password_reset_tokens` | `id`, `user_id`, `token_hash`, `expires_at`, `used_at` |
| `user_invitations` | `id`, `email`, `role_ids`, `site_ids`, `full_name`, `token_hash`, `invited_by`, `expires_at`, `accepted_at` |
| `kiosk_devices` | `id`, `name`, `token_hash`, `site_ids`, `created_by`, `revoked_at`, `last_seen_at`, `created_at` |

### Catálogo

| Tabla | Columnas |
|---|---|
| `gas_types` | `code`, `display_name`, `plain_description`, `canonical_unit`, `lel_percent_vol`, `physical_max`, `max_rate_per_min`, `priority`, `is_active` |
| `normative_thresholds` | `id`, `gas_code`, `level`, `direction`, `value`, `metric`, `site_kind`, `kind`, `article`, `source_reference`, `verified`, `valid_from`, `created_by` |
| `app_settings` | `key`, `value` JSON, `updated_at` |

### Datos de campo

| Tabla | Columnas |
|---|---|
| `instruments` | `id`, `serial` único, `model`, `first_seen`, `last_seen`, `assigned_to`, `site_id` |
| `sites` | `id`, `name` único, `description` |
| `sensors` | `id`, `site_id`, `code`, `gas_type`, `unit`, `display_name`, `kind`, `location_note`, `is_active`, `instrument_id` |
| `etl_runs` | `id`, `started_at`, `finished_at`, `status`, `rows_ingested`, `rows_rejected`, `source_files`, `log`, `triggered_by_user_id` |
| `etl_run_steps` | `id`, `etl_run_id`, `step`, `rows_in`, `rows_out`, `rows_rejected`, `duration_ms`, `details` |
| `gas_readings` | `id`, `sensor_id`, `leyendo`, `unidad`, `stel_max`, `twa_max`, `alarma`, `temperatura`, `tiempo_inicio`, `tiempo_fin`, `is_synthetic`, `source_file`, `etl_run_id`, `value_canonical`, `unit_canonical`, `quality_status`, `created_at` |
| `data_quality_issues` | `id`, `gas_reading_id`, `sensor_id`, `etl_run_id`, `code`, `severity`, `detected_at`, `details` |
| `reading_grid` | `sensor_id` + `ts` como clave, `value`, `is_imputed`, `is_missing`, `source_etl_run_id`, `twa_8h`, `stel_15min` |
| `threshold_events` | `id`, `sensor_id`, `gas_code`, `level`, `threshold_id`, `started_at`, `ended_at`, `peak_value`, `peak_at`, `detected_by` |

### Modelos, pronóstico y avisos

| Tabla | Columnas |
|---|---|
| `model_registry` | `id`, `name`, `version`, `algorithm`, `family`, `params`, `metrics`, `problem_spec`, `calibration`, `selection_score`, `mlflow_run_id`, `artifact_uri`, `status`, `scope`, `trained_by`, `trained_at` |
| `training_jobs` | `id`, `model_registry_id`, `status`, `dataset_version`, `started_at`, `finished_at`, `triggered_by`, `params`, `log` |
| `model_evaluations` | `id`, `model_id`, `fold_index`, `fold_spec`, `gas_code`, `horizon_min`, `forecast_metrics`, `event_metrics`, `is_final_test` |
| `benchmark_runs` | `id`, `commit_sha`, `data_hash`, `seed`, `g1_params`, `created_at`, `is_final_test`, `manifest`, `selection_report`, `promoted_algorithm` |
| `backtest_forecasts` | `id`, `run_id`, `model_key`, `fold_index`, `sensor_id`, `issued_at`, `horizon_min`, `q10`, `q50`, `q90`, `q95`, `y_true`, `decided_level`, `train_end` |
| `forecasts` | `id`, `sensor_id`, `model_id`, `issued_at`, `status_level`, `exceed_prob`, `confidence`, `latency_ms`, `created_at` |
| `forecast_quantiles` | `id`, `forecast_id`, `horizon_min`, `q10`, `q50`, `q90`, `q95` |
| `forecast_explanations` | `id`, `forecast_id`, `method`, `factors`, `plain_text` |
| `alerts` | `id`, `forecast_id`, `gas_reading_id`, `sensor_id`, `kind`, `level`, `threshold_id`, `expected_at`, `message`, `recommendation`, `plain_message`, `plain_recommendation`, `status`, `created_at`, `acknowledged_by`, `acknowledged_at`, `resolved_by`, `resolved_at`, `resolution_note`, `origin`, `human_handled`, `closed_by` |
| `alert_outcomes` | `alert_id`, `outcome`, `event_id`, `lead_minutes`, `evaluated_at` |
| `stakeholders` | `id`, `name`, `type`, `organization`, `email`, `phone`, `notify_channels`, `created_at` |
| `stakeholder_user` | `stakeholder_id`, `user_id` |
| `stakeholder_subscriptions` | `id`, `stakeholder_id`, `site_id`, `sensor_id`, `min_level`, `created_at` |
| `alert_notifications` | `id`, `alert_id`, `stakeholder_id`, `channel`, `status`, `sent_at`, `error` |

### Salidas y asistente

| Tabla | Columnas |
|---|---|
| `reports` | `id`, `type`, `period_start`, `period_end`, `file_path`, `generated_by`, `created_at` |
| `audit_log` | `id`, `user_id`, `action`, `resource_type`, `resource_id`, `metadata`, `details`, `created_at` |
| `assistant_turns` | `id`, `user_id`, `role`, `question`, `tools`, `artifacts`, `grounded`, `in_scope`, `latency_ms`, `provider`, `model`, `tokens`, `reply`, `created_at` |
| `assistant_feedback` | `id`, `turn_id`, `useful`, `comment`, `created_at` |

`is_synthetic` en `gas_readings` tiene un check que solo admite falso. Los códigos de calidad que la corrida documentada escribió son `fuera_de_rango_fisico`, `hueco`, `salto_imposible` y `valor_congelado`.

## 18. Decisión: de cuantiles a `alerts.level`

Implementación: `ml_core/forecasting/decision.py`.

1. El adaptador emite (q10, q50, q90, q95) por horizonte.
2. `exceedance_probability` interpola una CDF empírica lineal sobre los nudos τ ∈ {0,10, 0,50, 0,90, 0,95}. Si `direction=above`, P(C ≥ θ) = 1 − F̂(θ). Si `direction=below`, P(C ≤ θ) = F̂(θ).
3. `DecisionState.pi` por defecto: vigilar 0,40, actuar 0,55, evacuar 0,75. El nivel se propone si P ≥ π.
4. Persistencia: `persistence_steps = 2`. Histéresis: el nivel activo se mantiene mientras P ≥ 0,8 · π. Evita conmutación de un paso.
5. `confirmed_level(y_t, thresholds)` dispara `kind=confirmado` si y_t ya viola el umbral. No consulta el forecast. `operational_level` devuelve el de mayor `LEVEL_RANK` entre confirmado y anticipado. Orden: normal < vigilar < actuar < evacuar.
6. `fit_decision_threshold` puede reestimar π maximizando recall sujeto a falsas alarmas por turno. No hay artefacto de esa calibración en `reports/`.

La regla está en código. No consta el π efectivo de una corrida real ni el conteo de avisos `anticipado` escritos el 2026-11-08. La bitácora indica que el backtest histórico no materializa todos los avisos en `alerts`.

## 19. Asistente, herramienta por herramienta

Módulo `app/modules/assistant/`. Trece herramientas en `tools/registry.py`. El modelo solo puede llamar a las que el rol permite. No hay herramienta para cerrar un aviso, cambiar un límite ni promover un modelo. La única escritura es `generar_informe`, que pasa por el módulo de reportes.

| Herramienta | Permiso | Contrato |
|---|---|---|
| `resumen_estado` | `status.view` | Último `leyendo`, `status_level` y q50 por sensor visible |
| `buscar_avisos` | `alerts.view` | Filtro de `alerts` por periodo, nivel, estado y origen |
| `detalle_aviso` | `alerts.view` | Ficha: `plain_message`, lectura, q esperado, umbral, `alert_outcomes` |
| `serie_gas` | `history.view` | Agregados de la serie. No devuelve el microdato completo |
| `estadisticas_gas` | `history.view` | min, max, media y conteo de superaciones |
| `episodios` | `history.view` | `threshold_events`: inicio, fin, pico, aviso previo |
| `confiabilidad` | `reliability.view` | recall, lead time y FA/turno desde `alert_outcomes`, con n |
| `limites` | `status.view` | `normative_thresholds`: valor, `metric`, `article`, `verified` |
| `cobertura_datos` | `status.view` | Rango temporal, sensores, gases y `data_quality_issues` |
| `resultados_modelos` | `models.train` | Filas de benchmark y `selection_report` |
| `crear_grafico` | ninguno | Gráfico a partir de un `chart_id` ya emitido en el turno |
| `generar_informe` | `reports.export` | PDF/XLSX vía `reports`. Única herramienta con efecto de escritura |
| `buscar_manual` | ninguno | Recuperación BM25 sobre `docs/manual/` |

Parámetros que el modelo puede pedir, tipados en `tools/params.py`: fechas `AAAA-MM-DD` en hora de Bogotá; nivel `vigilar`, `actuar`, `evacuar` o `normal`; estado del aviso `abierta`, `reconocida` o `resuelta`; origen `en_vivo` o `historico`; agregación `6min`, `hora` o `dia`; métrica `valor`, `twa_8h` o `stel_15min`; informe `avisos_periodo`, `resumen_gerencia`, `confiabilidad` o `comportamiento_gas`, en `pdf` o `xlsx`. No puede enviar SQL ni un nombre de tabla.

Ciclo de `run_turn` (`service.py`, `grounding.py`, `prompts.py`):

1. Match contra `app_settings.assistant_emergency_terms` → no hay llamada al proveedor. Respuesta fija de protocolo. El LLM no clasifica la emergencia.
2. `ASSISTANT_PROVIDER=off` o sin credencial → HTTP 503 con `copy.ASK_OFFLINE`. El resto de routers sigue.
3. El proveedor (`fake` en eval, `gemini` o `ollama`) devuelve `functionCall`. El system prompt no incluye filas de la mina. Prohíbe cifras, fechas y equipos que no vengan de una herramienta del turno. La salida exigida es JSON `{reply, in_scope, include}`.
4. `check_reply` extrae números del texto y los contrasta con el conjunto autorizado de la evidencia. Si falla, un reintento. Si vuelve a fallar, plantilla. Roles `operador`, `supervisor_seguridad` y `gerencia` pasan además por el filtro de `FORBIDDEN_TERMS`.
5. Persistencia en `assistant_turns` (`grounded`, `in_scope`, `tools`, `latency_ms`, `provider`). Feedback binario en `assistant_feedback.useful`.
6. Cadena Gemini declarada: `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.0-flash` (`ASSISTANT_GEMINI_MODELS`). Cero evaluaciones `live_llm`.

El índice de ayuda es BM25 sobre `docs/manual/`, expuesto en `/ayuda` y `/ayuda/{slug}`.

## 20. Manual de operación, capítulo por capítulo

Los textos completos están en `docs/manual/`. Esto es lo que cada uno afirma.

El manual operativo evita el léxico del modelo. Aquí se anota el concepto técnico que cada capítulo cubre.

| Archivo | Concepto técnico que explica, en lenguaje de UI |
|---|---|
| `00_que_es_vigia.md` | Separación entre monitoreo y decisión de acceso. `kind` anticipado vs confirmado. `data_until` como marca de histórico |
| `01_ingresar.md` | Sesión, TOTP, reset y revocación de `refresh_tokens` |
| `02_hoy.md` | `status_key` con etiqueta. Serie medida vs q50. `/sala` es solo lectura |
| `03_avisos.md` | `acknowledge` no transiciona a `resuelta`. `resolve` exige nota. El asistente no tiene tool de cierre |
| `04_equipos_historial.md` | Serie por sensor, gas y ventana temporal. Export condicionado a `reports.export` |
| `05_revisar_un_turno.md` | Timeline de `gas_readings` y `alerts` de un día |
| `06_confiabilidad.md` | Recall («de cada 10»), lead time y FA/turno. n insuficiente → sin cifra |
| `07_limites.md` | `normative_thresholds`: instantáneo, `twa_8h`, `stel_15min`. Escritura solo en `/ajustes/limites` |
| `08_informes.md` | Generación PDF/XLSX con periodo y `data_until` en el pie |
| `09_preguntar.md` | El asistente no muta umbrales ni avisos. Degradación si no hay proveedor |
| `10_equipo_y_roles.md` | RBAC, `user_site_scopes`, kiosco, stakeholders, `audit_log` |
| `11_cargar_datos.md` | Rechazo de esquema y `data_quality_issues` sin imputar el valor marcado |
| `12_laboratorio.md` | Única vista que nombra modelo y entrenamiento. `models.train` no implica `models.promote` |
| `13_preguntas_frecuentes.md` | El color no es la decisión. El eje temporal está acotado por el último dato |

## 21. Diagramas que el Plan 28 especifica

Los `.drawio` de `docs/diseno/drawio/` no están generados. La especificación sí, en `documentacion/claude/28_DIAGRAMAS_ARQUITECTURA_Y_FLUJOS.md`.

| Archivo pedido | Qué debe mostrar |
|---|---|
| `01_contexto_c4` | Personas, Vigía, archivos de campo, Gemini opcional, correo o `storage/outbox/`. Sin enlace en vivo al detector |
| `02_contenedores_c4` | Navegador, FastAPI, PostgreSQL, MLflow. El compose no monta `data/` |
| `03_componentes_c4` | Módulos de `app/main.py` y `ml_core` fuera del cuadro de FastAPI |
| `04_despliegue_borde` | Un equipo en bocamina. La nube del Plan 09 en un nodo punteado y pendiente |
| `05_secuencia_autenticacion` | CSRF, POST, bloqueo a los 5 fallos, cookies, aterrizaje por rol |
| `06_flujo_etl` | E1 a E6 y los tres disparadores: API, inbox y script |
| `07_secuencia_pronostico_aviso` | Cuantiles, decisión, confirmado sin modelo, anticipado con modelo, notificación solo en vivo, desenlace posterior |
| `08` a `11` | El plan sigue con informes, asistente, estados del aviso y mapa de navegación. El asistente, donde aparezca, lleva la nota de que no emite avisos ni órdenes de evacuación |

Estados del aviso en ese plan: `abierta`, `reconocida`, `resuelta`.

## 22. Notebooks y camino retirado

La aplicación no importa notebooks. Están en `notebooks/` como investigación:

| Archivo | Papel |
|---|---|
| `01_exploracion.ipynb` | Explora `data/raw` y arma los CSV por mes |
| `ETL_–_Carga_y_limpieza_de_datos_.ipynb` | ETL de investigación |
| `02_ETL_–_Carga_y_limpieza_de_datos copy.ipynb` | Copia con salidas |
| `03_ETl_PROCESADO.ipynb` | Confirma 13 894 filas en 9 CSV |

`01_exploracion.ipynb` importa un `config.py` de la raíz que ya no existe. No se usan para correr el sistema.

El zoo retirado, en `legacy/` desde el 2026-11-02, es el de clasificación y regresión: regresión logística, árbol, bosque aleatorio, XGBoost, SVM, MLP, LSTM, GRU, transformer y CNN 1D, con etiqueta `evento_final` y horizonte por defecto de 7,5 minutos. El servicio vigente rechaza esas tareas y solo acepta pronóstico. Un modelo `transformer` que estaba marcado en producción se archivó en el Plan 25 F0.

## 23. Lo que sigue sin poder incluirse

Estas piezas no están en el repositorio, así que este documento no puede copiarlas:

- El texto del marco teórico, los objetivos reescritos y las amenazas a la validez. El Plan 23 los pide y siguen en su lista abierta.
- El contenido celda por celda de los notebooks.
- Los archivos `.drawio`, el Word y el Excel de resultados del Plan 32.
- Conteos actuales de filas en PostgreSQL, modelos en MLflow o avisos abiertos hoy. Los números de este archivo son los de los reportes del 8 y 9 de noviembre de 2026.
- La firma del director y el resultado de unas sesiones SUS que no se han hecho.
- Métricas de LSTM, TFT, LightGBM, Chronos, TimesFM y TTM. No existen porque la ventana es de 12 pasos y porque su `fit` no entrena.

## 24. Frase que este documento puede sostener

Hay un monolito edge que persiste 13 894 lecturas reales (`is_synthetic=false`) y pronostica a H = 6, 12 y 18 min. Los umbrales de semilla siguen con `verified=false`. La única evaluación archivada es persistencia contra ETS en `fold-0`, `is_final_test=false`: MASE(ETS) = 0,8601, cobertura empírica del intervalo [q10, q90] = 0,7083 frente a 0,6667 de la persistencia, ambas bajo el 0,90 nominal. El resto del zoo no tiene métrica: la mediana de segmento es 2 pasos, así que `lookback=12` los excluye en G1, y sus `fit` lanzan `ModelUnavailableError`. `promoted_algorithm` no se escribió. G0 no tiene firma.
