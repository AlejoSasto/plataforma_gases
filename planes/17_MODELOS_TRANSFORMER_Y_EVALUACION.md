# 17 — Modelos transformer, decisión, explicabilidad y evaluación

**Objetivo de tesis:** OE3.
**Prerrequisitos:** Plan 15 (G0, rejilla, `ProblemSpec`, walk-forward) y Plan 16 (M4–M6).
**Entrega:** un zoo de pronóstico probabilístico con referencias honestas, tres transformers supervisados, tres modelos fundacionales, calibración conformal, capa de decisión normativa, explicaciones en lenguaje natural, una evaluación reproducible para la tesis y la regla de selección del modelo en producción.

---

## 1. Principios

1. **Todo modelo compite contra la persistencia.** Si no la supera (MASE ≥ 1), no aporta valor y no se promueve.
2. **Una sola interfaz** para todos los modelos; la evaluación es idéntica para todos.
3. **Probabilístico siempre:** cada modelo entrega cuantiles. Si un modelo es puntual, se le agregan intervalos conformales.
4. **Escasez de datos reales → transferencia.** Los modelos fundacionales preentrenados (zero-shot o con ajuste fino) son la respuesta científica a tener pocos datos. No se clona información.
5. **Ligero para el borde.** El modelo en producción debe pronosticar todos los sensores en menos de 1 s por ciclo en una CPU de 4 núcleos.

---

## 2. Arquitectura de código

```
ml_core/
├── forecasting/
│   ├── problem.py          # ProblemSpec (Plan 15 F3)
│   ├── dataset.py          # rejilla → formato largo (unique_id, ds, y, covariables, máscara)
│   ├── base.py             # interfaz Forecaster
│   ├── adapters/
│   │   ├── baselines.py    # persistencia, estacional, ETS
│   │   ├── gbm.py          # LightGBM cuantílico
│   │   ├── neural.py       # LSTM, TFT, PatchTST, iTransformer (neuralforecast)
│   │   ├── chronos.py      # Chronos-2 / Chronos-Bolt
│   │   ├── timesfm.py      # TimesFM
│   │   └── ttm.py          # Tiny Time Mixers (IBM Granite)
│   ├── conformal.py        # calibración de cuantiles por horizonte
│   ├── decision.py         # probabilidad de superar el umbral → nivel → aviso
│   └── explain/
│       ├── attributions.py # VSN de TFT, gradientes integrados, SHAP
│       └── narrator.py     # factores → frase natural (plantillas, sin LLM)
├── validation/
│   ├── walk_forward.py     # Plan 15 F5
│   └── metrics.py          # pronóstico + eventos + operación
└── experiments/
    ├── run_benchmark.py    # corre el zoo completo sobre todos los pliegues
    └── thesis_report.py    # tablas y figuras para la tesis y el artículo
```

**Interfaz única:**

```python
class Forecaster(Protocol):
    name: str
    family: Literal["baseline", "tabular", "recurrente", "transformer", "fundacional"]
    def fit(self, train: pd.DataFrame, spec: ProblemSpec) -> None: ...
    def predict_quantiles(self, context: pd.DataFrame, spec: ProblemSpec) -> pd.DataFrame:
        """Devuelve: unique_id, issued_at, horizon_min, q10, q50, q90, q95."""
    def save(self, path: Path) -> None: ...
    @classmethod
    def load(cls, path: Path) -> "Forecaster": ...
```

Cada adaptador fija sus versiones en `requirements-ml.txt`. Al instalar se **verifica la API vigente** de cada librería y se ajusta el adaptador; nunca se asume.

---

## 3. Zoo de modelos

