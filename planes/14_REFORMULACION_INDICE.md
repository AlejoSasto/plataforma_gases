# 14 — Reformulación integral: índice, objetivos y orden de ejecución

> **Qué es este paquete:** la reformulación completa de la plataforma para responder a las observaciones del jurado y cumplir los objetivos del trabajo de grado. Usa **solo datos reales**, modelos de pronóstico basados en **transformers**, un rediseño visual completo y **lenguaje natural no técnico** en todo lo que ve la empresa.
>
> Reemplaza el enfoque de los planes 04, 05, 07, 11, 12 y 13 en lo que se contradiga. Los planes 01–03, 06 y 08 siguen vigentes como base. Ante conflicto: **este paquete > planes anteriores**, y el **código** es la verdad del estado actual.

| Plan | Archivo | Responde a |
|------|---------|------------|
| 14 | `14_REFORMULACION_INDICE.md` (este) | Mapa general, objetivos, prompt del bucle |
| 15 | `15_DATOS_REALES_Y_FORMULACION.md` | OE1, OE2 · Jurado 2A, 2B, 6 |
| 16 | `16_MODELO_DE_DATOS_V2.md` | OE2, OE3, OE4 · trazabilidad |
| 17 | `17_MODELOS_TRANSFORMER_Y_EVALUACION.md` | OE3 · Jurado 2A, 2B, 2C, 2D, 6 |
| 18 | `18_UX_UI_LENGUAJE_NATURAL.md` | OE4 · Jurado 2D (explicabilidad para el operador) |
| 19 | `19_USUARIOS_ROLES_Y_ACCESO.md` | OE4 · seguridad de la plataforma |
| 20 | `20_PRUEBAS_Y_BUCLE_DE_CALIDAD.md` | Transversal: definición de “perfecto” y bucle |

---

## 1. Decisiones no negociables

1. **Solo datos reales.** Se retira el dataset aumentado de 24 meses y el clonado de meses (`ml_core/augmentation.py`). Ningún entrenamiento, validación ni métrica usa filas `is_synthetic=true`. Una prueba automática lo garantiza (Plan 20).
2. **Sin fuga de información.** Toda variable en el instante *t* se calcula solo con datos ≤ *t*. Toda estadística (percentiles, medias, desviaciones, normalización) se ajusta solo con el bloque de entrenamiento de cada partición. Hay pruebas automáticas de no-fuga.
3. **El sistema pronostica, luego decide.** El núcleo es un **pronóstico probabilístico** de la concentración a *t+k* minutos. La alerta es una **decisión** que compara ese pronóstico con **umbrales normativos** (Decreto 1886 de 2015 y valores límite de exposición). Ya no se clasifica “si la lectura actual es alta”.
4. **Dos registros de lenguaje.**
   - **Vistas operativas** (operador, supervisor, gerencia, auditor): lenguaje natural, cero jerga de IA. Una prueba automática bloquea términos prohibidos.
   - **Laboratorio de modelos** (solo analista de datos y admin): aquí sí se permiten métricas técnicas.
5. **Honestidad de resultados.** Si los datos reales no permiten cumplir una meta del anteproyecto, el sistema lo **muestra** y la tesis lo **documenta como limitación**. Nunca se infla una métrica.
6. **Edge primero.** La plataforma corre completa y sin internet en un equipo en bocamina (Docker). La nube (Plan 09) queda como sincronización asíncrona para reentrenar y para la analítica gerencial.

---

## 2. Objetivos reformulados (texto propuesto para el documento de tesis)

Mantienen la identidad del proyecto (*sistema predictivo + ETL*), quedan alineados en todas las secciones y corrigen la terminología que señaló el jurado.

**Objetivo general.** Desarrollar un sistema predictivo de alerta temprana que, mediante procesos ETL y modelos de pronóstico probabilístico de series temporales basados en arquitecturas *transformer*, anticipe la superación de umbrales normativos de concentración de gases en una mina subterránea de carbón colombiana (caso de estudio), como herramienta de apoyo a la toma de decisiones preventivas.

