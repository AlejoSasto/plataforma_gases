# 31 — Diseño de la solución de inteligencia artificial

**Ejecutor:** Claude.  
**Contrato:** [`27_PAQUETE_DISENO_INDICE.md`](27_PAQUETE_DISENO_INDICE.md).  
**Salidas:**

- `docs/diseno/word/02_diseno_solucion_ia.docx`
- `docs/diseno/drawio/14_pipeline_ia.drawio`
- `docs/diseno/drawio/15_walk_forward.drawio`
- `docs/diseno/drawio/16_ciclo_vida_modelo.drawio`

**Bitácora:** `docs/diseno/bitacora/31.md`.

Este documento es el diseño. Las cifras medidas van al Plan 32. Aquí se describe lo que el sistema está construido para hacer, y se marca como meta lo que el Plan 17 fijó y la corrida publicada todavía no evidencia.

## Fuentes obligatorias

- [`17_MODELOS_TRANSFORMER_Y_EVALUACION.md`](../../planes/17_MODELOS_TRANSFORMER_Y_EVALUACION.md) completo.
- [`15_DATOS_REALES_Y_FORMULACION.md`](../../planes/15_DATOS_REALES_Y_FORMULACION.md) en lo que toca a G0, `ProblemSpec` y walk-forward.
- [`docs/g0_visto_director.md`](../../docs/g0_visto_director.md).
- Código: `ml_core/forecasting/` (`base`, `problem`, `dataset`, `conformal`, `decision`, `explain`), `ml_core/validation/`, `ml_core/experiments/`. Si un archivo del plan ya no existe, se describe el que cumple esa función y se anota el nombre real.
- [`CONTEXTO_SISTEMA.md`](../../planes/CONTEXTO_SISTEMA.md) §8.3, solo para no resucitar el zoo tabular de `legacy/` como diseño vigente.

## Trazado del Word

1. Portada. Título: Diseño de la solución de pronóstico probabilístico. Sistema Vigía.
2. Control de versiones.
3. Pregunta de diseño. Qué se predice, a qué horizonte, con qué decisión y qué queda fuera.
4. Formulación matemática.
5. Datos que entran al modelo y los que no.
6. Protocolo de validación.
7. Zoo y contrato único.
8. Calibración e incertidumbre.
9. Capa de decisión y regla dura.
10. Explicabilidad.
11. Métricas, metas y regla de promoción.
12. Ciclo de vida.
13. Papel del asistente, en un apartado corto que lo deja fuera del lazo de decisión.
14. Limitaciones de diseño frente a la evidencia disponible.
15. Referencias internas a los planes 15 y 17 y al Decreto 1886 de 2015.

Tono: impersonal, preciso, con la notación definida antes de usarla. No se usa «inteligencia artificial» como explicación de un resultado.

## Formulación que debe quedar escrita así

Sea \(C_{t}\) la concentración en unidad canónica del gas \(g\) en un sensor, en el instante \(t\). El modelo estima los cuantiles

\[
\hat q_{\tau}(t+k), \quad \tau \in \{0{,}10;\ 0{,}50;\ 0{,}90;\ 0{,}95\}, \quad k \in \{6,\ 12,\ 18\} \text{ minutos.}
\]

Esos horizontes son 1, 2 y 3 pasos de la rejilla que sostiene la compuerta G0 (Δt mediano máximo entre CH₄, CO y H₂S de 5,77 minutos, banda media). No se formulan 5 ni 10 minutos: el visto G0 los retiró para este consolidado.

La decisión no es una clase aprendida. Para cada nivel normativo \(\ell\) con umbral \(\theta_{g,\ell}\) y dirección `above` o `below`, se obtiene

\[
\hat p_{\ell}(t+k) = P(C_{t+k} \ge \theta_{g,\ell})
\]

o la desigualdad opuesta si la dirección es `below` (oxígeno). El nivel operativo es el máximo entre el nivel que ya confirma la lectura actual y el nivel anticipado que supera el umbral de decisión \(\pi_{\ell}\).