| Clave | Familia | Modelo | Rol en la tesis | Librería |
|-------|---------|--------|-----------------|----------|
| `persistencia` | baseline | $\hat y_{t+k}=y_t$ | **Referencia obligatoria**; denominador de MASE | propio |
| `ets` | baseline | Suavizamiento exponencial automático | Referencia estadística clásica | statsforecast |
| `lgbm_q` | tabular | LightGBM cuantílico con rezagos, derivadas y ventanas causales | Referencia fuerte no-transformer; SHAP nativo | mlforecast + lightgbm |
| `lstm` | recurrente | LSTM con salida cuantílica | Comprometido en el anteproyecto | neuralforecast |
| `tft` | transformer | **Temporal Fusion Transformer** | **Candidato principal supervisado.** Cuantiles nativos, covariables y explicabilidad propia (selección de variables + atención) | neuralforecast |
| `patchtst` | transformer | PatchTST (atención sobre parches) | Transformer de referencia para series largas | neuralforecast |
| `itransformer` | transformer | iTransformer (atención entre variables) | Aprovecha la relación entre gases del mismo sitio | neuralforecast |
| `chronos2` | fundacional | Chronos-2 / Chronos-Bolt | Zero-shot y ajuste fino; admite covariables; responde a la escasez de datos | chronos-forecasting |
| `timesfm` | fundacional | TimesFM | Segundo fundacional (zero-shot) para robustez del hallazgo | timesfm |
| `ttm` | fundacional | Tiny Time Mixers (~1 M parámetros) | **Candidato para el borde**: ajuste fino rápido en CPU | granite-tsfm |

> **Por qué no BERT:** BERT es un modelo de lenguaje sobre texto. Los fundacionales de esta tabla aplican la misma idea (preentrenamiento masivo + transferencia) a series numéricas. Esa es la justificación para la tesis.

**Configuración común de los modelos neuronales:**
- Pérdida cuantílica multi-cuantil (τ = 0,1 / 0,5 / 0,9 / 0,95).
- Escalado por serie ajustado **solo con el entrenamiento**.
- Modelo **global** (todas las series de un gas) con identificador de sensor como covariable estática.
- *Early stopping* sobre la calibración del pliegue (nunca sobre validación).
- Semillas fijas; 3 semillas por configuración, con media y desviación reportadas.

**Búsqueda de hiperparámetros:** Optuna, 30 ensayos por modelo, **dentro** del entrenamiento de cada pliegue (validación interna temporal). Espacio declarado en `ml_core/experiments/search_spaces.yaml`.

**Ablaciones para la tesis:**

| Ablación | Variantes |
|----------|-----------|
| Ventana | w = 30, 60, 120 pasos |
| Covariables | Solo el gas objetivo / con otros gases / con temperatura y presión |
| Fundacional | Zero-shot / ajuste fino |
| Alcance | Modelo global por gas / modelo por sensor |
| Pérdida | Pinball / pinball + peso asimétrico ($1+\alpha\,\mathbb{1}[y>\hat q]$) |

---

## 4. Calibración conformal (gestión de la incertidumbre)

1. Sobre el bloque de calibración de cada pliegue: residuos por horizonte $r = y - \hat q_\tau$.
2. **Cuantil conformal dividido:** se ajusta cada cuantil con el cuantil empírico de los residuos, para lograr la cobertura nominal (por ejemplo, 90 % para el intervalo [q10, q90]).
3. **En producción:** calibración adaptativa en línea (ACI). Ajusta el nivel según la cobertura reciente y corrige la deriva de los sensores.
4. Implementación propia en `conformal.py` (sin depender de la API de terceros), con prueba de cobertura sobre datos simulados.
5. La **confianza** que ve la UI (`alta`/`media`/`baja`) sale del ancho relativo del intervalo calibrado frente al umbral más cercano.

---

## 5. Capa de decisión

1. A partir de los cuantiles calibrados, se interpola la distribución predictiva para obtener $\hat p_\ell(t+k)=P(C_{t+k}\ge\theta_{g,\ell})$ (o `≤` si la dirección es `below`).
2. **Umbral de decisión $\pi_\ell$** por nivel, ajustado en la calibración con este criterio:
   - **maximizar el recall por evento sujeto a falsas alarmas por turno ≤ límite** (configurable; inicial: 1 por turno en “Actuar”, 0,25 en “Evacuar”).
   - Si no hay $\pi_\ell$ que cumpla las dos condiciones, se prioriza el recall y se registra la tasa resultante.