| # | Objetivo específico | Evidencia en la plataforma |
|---|---------------------|----------------------------|
| OE1 | Caracterizar los datos reales de los sensores de gases de la mina caso de estudio: calidad, frecuencia de muestreo, patrones temporales, relaciones entre variables y episodios de superación de umbrales normativos. | Informe automático de diagnóstico + pantalla “Calidad de los datos” (Plan 15, F0 y F6) |
| OE2 | Diseñar e implementar un proceso ETL reproducible e idempotente que valide, estandarice y registre la trazabilidad de cada transformación de las lecturas. | ETL v2 con etapas, linaje y registro de problemas de calidad (Planes 15 y 16) |
| OE3 | Desarrollar y evaluar, con validación temporal sin fuga de información, modelos de pronóstico probabilístico basados en transformers frente a modelos de referencia, para anticipar la superación de umbrales con un tiempo de anticipación operativo. | Laboratorio de modelos + comparativa reproducible (Plan 17) |
| OE4 | Implementar una interfaz en lenguaje no técnico que presente en tiempo casi real el estado actual, el pronóstico, los avisos con su explicación y las recomendaciones, validada con usuarios de la mina. | Plataforma rediseñada + pruebas de aceptación con usuarios (Planes 18–20) |

> **Componente cualitativo:** las entrevistas pasan a ser **ingeniería de requisitos y validación de usabilidad** (diseño centrado en el usuario). Ya no es una “metodología mixta convergente-paralela”. Quedan en el cronograma como dos sesiones: co-diseño (Plan 18, F1) y pruebas de aceptación (Plan 20, F6). Esto responde a la observación 4 del jurado.

---

## 3. Mapa observación del jurado → atención

| Observación | Cómo se atiende | Plan |
|-------------|-----------------|------|
| 2A Ambigüedad clasificación vs. regresión | Formulación formal: pronóstico cuantílico $\hat q_\tau(t+k)$ más una función de decisión normativa | 15 F3 |
| 2B Validación cruzada con fuga | Walk-forward por bloques con purga y embargo; se elimina la “validación cruzada estratificada” | 15 F5, 17 |
| 2C Desbalance extremo | Pérdida cuantílica (asimétrica), cuantil alto para decidir, ajuste del umbral sobre validación; sin SMOTE ni clonado | 17 |
| 2D Explicabilidad | Importancia de variables (TFT), gradientes integrados y SHAP traducidos a frases naturales en cada aviso | 17, 18 |
| 3A Local vs. nube | Arquitectura edge-to-cloud: inferencia local y sincronización asíncrona | 14 §1.6, 09 |
| 3B Presupuesto | MVP edge + Cloud Run/BigQuery; se retiran Dataflow, Composer, Looker e Interconnect del alcance | 09 (ajustar) |
| 4 Coherencia de objetivos | Objetivos reformulados (§2), idénticos en todas las secciones | 14 |
| 6 Lead time y falsas alarmas | Anticipación medida por evento y falsas alarmas por turno, como métricas oficiales | 17 |
| 5 Forma | Duplicados, Decreto 1886 (no 1586), terminología, fuentes de 2024–2025 | Documento (fuera de código) |

---

## 4. Orden de ejecución y compuertas

```
15 F0 Diagnóstico ──► COMPUERTA G0 (horizonte posible con estos datos)
        │
15 F1–F6 Datos reales + ETL v2 ──► 16 Modelo de datos v2 (migraciones)
        │
17 Modelos (baselines → transformers → decisión → explicación)
        │
19 Usuarios y acceso ──► 18 UX/UI lenguaje natural (consume 16, 17, 19)
        │
20 Pruebas + bucle de calidad (corre al final de CADA plan, no solo al final)
```

- **No saltar compuertas.** G0 decide los horizontes que el sistema puede prometer. Todo lo de abajo depende de eso.
- **Cada plan cierra con `python scripts/verify.py` en verde** (definido en el Plan 20).
- Commits: `feat(<módulo>): <plan>.<fase>.<paso> <descripción>`, por ejemplo `feat(forecasting): 17.F3.2 adaptador TFT`.

