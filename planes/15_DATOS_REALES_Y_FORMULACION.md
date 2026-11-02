# 15 — Datos reales, formulación formal del problema y ETL v2

**Objetivos de tesis:** OE1 (caracterizar los datos) y OE2 (ETL reproducible).
**Prerrequisitos:** planes 01–03 completados. DB migrada y con el consolidado real cargado.
**Entrega:** diagnóstico de datos reales, compuerta G0, purga de sintéticos, ETL v2 por etapas con calidad y linaje, formulación matemática y protocolo de validación temporal.

---

## F0 — Diagnóstico de los datos reales (bloquea todo lo demás)

### Pasos

1. Crear `scripts/diagnose_real_data.py`. Debe ser idempotente, de solo lectura y leer `gas_readings` con `is_synthetic=false`. Calcula:
   - por sensor y gas: número de lecturas, primera y última fecha, **intervalo entre lecturas** (p10, p50, p90 en minutos), porcentaje de huecos mayores a 3× la mediana;
   - lecturas por mes y por gas (tabla de densidad);
   - **tipo probable de sensor**: portátil o fijo (heurística: sesiones cortas con `tiempo_inicio`/`tiempo_fin` agrupados = portátil);
   - duplicados exactos y casi duplicados, que vienen de las copias `(1)` y `(2)` de los Excel;
   - unidades presentes por gas;
   - **episodios de superación** de cada nivel normativo (F4), contados como *eventos de inicio* (ver F3), por gas y por nivel.
2. Salidas:
   - `reports/diagnostico/diagnostico_datos.md` (legible, en español, con tablas);
   - `reports/diagnostico/diagnostico_datos.json` (lo consumen las pruebas y la pantalla de calidad).
3. Revisar el informe con el director antes de seguir.

### Compuerta G0 — qué horizonte puede prometer el sistema

Con la **mediana del intervalo entre lecturas** (Δt) de los gases prioritarios (CH₄, CO, H₂S):

| Resultado | Decisión |
|-----------|----------|
| Δt ≤ 2 min | Horizontes **5 y 10 min**, tal como dice el anteproyecto. Se continúa. |
| 2 < Δt ≤ 10 min | Horizontes = 1, 2 y 3 pasos de Δt (redondeado). Se documenta. Se **solicita** al proveedor el export de *datalog* por intervalo. |
| Δt > 10 min (resúmenes por periodo) | Con estos datos **no** se puede sostener una alerta a 5–10 min. Acción obligatoria: solicitar el export crudo de *datalog* del instrumento (iNet). Mientras llega, el sistema opera y se evalúa en el horizonte que el dato permite, y la tesis lo declara como limitación. |

Además, por gas y nivel:

| Episodios de inicio en datos reales | Decisión |
|-------------------------------------|----------|
| ≥ 30 | Evaluación por evento con intervalos de confianza por *bootstrap*. |
| 10–29 | Evaluación por evento con IC amplios y advertencia explícita. |
| < 10 | No se reportan métricas por evento para ese nivel. Se evalúa en el nivel inferior (“Vigilar”) más las métricas de pronóstico. |

Los horizontes elegidos se guardan en `app_settings.forecast_horizons_min` (Plan 16). **Ningún horizonte va fijo en el código.**

### Definición de terminado F0
- [x] El informe existe (`reports/diagnostico/diagnostico_datos.md|.json`).
- [x] La decisión G0 está escrita en `planes/BITACORA_BUCLE.md` (banda medium, horizontes 6/12/18).
- [x] `tests/unit/test_diagnose.py` valida intervalos y duplicados sobre un set de juguete.
- [ ] Visto del director (paso 3).

---

## F1 — Solo datos reales

1. `scripts/purge_synthetic.py --confirm`: borra las filas `gas_readings` con `is_synthetic=true` y lo registra en `audit_log` (`data.purge_synthetic`). Sin `--confirm` hace un ensayo (*dry-run*) y muestra los conteos.
2. Retirar:
   - la opción `--augmented-24m` de `scripts/load_processed_dataset.py`;
   - `ml_core/augmentation.py` y `augmentation_manifest.json` (mover a `legacy/` fuera del paquete, o eliminar).
3. **Guardia en el cargador de entrenamiento:** `ml_core/data/loader.py::load_training_frame()` filtra `is_synthetic=false` y **lanza `SyntheticDataError`** si recibe cualquier fila sintética.
4. **Deduplicación idempotente:**
   - huella SHA-256 del archivo fuente en `etl_runs.source_files`, de modo que un archivo ya cargado se omite;
   - restricción única en lecturas: `UNIQUE (sensor_id, tiempo_inicio)` (migración en el Plan 16). La inserción usa `ON CONFLICT DO NOTHING`.
5. Script de limpieza única de duplicados existentes antes de crear la restricción.

**Definición de terminado F1:** `SELECT count(*) FROM gas_readings WHERE is_synthetic` = 0; cargar dos veces el mismo Excel no cambia los conteos; `test_no_synthetic_in_training` en verde.

---

## F2 — ETL v2 por etapas, con calidad y linaje