3. **Persistencia** (`alert_persistence_steps`, inicial 2) e **histéresis** (cierra al bajar de $0.8\,\pi_\ell$) para evitar el parpadeo de avisos.
4. **Avisos confirmados:** si la lectura actual ya supera el umbral, se emite un aviso `confirmado` sin pasar por el modelo. La regla dura nunca depende del modelo.
5. El estado operativo del sensor es el **máximo** entre el nivel confirmado y el anticipado.

---

## 6. Explicabilidad traducida a lenguaje natural

| Modelo | Método | Salida |
|--------|--------|--------|
| TFT | Selección de variables + atención temporal nativa | Peso por factor y por tramo de tiempo |
| LSTM, PatchTST, iTransformer, TTM | Gradientes integrados (Captum) sobre la ventana | Peso por factor y por tramo |
| LightGBM | TreeSHAP | Peso por rasgo |
| Fundacionales zero-shot | Sensibilidad por oclusión de tramos de la ventana | Tramo de tiempo más influyente |

**Catálogo de factores** (`explain/factors.py`): los rasgos técnicos se agrupan en factores comprensibles:

| Código | Agrupa | Frase base |
|--------|--------|------------|
| `tendencia_subida` | ΔC/Δt, pendiente reciente | “El {gas} viene subiendo de forma sostenida en los últimos {n} minutos” |
| `nivel_alto` | C_t frente al umbral | “El nivel actual ya está cerca del límite de {nivel}” |
| `subida_brusca` | Variación local alta | “Hubo un aumento repentino hace {n} minutos” |
| `otro_gas` | Covariables de otros gases | “El {otro_gas} en la misma zona también está subiendo” |
| `temperatura` | T_t | “La temperatura en la zona aumentó” |
| `hora_turno` | Hora / turno | “A esta hora suelen registrarse aumentos en esta zona” |

`narrator.py` toma los 2–3 factores de mayor peso y arma, con **plantillas fijas**, el texto de `forecast_explanations.plain_text` (sin LLM, determinista y verificable). Hay pruebas que verifican que cada factor tiene plantilla y que el texto no contiene términos prohibidos (Plan 20).

---

## 7. Métricas (todas por gas, horizonte, nivel y pliegue)

**Pronóstico**

| Métrica | Uso |
|---------|-----|
| MAE y RMSE en unidad canónica | Error absoluto (CH₄ en % vol) |
| **MASE** frente a persistencia | < 1 = aporta sobre “no hacer nada” |
| Pinball promedio | Calidad de los cuantiles |
| Cobertura del intervalo [q10, q90] y ancho medio | Calibración (meta: 90 % ± 5 pp) |

**Eventos (verdad = `threshold_events`, inicios)**

| Métrica | Definición |
|---------|------------|
| Recall por evento | Episodios avisados a tiempo / episodios |
| Precisión por evento | Avisos acertados / avisos emitidos |
| F1 por evento | — |
| Tasa de no detectados | 1 − recall |
| **Anticipación** p10 y p50 (min) | Medida por episodio (Plan 15 F3) |
| **Falsas alarmas por turno** | Por turno de 8 h observado |
| IC 95 % | Bootstrap por bloques de episodios |

**Operación:** latencia por ciclo, memoria y tamaño del artefacto.

### Correspondencia con los criterios del anteproyecto

| Criterio del anteproyecto | Reformulación medible | Nota |
|---------------------------|-----------------------|------|
| Recall clase riesgo ≥ 95 % | Recall **por evento** en nivel “Actuar” ≥ 0,95 | Con IC; si hay < 10 episodios, ver G0 |
| FN ≤ 5 % | Tasa de no detectados ≤ 0,05 | Equivale al anterior |
| Precisión ≥ 90 % | Precisión por evento ≥ 0,90 **y** falsas alarmas por turno ≤ límite | La segunda es la que entiende la operación |
| F1 ≥ 0,92 | F1 por evento ≥ 0,92 | |
| RMSE ≤ 0,05 fracción molar | **RMSE ≤ 0,05 % vol para CH₄** a k = 5 min | Solo CH₄; los demás gases se evalúan con MASE |
| Anticipación ≥ 5 min | Anticipación **p50** ≥ 5 min (y p10 reportado) | Solo si G0 lo permite |