Estados visibles: Normal, Vigilar, Actuar ya, Evacuar, Sin datos.

## Datos

Incluir, con el nombre de la tabla:

- Entran: `reading_grid` (valor, imputado, faltante), umbrales vigentes de `normative_thresholds`, identificador de sensor como covariable estática cuando el modelo es global por gas.
- No entran como etiqueta: la alarma del instrumento, el STEL del archivo ni el percentil 95 de toda la historia del sensor. Eso perteneció a un diseño retirado (`evento_final`) y se menciona solo en la sección de limitaciones, como antecedente que ya no rige.
- No entran filas sintéticas.
- La temperatura puede entrar como covariable causal si el adaptador la declara. No se usa una estadística calculada con el futuro ni con el bloque de prueba.

Diagrama `14_pipeline_ia.drawio`, de izquierda a derecha:

Archivo de campo → E1–E6 → `gas_readings` → `reading_grid` → `ProblemSpec` → adaptador `Forecaster` → cuantiles → calibración conformal → decisión → `forecasts` / `forecast_quantiles` / explicación por plantilla → aviso.

Una flecha aparte, que no pasa por el adaptador: lectura actual comparada con el umbral → aviso confirmado.

El asistente no está en este flujo.

## Validación

Diagrama `15_walk_forward.drawio`. Una línea de tiempo por pliegue, con cuatro bloques en este orden: entrenamiento, purga, calibración, validación. El último bloque real de la serie queda fuera de todos los pliegues de selección y solo se usa en la prueba final (`is_final_test`).

Texto que debe acompañar el dibujo:

- La partición es temporal. No es aleatoria ni estratificada.
- Toda estadística de escala se ajusta dentro del entrenamiento del pliegue.
- El embargo impide que una ventana que toca el corte se use como si fuera pasado.
- Si un gas no tiene episodios suficientes para una métrica de evento, la política de evaluación del diagnóstico manda (`no_event_metrics`, `bootstrap_ic`, `wide_ic_warning`). No se imputa un recall.

## Zoo

Tabla en el Word, tomada del Plan 17 y comprobada contra `ml_core/forecasting/adapters/`. Si un adaptador no está en código, la fila dice «previsto en el Plan 17, no presente en el código a la fecha de corte».

| Clave | Familia | Papel en el diseño |
|-------|---------|--------------------|
| persistencia | baseline | Piso obligatorio. Denominador del MASE. |
| ets | baseline | Referencia estadística clásica. |
| lgbm_q | tabular | Referencia fuerte no transformer, con rasgos causales. |
| lstm | recurrente | Compromiso del anteproyecto, salida cuantílica. |
| tft | transformer | Candidato supervisado principal: cuantiles, covariables y selección de variables. |
| patchtst | transformer | Referencia de atención sobre parches. |
| itransformer | transformer | Atención entre variables del mismo sitio. |
| chronos2 | fundacional | Transferencia ante escasez de datos. |
| timesfm | fundacional | Segunda comprobación fundacional. |
| ttm | fundacional | Candidato ligero para el borde. |

Párrafo obligatorio: estos fundacionales aplican preentrenamiento y transferencia a series numéricas. No son un modelo de lenguaje y no sustituyen a la capa de decisión.

Contrato, en prosa y en un recuadro: todo adaptador ajusta con el bloque de entrenamiento y devuelve `unique_id`, `issued_at`, `horizon_min`, q10, q50, q90 y q95. Si la librería no está instalada, el adaptador se registra como no disponible. No se simula su métrica.

## Calibración, decisión y explicación

Calibración: residuos por horizonte en el bloque de calibración; cuantil conformal para acercar la cobertura del intervalo q10–q90 al 90 %. La confianza alta, media o baja que ve la operación sale del ancho relativo de ese intervalo frente al umbral cercano, no de una probabilidad inventada.