---

## 5. Qué se retira

| Se retira | Motivo | Reemplazo |
|-----------|--------|-----------|
| `Procesamiento_de_Datos_24m.csv`, `--augmented-24m`, `ml_core/augmentation.py` | Clonado de meses: fuga y datos no reales | Solo datos reales; modelos fundacionales para la escasez de datos |
| Etiqueta `evento_final` (alarma / STEL / p95 en *t*) | Tautológica y con fuga | Evento de inicio en [t+k₁, t+k₂] con umbral normativo |
| Rasgos con estadística global (p95, media + 2σ del sensor completo) | Fuga | Ventanas causales; estadística solo del entrenamiento |
| SVM, árbol simple, GRU, Transformer vanilla, CNN1D, MLP sklearn | No temporales, redundantes o sin calibrar | Zoo del Plan 17 |
| `P ≈ |c|/(|c|+1)` | Mezcla unidades, no es probabilidad | Probabilidad de superar el umbral a partir de cuantiles calibrados |
| `lead_time_minutes_mean = 7.5` constante | No es una medición | Anticipación medida por evento |
| Preferencia fija por modelos de secuencia en la inferencia | No basada en evidencia | Regla de selección por métricas (Plan 17) |
| Tabla `predictions` | Modelo puntual | `forecasts` + `forecast_quantiles` (Plan 16) |
| Inter, Chart.js, tema teal/slate | Rediseño | IBM Plex, Apache ECharts, nuevo sistema visual (Plan 18) |

---

## 6. Prompt maestro para Cursor (bucle de ejecución)

Pegar en Cursor (modo agente) al iniciar cada plan, cambiando `<NN>`:

```text
Eres el agente de implementación de la Plataforma de Monitoreo y Predicción de Gases.
Contexto obligatorio: planes/CONTEXTO_SISTEMA.md, planes/14_REFORMULACION_INDICE.md
y planes/<NN>_*.md. Ante conflicto, el código actual describe el estado; el plan describe el destino.

Ejecuta el plan <NN> fase por fase, paso por paso, en BUCLE:
1. Implementa el siguiente paso pendiente (cambios pequeños, un commit por paso).
2. Ejecuta: python scripts/verify.py --plan <NN>
3. Si algo falla: diagnostica la causa raíz, corrige y vuelve al punto 2.
   No desactives pruebas, no bajes umbrales de cobertura, no marques pruebas como skip
   para “pasar”. Si una prueba está mal planteada, explícalo en la bitácora antes de cambiarla.
4. Cuando el paso quede en verde, regístralo en planes/BITACORA_BUCLE.md
   (paso, archivos tocados, resultado de verify, decisiones) y continúa.
5. Al terminar la fase, revisa su “Definición de terminado” punto por punto.
   Si un punto no se cumple, vuelve al paso correspondiente.
6. Máximo 5 iteraciones fallidas seguidas sobre el mismo paso: detente, escribe en la bitácora
   qué bloquea y qué opciones hay, y pide decisión humana.

Reglas: migraciones solo con Alembic (con downgrade); nada de datos sintéticos; nada de
estadística global en rasgos; vistas operativas en lenguaje natural (pasa el verificador
de lenguaje); secretos solo por variables de entorno.
Al cerrar el plan: actualiza planes/CONTEXTO_SISTEMA.md y la tabla de estado del índice.
```

---

## 7. Estado del paquete (actualizar a mano)

| Plan | Estado | Fecha |
|------|--------|-------|
| 15 Datos reales y formulación | 🟡 G0 medium (6/12/18 min); verify verde; falta visto director | 2026-11-01 |
| 16 Modelo de datos v2 | ⬜ | |
| 17 Modelos transformer | ⬜ | |
| 18 UX/UI lenguaje natural | ⬜ | |
| 19 Usuarios, roles y acceso | ⬜ | |
| 20 Pruebas y bucle | ⬜ (transversal) | |