Las metas viven en `app_settings` (`thesis_targets`). El laboratorio las muestra en verde o rojo **sin maquillar**.

---

## 8. Regla de selección del modelo en producción

Orden lexicográfico sobre la media de los pliegues (nunca sobre la prueba final):

1. **Elegibilidad:** MASE < 1 en CH₄ a todos los horizontes **y** cobertura dentro de 90 % ± 5 pp.
2. Mayor recall por evento en “Actuar”, con falsas alarmas por turno ≤ límite.
3. Mayor anticipación p50.
4. Menos falsas alarmas por turno.
5. Desempate: menor latencia (preferencia por el borde).

`select_production_model()` calcula el `selection_score`, propone el ganador y **requiere promoción explícita** con `models.promote` (queda en auditoría). Se elimina la preferencia fija por modelos de secuencia.

---

## 9. Inferencia en producción

1. Job (APScheduler) cada `grid_step_minutes`: por cada sensor activo, toma la ventana de `reading_grid`, pronostica los cuantiles, calibra (ACI), decide el nivel, explica y persiste `forecasts`, `forecast_quantiles` y `forecast_explanations` de forma idempotente (UQ).
2. Si hay cambio de nivel → crea o actualiza `alerts` con su mensaje y recomendación natural → notifica a los interesados.
3. Job de cierre: pasado $k_{\max}$ + tolerancia, completa `alert_outcomes` (acertado / falsa alarma) con `threshold_events`.
4. Sin modelo en producción → solo operan los avisos confirmados, y la UI lo dice en lenguaje natural (“El sistema está mostrando solo lo que marcan los sensores en este momento”).
5. Artefactos: MLflow (`plataforma-gases-forecasting`). Copia local del modelo en producción en `storage/models/production/` para operar sin red.

---

## 10. Reproducibilidad y salidas para la tesis

1. `python -m ml_core.experiments.run_benchmark --config experiments/benchmark.yaml` corre todo el zoo sobre todos los pliegues y escribe `model_evaluations`.
2. `python -m ml_core.experiments.thesis_report` genera en `reports/thesis/`:
   - tablas en Markdown y LaTeX (por gas, horizonte y nivel, con IC);
   - figuras: pronóstico con bandas sobre episodios reales, curva recall vs. falsas alarmas por turno, distribución de la anticipación, importancia de factores, cobertura por horizonte;
   - `ablaciones.md`.
3. La **prueba final** se corre una sola vez con `--final-test`. Queda marcada `is_final_test=true` y no se repite sin justificación escrita en la bitácora.

---

## 11. Dependencias y contenedor

- `requirements-ml.txt` separado (neuralforecast, statsforecast, mlforecast, lightgbm, optuna, captum, shap, chronos-forecasting, timesfm, granite-tsfm), con versiones fijadas.
- Imagen `app` con torch CPU. Los pesos de los fundacionales se descargan **en la construcción** (`scripts/fetch_foundation_weights.py`) para operar sin red en el borde.
- Pruebas pesadas marcadas `@pytest.mark.slow` (corren en `verify --full`).

---

## Definición de terminado del Plan 17
- [x] Los 10 adaptadores cumplen la interfaz (prueba de contrato parametrizada).
- [x] El benchmark reducido corre y escribe `reports/thesis/`; el llenado masivo de `model_evaluations` sobre los 10 fundacionales queda para una corrida `--full`/GPU.
- [x] Cobertura conformal verificada sobre datos simulados (90 % ± 2 pp).
- [x] Decisión con persistencia e histéresis probada; avisos confirmados independientes del modelo.
- [x] Cada aviso trae una explicación en lenguaje natural que pasa el verificador de lenguaje.
- [x] Regla de selección implementada; sin preferencias fijas por familia.
- [x] Latencia del modelo en producción < 1 s por ciclo para todos los sensores (prueba de rendimiento).
- [x] `reports/thesis/` generado y reproducible.
- [x] `python scripts/verify.py --plan 17` en verde.