Decisión: \(\pi_{\ell}\) se ajusta en calibración para subir el recall por evento sin pasar el límite de falsas alarmas por turno (diseño inicial: 1 por turno en Actuar ya y 0,25 en Evacuar). Si ningún umbral cumple las dos cosas, se prioriza el recall y se guarda la tasa resultante. Persistencia de dos pasos e histéresis para no parpadear. Cerrar estas constantes contra `app_settings` y, si el código usa otras, escribir las del código.

Explicación: los factores técnicos se agrupan (tendencia de subida, nivel ya alto, subida brusca, otro gas, temperatura, hora del turno). Una plantilla arma dos o tres frases. No interviene un modelo de lenguaje. Métodos según familia: selección de variables del TFT, gradientes integrados, TreeSHAP, oclusión en fundacionales zero-shot. Si el código solo implementa una parte, el Word dice «diseñado» y «implementado» en columnas distintas.

## Métricas y promoción

Pronóstico: MAE, RMSE, MASE, pinball, cobertura y ancho del intervalo q10–q90, latencia.

Evento, con verdad en `threshold_events`: recall, precisión, F1, no detectados, anticipación p10 y p50, falsas alarmas por turno de 8 horas, intervalo de confianza por bloques cuando la política lo permite.

Metas del anteproyecto, reformuladas, como metas y no como resultados: recall por evento en Actuar ya de al menos 0,95; precisión por evento de al menos 0,90 junto con el límite de falsas alarmas; F1 de al menos 0,92; RMSE de CH₄ de como máximo 0,05 %vol; anticipación p50 de al menos 5 minutos solo si G0 lo permite. G0 permite hablar de horizontes de 6 minutos o más; no autoriza a dar por cumplida la anticipación de 5 minutos sin medirla.

Promoción, en orden lexicográfico sobre la media de los pliegues, nunca sobre la prueba final:

1. Elegible solo si el MASE es menor que 1 en CH₄ en todos los horizontes y la cobertura queda en 90 % ± 5 puntos.
2. Mayor recall de evento en Actuar ya, dentro del límite de falsas alarmas.
3. Mayor anticipación p50.
4. Menos falsas alarmas.
5. Menor latencia.

El ganador se propone. Una persona con `models.promote` lo pasa a producción. Queda en auditoría.

## Ciclo de vida

Diagrama `16_ciclo_vida_modelo.drawio`. Estados de `model_registry.status`: staging, production, archived. Transiciones: entrenar crea staging; promover lleva uno a production y no borra la evaluación; archivar saca de producción. No hay flecha automática de «mejor métrica» a production.

## Apartado del asistente

Un apartado de una página, no más. El asistente lee pronósticos, avisos y el manual mediante herramientas. No elige \(\pi_{\ell}\), no escribe `alerts` y no modifica `model_registry`. Si no hay red, el lazo de este capítulo sigue igual.

## Limitaciones que el capítulo debe decir

- El consolidado tiene huecos de meses y frecuencia irregular. Por eso el horizonte es el de G0 y no el del anteproyecto original.
- Varios gases tienen pocos inicios de episodio en los niveles de interés. La métrica de evento no se calcula, o se calcula con advertencia de intervalo ancho, según la tabla del diagnóstico. Claude copia esa política desde `reports/diagnostico/diagnostico_datos.md` como contexto del diseño, y deja los conteos para el Plan 32.
- La corrida en `reports/thesis/benchmark.json` no es evidencia del zoo completo ni de la prueba final.
- La firma del director en el visto G0 puede seguir pendiente. El diseño usa la decisión técnica ya registrada; no afirma una firma que el archivo no tenga.
- Los umbrales de semilla pueden tener `verified=false`.

## Definición de terminado

- El Word contiene la formulación, el zoo contrastado con el código, la regla de promoción y las limitaciones, sin cifras de MAE o MASE (esas pertenecen al Plan 32).
- Los tres `.drawio` existen y el pipeline muestra la regla dura al margen del modelo.
- La bitácora lista adaptadores previstos que no están en código, si los hay.