Paquete nuevo `app/modules/ingestion/pipeline/` (refactor de `sensors_ingestion`). Cada etapa es una función pura con entrada y salida en DataFrame y conteos registrados:

| # | Etapa | Qué hace | Registro |
|---|-------|----------|----------|
| E1 | Extraer | Lee `dls_report` (hoja `Resumen`, cabecera fila 24) y el CSV consolidado | filas leídas |
| E2 | Validar esquema | 15 columnas canónicas, tipos, fechas parseables | filas rechazadas + motivo |
| E3 | Estandarizar | Nombres de sensor y gas canónicos; **unidad canónica por gas** | conversiones aplicadas |
| E4 | Calidad | Detecta problemas (tabla abajo) y los marca; no borra | `data_quality_issues` |
| E5 | Cargar | Inserta lecturas idempotentes | insertadas / omitidas |
| E6 | Rejilla | Re-muestrea por sensor a una rejilla regular (Δ = decisión G0) con máscara de faltantes | `reading_grid` |

**Unidades canónicas** (configurables en `gas_types`, Plan 16):

| Gas | Unidad canónica | Conversión conocida |
|-----|-----------------|---------------------|
| CH₄ | % vol | % LEL → % vol: `x · LIE/100`, con LIE = 5,0 % vol (o 4,4 % vol según IEC 60079-20-1). El valor usado queda en la configuración y se documenta. |
| CO, H₂S, NO₂ | ppm | — |
| O₂ | % vol | — |
| CO₂ | ppm | % vol × 10 000 |

**Reglas de calidad (E4):**

| Código | Regla | Severidad |
|--------|-------|-----------|
| `fuera_de_rango_fisico` | Valor < 0 o mayor que el máximo del instrumento | error (se excluye del modelo) |
| `valor_congelado` | Mismo valor exacto durante ≥ N pasos con varianza nula (sensor pegado) | advertencia |
| `salto_imposible` | \|ΔC/Δt\| mayor que el límite físico configurado por gas | advertencia |
| `duplicado` | Misma (sensor, tiempo) | info (omitido) |
| `hueco` | Intervalo mayor a 3× la mediana | info |
| `unidad_desconocida` | Unidad no mapeable | error |

**Rejilla (E6):** solo se imputan huecos de ≤ 3 pasos (último valor válido). Los huecos más largos quedan como faltantes con `is_imputed=false` y `is_missing=true`. Los modelos reciben la máscara. **Nunca se interpola hacia el futuro.**

**Linaje:** cada corrida registra los conteos por etapa en `etl_run_steps` (Plan 16). `scripts/export_etl_lineage.py` genera `docs/etl/transformaciones.md` con la descripción de cada etapa y los conteos de la última corrida (evidencia de OE2).

**Definición de terminado F2:** pruebas unitarias por etapa; prueba de idempotencia (dos corridas, mismo resultado); conversión de % LEL verificada; la rejilla no inventa valores en huecos largos.

---

## F3 — Formulación formal del problema (texto para la tesis y contrato para el código)

**Entrada.** Para cada sensor *s* y paso de rejilla *t*:

$$\mathbf{x}_t = \big[C_t,\; \tfrac{\Delta C}{\Delta t},\; \bar C_{t,w_1},\; \sigma_{t,w_1},\; T_t,\; m_t,\; \text{hora}_t,\; \text{turno}_t,\; \mathbf{c}_t\big]$$

donde $C_t$ es la concentración canónica, $m_t$ la máscara de faltantes, $\bar C,\sigma$ estadísticos **causales** sobre $w_1$ pasos y $\mathbf{c}_t$ las covariables disponibles (concentraciones de otros gases del mismo sitio y, si existen, presión barométrica o estado de la ventilación).

**Ventana y horizonte.** Ventana de observación $X_{t-w+1:t}$, con $w$ ∈ {30, 60, 120} pasos (ablación), y horizontes $k \in \mathcal{K}$ (decisión G0).

**Modelo (pronóstico probabilístico).**

$$\hat q_\tau(t+k) = f_\theta\big(X_{t-w+1:t}\big), \quad \tau \in \{0.1,\,0.5,\,0.9,\,0.95\}$$

entrenado con **pérdida cuantílica** (pinball):

$$\mathcal{L}_\tau(y,\hat q)=\max\big(\tau(y-\hat q),\,(\tau-1)(y-\hat q)\big)$$

Es asimétrica por construcción: para τ alto, subestimar una concentración cuesta más que sobreestimarla. Esto responde a la observación 2C.

**Decisión (alerta).** Para el gas *g* y el nivel normativo ℓ con umbral $\theta_{g,\ell}$:

$$\hat p_{\ell}(t+k)=P\big(C_{t+k}\ge\theta_{g,\ell}\mid X\big)\;\;(\text{de los cuantiles calibrados})$$

$$\text{aviso}_{\ell}(t)=\mathbb{1}\big[\max_{k\in\mathcal{K}}\hat p_\ell(t+k)\ge\pi_\ell\big]$$

con $\pi_\ell$ ajustado en validación, más **persistencia** (dos pasos seguidos para emitir) e **histéresis** (para cerrar debe bajar de $0.8\,\pi_\ell$).

