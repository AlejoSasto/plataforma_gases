# 24 — Operación completa con datos reales (cero datos demo)

**Objetivo:** cada lectura, pronóstico, aviso, gráfico y cifra de la plataforma sale de los **datos reales de la mina**, con linaje verificable hasta el archivo de origen. Las alertas se generan con el mismo flujo de producción, recorriendo el histórico real en orden cronológico **sin fuga de información**.
**Prerrequisitos:** Plan 23 F2 (umbrales del Decreto 1886), F3 (benchmark real) y F5 (camino viejo retirado). F7 (gráficas) puede ir en paralelo.
**Regla de oro:** si un dato no se puede rastrear hasta un `dls_report` o el consolidado real (con su huella SHA-256), **no existe** para la plataforma.

> Lo único que no es real en este plan es el **reloj**: el sistema recorre el pasado como si fuera el presente para generar los avisos que habría dado. Las lecturas, los modelos, las decisiones y los resultados son reales, y la interfaz lo dice siempre.

---

## 1. Qué cuenta como dato real y qué no

| Permitido | Prohibido |
|-----------|-----------|
| Lecturas del consolidado real y de los `dls_report` cargados por el ETL v2 | Filas `is_synthetic`, clonado de meses, TimeGAN o SMOTE en la base de desarrollo o en la interfaz |
| Pronósticos de modelos entrenados **solo con datos anteriores** al momento pronosticado | Pronósticos sobre periodos que el modelo ya vio al entrenar |
| Avisos generados por el flujo de producción a partir de esas lecturas y pronósticos | Avisos escritos a mano, sembrados o copiados de los mockups |
| Umbrales del Decreto 1886 y umbrales internos **firmados** por la mina | Umbrales inventados sin fuente |
| Usuarios reales creados por invitación o superadmin por variables de entorno | `test.admin@example.com` y demás usuarios de prueba en la base de desarrollo |
| Nombres de equipo derivados del número de serie real | Zonas ficticias ("Frente 3 Sur"), personas ficticias, cifras de ejemplo en los templates |

Las fábricas y la muestra `tests/fixtures/real_sample.csv` siguen existiendo, **solo** en la base de pruebas.

---

## F1 — Limpieza: sacar todo lo demo de la plataforma

1. `scripts/audit_demo_data.py` (solo lectura) revisa la base de desarrollo y el código, y reporta:
   - usuarios con correo `@example.com` u otros de prueba;
   - sitios o sensores sin `etl_run` ni archivo de origen;
   - avisos sin `forecast_id` ni `gas_reading_id`;
   - pronósticos de modelos sin `run_id`;
   - textos de ejemplo en `app/templates/` y `app/shared/copy.py` ("Frente 3 Sur", "Ana Rojas", "Carlos Pinzón", "0,72", "Mina caso de estudio", etc.).
2. `scripts/purge_demo_data.py --confirm` borra lo detectado (con auditoría `data.purge_demo`). Sin `--confirm` es un ensayo.
3. Los templates no llevan cifras ni nombres de ejemplo: todo llega del servicio. `/_componentes` usa datos reales del último periodo o se muestra vacío.
4. El kit de mockups queda en `design/` como referencia visual, **fuera** de `app/static` y sin ruta que lo sirva.
5. El acceso en desarrollo se hace solo con el superadmin de `.env` o con usuarios invitados. Se actualiza `CONTEXTO_SISTEMA.md` §7.
6. Guardias nuevas:
   - `test_no_demo_strings_in_templates` busca en `app/templates` y `copy.py` una lista negra de nombres y cifras del kit;
   - `test_app_does_not_serve_mockups`.

**Definición de terminado F1:** `audit_demo_data.py` sale limpio; guardias en verde; se puede ingresar con el superadmin.

---

## F2 — Identidad real de los equipos (sin zonas inventadas)

Los datos vienen de detectores portátiles con `Sitio` vacío (Plan 23 F1).