**Verdad de referencia (evento de inicio).**

$$e_\ell(t)=\mathbb{1}\Big[\max_{s\in(t,\,t+k_{\max}]}C_s\ge\theta_{g,\ell}\;\wedge\;C_t<\theta_{g,\ell}\Big]$$

Solo cuentan los **inicios**: los episodios ya en curso se excluyen. Así se evita premiar al sistema por “ver” lo que el sensor ya marca.

**Anticipación.** Para cada episodio con cruce en $t_e$: $\text{anticipación}=t_e-t_{\text{primer aviso}}$, si el aviso estuvo activo de forma continua hasta $t_e$. Si no hubo aviso, el episodio cuenta como **no detectado**.

**Falsa alarma.** Un episodio de aviso sin cruce dentro de $k_{\max}$ + tolerancia. Se reporta **por turno de 8 h**.

Contrato en código: `ml_core/forecasting/problem.py` define `ProblemSpec(lookback, horizons, quantiles, levels)`. Todos los módulos lo reciben; nadie usa constantes sueltas.

---

## F4 — Umbrales normativos como datos

1. Tabla `normative_thresholds` (Plan 16) y semilla en `scripts/seed_thresholds.py`.
2. Valores iniciales **a verificar con el artículo exacto** antes de usar en la tesis. La semilla los marca con `verified=false` y la UI del supervisor lo muestra:

| Gas | Nivel “Vigilar” | Nivel “Actuar” | Nivel “Evacuar” | Fuente a confirmar |
|-----|-----------------|----------------|-----------------|--------------------|
| CH₄ (% vol) | 0,5 | 1,0 | 1,5 | Decreto 1886 de 2015 (artículos sobre metano en labores y frentes) |
| CO (ppm) | 25 | 50 | 100 | Decreto 1886 / valores límite de exposición (TLV) adoptados |
| H₂S (ppm) | 1 | 5 | 10 | Ídem |
| O₂ (% vol) | < 19,5 | < 19,0 | < 17,0 | Ídem (dirección inversa: **por debajo**) |

3. El campo `direction` (`above` / `below`) cubre el oxígeno.
4. Cambiar un umbral exige el permiso `thresholds.manage`, queda en auditoría y **no** reescribe avisos pasados (los umbrales tienen `valid_from`).

**Definición de terminado F4:** semilla idempotente; la evaluación lee los umbrales desde la DB; existe una prueba para la dirección `below`.

---

## F5 — Protocolo de validación temporal (contrato para el Plan 17)

1. **Walk-forward con ventana expansiva por bloques** sobre los periodos reales con datos. El último bloque real (por ejemplo, dic-2025) es la **prueba final intocable**: solo se usa una vez, al cerrar la tesis.
2. **Purga:** se eliminan las muestras de entrenamiento cuya ventana o cuyo objetivo se solape con el bloque de validación. Brecha mínima = $w + k_{\max}$ pasos.
3. **Embargo:** se descartan además $k_{\max}$ pasos después de cada bloque de validación antes de usarlo como entrenamiento en el siguiente pliegue.
4. **Calibración:** el último 20 % temporal del entrenamiento de cada pliegue se reserva para la calibración conformal y el ajuste de $\pi_\ell$.
5. **Requisitos mínimos por pliegue:** al menos 500 pasos válidos de validación por gas prioritario. Si un periodo no alcanza, se fusiona con el contiguo, y eso queda registrado.
6. Implementación: `ml_core/validation/walk_forward.py` → genera los pliegues como objetos `Fold(train_idx, calib_idx, val_idx)` y los persiste en `model_evaluations.fold_spec`.
7. Queda **prohibido** usar `KFold`, `StratifiedKFold` o `train_test_split` con `shuffle=True` en `ml_core/`. Lo verifica una prueba que analiza el código fuente.

**Definición de terminado F5:** `test_walk_forward_no_overlap` (ningún índice de validación aparece en entrenamiento o calibración, y la brecha ≥ $w+k_{\max}$); `test_no_shuffle_splitters`.

---

## F6 — Evidencia de OE1 dentro de la plataforma

1. `scripts/build_eda_report.py` genera `reports/eda/` con figuras ECharts exportadas o PNG: series por gas, distribución, ciclo diario, correlación entre gases y episodios. Se reutiliza en la tesis.
2. Pantalla “**Calidad de los datos**” (solo analista y admin, Plan 18): cobertura por sensor, huecos, problemas detectados y la decisión G0 vigente.
3. Los notebooks quedan como históricos. Toda lógica que se necesite pasa a `ml_core/` o `app/`.

---

## Definición de terminado del Plan 15
- [x] G0 decidido y documentado (horizontes 6/12/18; visto del director pendiente).
- [x] Cero filas sintéticas; carga idempotente.
- [x] ETL v2 con 6 etapas, conteos y linaje exportable.
- [x] Formulación implementada en `ProblemSpec` y escrita para la tesis.
- [x] Umbrales en DB con dirección y vigencia.
- [x] Walk-forward con purga y embargo, con pruebas.
- [x] `python scripts/verify.py --plan 15` en verde.