1. Tabla `instruments` (migración con `downgrade`): `serial` (único, del `Sensor SN`), `model` (MX6 u otro, si se puede inferir), `first_seen`, `last_seen`, `assigned_to` (nulo hasta que la mina lo informe), `site_id` (nulo).
2. `sensors.instrument_id`: cada sensor de gas pertenece a un instrumento. El ETL E3 lo resuelve.
3. Mientras no exista ubicación real, la interfaz agrupa por **equipo**: "Detector 4521" con sus gases. "Zonas" se renombra a **"Equipos y zonas"** y la vista de zonas solo aparece si hay sitios con datos.
4. El alcance del operador (`user_site_scopes`) admite instrumentos además de sitios: tabla `user_instrument_scopes`.
5. Si la mina entrega el mapeo serial → labor o el sistema de monitoreo fijo, se carga con `scripts/load_instrument_map.py` (CSV firmado). Recién ahí se activan zonas y el corte de la mina.

**Definición de terminado F2:** todos los sensores tienen instrumento; la interfaz no muestra ninguna zona sin respaldo; prueba de alcance por instrumento.

---

## F3 — Flujo único de datos reales, de punta a punta

Un solo comando reconstruye la plataforma desde los archivos reales. Es idempotente y se puede repetir:

```bash
python scripts/build_real_platform.py --confirm      # también: make real
```

| Paso | Qué hace | Salida verificable |
|------|----------|--------------------|
| 1 | `alembic upgrade head` | Head esperado |
| 2 | Semillas: roles, gases, **umbrales del decreto** (Plan 23 F2), ajustes G0 | Conteos |
| 3 | Superadmin desde `.env` | 1 admin |
| 4 | ETL v2 (E1–E6) sobre el consolidado real y los `dls_report` del inbox, con deduplicación SHA-256 | `etl_runs`, `etl_run_steps`, problemas de calidad, incluidas pruebas funcionales |
| 5 | Instrumentos (F2) | `instruments` |
| 6 | Rejilla y series TWA 8 h / STEL 15 min | `reading_grid` |
| 7 | Episodios reales contra el decreto | `threshold_events` por gas y nivel |
| 8 | Benchmark walk-forward con modelos reales (Plan 23 F3); guarda modelos **por pliegue** | `benchmark_runs`, `backtest_forecasts`, `model_evaluations` |
| 9 | Selección del mejor modelo por la regla del Plan 17 §8 y **promoción explícita** (pide confirmación o `--promote`) | Modelo activo con `run_id` |
| 10 | **Reproducción histórica** (F4): pronósticos y avisos del histórico | `forecasts`, `alerts`, `alert_outcomes` con `origin='historico'` |
| 11 | Informe de cierre `reports/real_platform/build_report.md` | Conteos de cada tabla, episodios, avisos y resultados |

Si un paso falla, se detiene y lo dice. Nunca rellena con datos de respaldo.

**Definición de terminado F3:** dos corridas seguidas dejan los mismos conteos; el informe de cierre se genera; ninguna tabla operativa tiene filas sin linaje.

---

## F4 — Reproducción histórica: cómo se generan los avisos con datos reales

### 4.1 Regla de no fuga (lo más importante del plan)

Un aviso en el instante *t* solo puede venir de un modelo que **no vio *t***. Por eso la reproducción usa los **modelos de cada pliegue** del walk-forward, no el modelo final:

| Periodo del histórico | Pronóstico usado |
|-----------------------|------------------|
| Bloque de validación del pliegue *j* | El modelo entrenado en el pliegue *j*, que solo vio datos anteriores (con purga y embargo) |
| Primer bloque (no hay datos previos para entrenar) | Solo **modelos fundacionales en zero-shot**, que no se entrenan con estos datos, con calibración conformal **en línea** (solo residuos pasados). Si no hay fundacional instalado: solo avisos **confirmados** |
| **Prueba final intocable** (último bloque real) | Antes de correr la prueba final: solo avisos **confirmados** y la etiqueta "Periodo reservado para la evaluación final". Después de la corrida única: pronósticos del modelo final congelado |

Cada fila de `forecasts` guarda `model_id`, `fold_index`, `train_end` y `run_id`. Guardia `test_forecast_model_never_saw_target`: para todo pronóstico, `train_end + embargo < issued_at`.

### 4.2 El recorrido

`python -m app.modules.forecasting.replay --run <run_id>` recorre la rejilla real en orden cronológico, paso por paso (6 min, G0). En cada paso y para cada sensor activo en ese momento:

1. Toma la ventana causal de `reading_grid` (solo ≤ *t*).
2. Pronostica cuantiles a 6, 12 y 18 min con el modelo que corresponde (tabla 4.1).
3. Calibra con ACI usando solo residuos pasados.
4. Decide el nivel con la regla fija del Plan 23 F3 y los umbrales vigentes en *t* (`valid_from`), con persistencia e histéresis.
5. Evalúa avisos **confirmados**: la lectura instantánea, el TWA o el STEL en *t* supera el umbral, según su `metric`.
6. Crea o actualiza `alerts` con un aviso por episodio, mensaje y recomendación de `copy.py` y explicación del narrador (factores reales del modelo).
7. Registra la notificación como **"habría notificado a…"**. Para avisos históricos no se envían correos.

Al terminar, el cierre de resultados llena `alert_outcomes` contra `threshold_events`: acertado (con minutos de anticipación), aviso innecesario o episodio no avisado (`missed_events_v`).

### 4.3 Marcas de origen

| Campo | Valores |
|-------|---------|
| `forecasts.origin`, `alerts.origin` | `historico` (reproducción) / `en_vivo` (datos nuevos que llegan de la mina) |
| `alerts.status` para `historico` | Se cierran solos al volver el nivel a normal: `resuelta`, `resolved_by=sistema`, nota "Cierre automático en revisión histórica" |
| `alerts.human_handled` | `false` en históricos. Las cifras de tiempo de respuesta del personal solo usan avisos `en_vivo` |

**Definición de terminado F4:** la reproducción corre sobre todo el histórico real; guardia de no fuga en verde; todos los episodios reales quedan clasificados como avisado, no avisado o falsa alarma; corrida idempotente (UQ).

---

## F5 — Operación en vivo con datos nuevos reales

Cuando la mina entregue datos nuevos (inbox, carga en Cargar datos o el sistema fijo):

1. ETL v2 → rejilla → ciclo de pronóstico con el **modelo activo** → decisión → avisos `en_vivo` → notificaciones reales (si `NOTIFICATIONS_DRY_RUN=false`).
2. Los avisos `en_vivo` sí aparecen como **abiertos** y esperan "Ya lo vi" y "Cerrar aviso" de una persona.
3. Reentrenamiento: cuando los datos nuevos completan un bloque, se agrega un pliegue y se vuelve a correr el benchmark. El modelo activo solo cambia por promoción explícita.

---

## F6 — Interfaz honesta con el tiempo

1. **Fecha de referencia global.** La barra superior muestra siempre "Datos hasta el 11 de diciembre de 2025, 16:40" (`max(ts)` real), y no "hace 40 s" si eso no es cierto. Si llegan datos en vivo, cambia a "Datos al día".
2. **Hoy** muestra el estado **al último dato real**, con encabezado: "Estado según las últimas lecturas recibidas (11 dic 2025, 16:40)". Avisos abiertos: solo los `en_vivo`. Si no hay, el estado vacío lo explica: "No hay avisos abiertos. Los avisos del histórico se ven en Revisar un turno".
3. **Revisar un turno** (Plan 23 F8) lee de la reproducción: se elige fecha y turno reales y se ve el recorrido paso a paso.
4. **Avisos** tiene un filtro de origen: "En vivo" (por defecto) e "Histórico". Cada aviso histórico lleva una marca visible.
5. **Confiabilidad** dice de qué periodo y cuántos episodios sale cada cifra ("Calculado con 59 situaciones reales de ácido sulfhídrico entre sep-2024 y nov-2025"). Si un gas no tiene episodios suficientes, lo dice: "Todavía no hay suficientes situaciones reales de metano para medir esto".
6. **Gráficos:** el eje de tiempo y "Ahora" usan la fecha de referencia (Plan 23 F7, causa 1).
7. Textos nuevos en `copy.py`, con el verificador de lenguaje en verde.

---

## F7 — Trazabilidad visible (para el jurado)

1. En el detalle de cada aviso, un bloque **"De dónde sale este aviso"** (visible para analista, auditor y admin):
   - lectura y archivo de origen con su huella;
   - corrida ETL;
   - pronóstico (modelo, pliegue y fecha de corte del entrenamiento);
   - umbral y artículo del decreto;
   - resultado (acertó o no, y con cuántos minutos).
2. `GET /api/avisos/{id}/linaje` devuelve esa cadena en JSON. Es un anexo reproducible para la tesis.
3. `scripts/export_thesis_evidence.py` exporta en `reports/thesis/evidencia/` las tablas de episodios, avisos, resultados y linaje (CSV) de la corrida promovida.

---

## F8 — Pruebas y guardias

| Prueba | Garantiza |
|--------|-----------|
| `test_no_demo_strings_in_templates` | Ningún nombre ni cifra de los mockups en la app |
| `test_dev_db_has_no_test_users` (en `verify --dev-audit`) | La base de desarrollo no tiene usuarios de prueba |
| `test_every_alert_has_lineage` | Todo aviso tiene lectura o pronóstico, con `etl_run` y archivo de origen |
| `test_forecast_model_never_saw_target` | `train_end + embargo < issued_at` en todo pronóstico |
| `test_final_block_reserved` | No hay avisos anticipados en el bloque de prueba final antes de su corrida única |
| `test_replay_idempotent` | Dos reproducciones dejan los mismos conteos |
| `test_historic_alerts_not_open` | Ningún aviso `historico` aparece como abierto |
| `test_no_email_for_historic` | La reproducción no envía notificaciones reales |
| `test_reference_time_is_last_reading` | "Ahora" en la interfaz es el último dato real |
| `test_reliability_counts_match_outcomes` | Las cifras de Confiabilidad coinciden con `alert_outcomes` |
| E2E | Hoy, Avisos (histórico), Revisar un turno, Confiabilidad y Laboratorio muestran gráficos con datos reales y sin errores de consola |

Todo se integra a `scripts/verify.py` con `--plan 24` y una etapa nueva `--dev-audit` que corre sobre la base de desarrollo en solo lectura.

---

## Riesgos que hay que decir en la tesis

- Las alertas históricas son lo que **habría** avisado el sistema; no hubo personas reaccionando. Por eso no se reporta tiempo de respuesta humano con ellas.
- Si el metano sigue sin episodios, la reproducción mostrará cero avisos anticipados de metano. Eso es un resultado, no un error.
- El primer bloque depende de los fundacionales en zero-shot. Si no están instalados, ese periodo solo tiene avisos confirmados.

---

## Prompt para Cursor

```text
Ejecuta planes/24_OPERACION_CON_DATOS_REALES.md fase por fase en bucle
(paso → python scripts/verify.py --plan 24 → corregir → bitácora).
Contexto: CONTEXTO_SISTEMA.md, 14, 17, 23 y este plan.
Reglas:
- Prohibido crear, sembrar o mostrar datos demo, de ejemplo o inventados en la base de desarrollo o en la app.
- Todo aviso nace del flujo de producción sobre lecturas reales, con linaje completo.
- Ningún pronóstico puede venir de un modelo que vio ese instante (train_end + embargo < issued_at).
- El bloque de prueba final queda reservado hasta su corrida única.
- Si falta un insumo real (modelo instalado, umbral firmado, mapeo de equipos), el sistema lo dice
  y se detiene; no inventa un respaldo.
- Vistas operativas en lenguaje natural; recursos locales; verificador de lenguaje en verde.
Al cerrar: ejecuta python scripts/build_real_platform.py --confirm y adjunta
reports/real_platform/build_report.md en la bitácora.
```

---

## Definición de terminado del Plan 24
- [ ] `audit_demo_data.py` limpio y guardias de demo en verde.
- [ ] Equipos reales (`instruments`) y sin zonas inventadas.
- [ ] `build_real_platform.py` reconstruye todo desde los archivos reales, idempotente, con informe de cierre.
- [ ] Reproducción histórica sin fuga: avisos y resultados para todo el histórico real; bloque final reservado.
- [ ] Interfaz con fecha de referencia real, avisos por origen y Confiabilidad con su fuente.
- [ ] Linaje visible por aviso y evidencia exportada para la tesis.
- [ ] `python scripts/verify.py --plan 24` y `--dev-audit` en verde.
