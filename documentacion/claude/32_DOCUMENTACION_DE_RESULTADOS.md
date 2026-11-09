# 32 — Documentación de resultados

**Ejecutor:** Claude.  
**Contrato:** [`27_PAQUETE_DISENO_INDICE.md`](27_PAQUETE_DISENO_INDICE.md).  
**Salidas:**

- `docs/diseno/word/03_resultados.docx`
- `docs/diseno/excel/resultados.xlsx`

**Bitácora:** `docs/diseno/bitacora/32.md`.

Este plan no interpreta de más. Cada número del Word y del Excel se copia de un archivo de `reports/` o de un documento de compuerta, con la ruta en la celda `fuente`. Si el archivo no trae el número, la celda queda vacía y la columna `nota` dice «no consta». Redondeo en la prosa: los mismos decimales que el informe fuente, o uno menos si la frase se vuelve ilegible; la hoja Excel conserva el valor completo.

## Fuentes obligatorias, en este orden

- `reports/diagnostico/diagnostico_datos.md` y `diagnostico_datos.json`
- `reports/diagnostico/g0_decision.json`
- `reports/diagnostico/diagnostico_g1.md` y su JSON, si existen
- `docs/g0_visto_director.md`
- `docs/etl/transformaciones.md` y `docs/etl/ultima_corrida.json` si existe
- `reports/eda/resumen.md`
- `reports/thesis/benchmark.json`, `metricas.md`, `ablaciones.md`, `mase_por_modelo.png`
- `reports/real_platform/build_report.md`
- `reports/assistant/eval_2026-11-09.md` y cualquier evaluación posterior en esa carpeta; si hay más de una, se usa la más reciente y se listan las demás en Control
- [`planes/23_AUDITORIA_Y_AJUSTES_TESIS.md`](../../planes/23_AUDITORIA_Y_AJUSTES_TESIS.md) solo para no presentar como cerrado un pendiente que ese plan sigue marcando

No se usan cifras de chats, de capturas ni de planes de intención (el Plan 17 describe metas, no resultados).

## Comprobación conocida a la fecha de corte

Sirve para detectar una copia mal hecha. Si al ejecutar el archivo ya no coincide, gana el archivo y la bitácora explica el cambio. No se «corrija» el archivo para que coincida con esta lista.

Diagnóstico `2026-11-08T01:55:22Z`, fuente `postgresql.gas_readings` con sintético falso:

- 13 894 filas reales, 50 pares sensor-gas, gases CH4, CO, CO2, H2S, NO2 y O2.
- Rango 2023-03-31 a 2025-12-11.
- Duplicados exactos: 0. Casi duplicados en 60 segundos con el mismo valor: 10.
- Δt mediano máximo entre CH₄, CO y H₂S: 5,7708 min. Banda `medium`. Horizontes 6, 12 y 18.
- Δt p50: CH4 5,7708; CO 2,5375; H2S 1,0.
- LIE de CH₄ usado en la conversión: 5,0 %vol.
- Umbrales de episodios: semilla con `verified=false`.
- Inicios que el informe publica y que hay que copiar enteros, no resumir en «pocos»: CH4 vigilar 0,5 con 1 inicio (`no_event_metrics`); CH4 evacuar 1,0 con 1 (`no_event_metrics`); O2 por debajo de 19,5 con 53 (`bootstrap_ic`); O2 por encima de 23,5 con 2 (`no_event_metrics`); CO actuar 25 con 7 (`no_event_metrics`); H2S actuar 1,0 con 59 (`bootstrap_ic`); H2S actuar 5,0 con 7 (`no_event_metrics`); CO2 5 000 con 23 y 30 000 con 13 (`wide_ic_warning`); NO2 0,2 con 23 (`wide_ic_warning`).

ETL sobre `Procesamiento_de_Datos.csv`, conteos de `docs/etl/transformaciones.md`:

- E1 a E3: 13 894 entran y salen, 0 rechazadas. E3: 4 714 conversiones, 0 unidades desconocidas.
- E4: 4 837 incidencias, entre ellas 2 337 fuera de rango físico, 2 335 huecos, 133 saltos imposibles, 32 valores congelados. Las filas no desaparecen por esa marca.
- E6: 13 894 entran y la rejilla produce 821 205 pasos, con 31 imputados y 821 152 faltantes, paso de 1 minuto.

Benchmark `reports/thesis/benchmark.json`, un solo pliegue `fold-0`, `is_final_test` falso:

- Persistencia, backend `native`: MAE 0,01945; RMSE 0,02345; MASE 1; pinball 0,00605; cobertura q10–q90 0,6667; latencia 2,66 ms.
- ETS, backend `holt-native`: MAE 0,01673; RMSE 0,02139; MASE 0,8601; pinball 0,00544; cobertura 0,7083; latencia 3,63 ms.
- No hay otras filas en ese JSON a la fecha de corte. El zoo del Plan 31 no tiene, en este archivo, resultado de TFT, LSTM, fundacionales ni prueba final.

`reports/thesis/ablaciones.md` declara el diseño de ablaciones y, en la corrida escrita, solo el backend de persistencia (`native`) y de ETS (`holt-native`). No se rellena el resto de la tabla de ablaciones con guiones que parezcan ceros.

`reports/real_platform/build_report.md` del `2026-11-08T01:57:08Z`: pasos de migraciones, semillas, superadmin, ETL, eventos, equipos, diagnóstico y benchmark con 4 089 filas y corrida 1. Promoción pedida: no.

Asistente, `reports/assistant/eval_2026-11-09.md`: 60 preguntas; herramienta correcta con el proveedor determinista 60/60; emergencias 2/2; fuera de tema 2/2. Gemini no se midió. No hay autorización escrita para enviar datos de la mina a un proveedor externo. Esa frase entra al Word tal cual, porque es un resultado de gobernanza, no una excusa.

## Estructura del Word

1. Portada. Título: Resultados obtenidos en el caso de estudio. Subtítulo que impida la lectura equivocada: «Evidencia registrada en el repositorio a la fecha de generación. No sustituye la prueba final del protocolo.»
2. Control de versiones y lista de archivos leídos, con su marca de tiempo interna si el archivo la trae.
3. Qué se puede afirmar y qué no. Media página. Incluye: hay caracterización de datos reales; hay una compuerta G0 técnica; hay una corrida de ETL con incidencias; hay un benchmark parcial de dos referencias; la promoción a producción no fue pedida en el informe de reconstrucción; el asistente se evaluó con un proveedor determinista, no con el proveedor de lenguaje de producción.
4. Caracterización de los datos (OE1). Tabla de inventario, huecos de calendario que el diagnóstico liste, Δt por gas prioritario, episodios por gas y nivel con la política de evaluación. Figura solo si el reporte ya trae una imagen; no se genera una gráfica nueva a partir de números redondeados.
5. Compuerta G0. Tabla del visto. Estado de la firma: el que diga `docs/g0_visto_director.md` en el momento de ejecutar. Si falta la firma, se escribe que la decisión técnica está registrada y la firma académica no.
6. Ingesta (OE2). Tabla E1–E6 con entradas, salidas, rechazos e incidencias. Interpretación permitida, en un párrafo: la rejilla es mucho más larga que las lecturas porque el paso de un minuto deja la mayoría de los pasos como faltantes; eso no es un aumento de información.
7. Pronóstico (OE3). Tabla íntegra del JSON. Columna «¿prueba final?» en falso. Párrafo de lectura: ETS baja el MASE por debajo de 1 en este pliegue y esta corrida; la cobertura de ambos queda por debajo del 90 % nominal; con un solo pliegue y sin el resto del zoo no se elige modelo de producción. No se calcule un ganador del zoo.
8. Ablaciones. Lo que el markdown contenga. Si solo hay backends, se dice que la ablación sustantiva (ventana, covariables, ajuste fino) no está en la corrida.
9. Plataforma reconstruida. Pasos del `build_report` y la frase de promoción no pedida.
10. Asistente (complemento de OE4). Tabla de la evaluación y el límite del proveedor real.
11. Objetivos específicos frente a la evidencia. Tabla de cuatro filas, OE1 a OE4, con tres columnas: evidencia que sí está, evidencia que el diseño pide y todavía no está, consecuencia para la tesis. Esta tabla es el cierre honesto. No usa la palabra «éxito» para OE3.
12. Pendientes que los propios reportes dejan abiertos: firma de G0 si falta, datalog crudo por intervalo, zoo incompleto en el JSON, prueba final, promoción, medición de latencia del ciclo completo si no está, proveedor de lenguaje del asistente sin medición, despliegue de nube.

## Estructura del Excel

Hojas: Portada, Control, inventario, g0, episodios, etl, benchmark, ablaciones, reconstruccion, asistente, objetivos.

Cada hoja de cifras tiene la columna `fuente` con la ruta del archivo. La hoja `benchmark` tiene una fila por objeto del JSON, no una fila resumida. La hoja `objetivos` usa solo tres valores en la columna de estado: `evidencia_suficiente`, `evidencia_parcial`, `sin_evidencia_en_reports`. A la fecha de corte, OE3 es `evidencia_parcial`. Claude puede cambiar ese valor solo si un reporte nuevo cubre el zoo y la prueba final, y lo justifica en la bitácora.

Portada: advertencia de una línea. «Las metas del anteproyecto no se copian en este libro como si fueran resultados.»

## Definición de terminado

- Ninguna celda numérica carece de `fuente`.
- El benchmark del Excel tiene las mismas filas que el JSON leído el día de la ejecución.
- El Word dice, en la sección 3 y otra vez en la sección 7, que la corrida no es la prueba final y que no hubo promoción en el informe de reconstrucción.
- La evaluación del asistente no se presenta como medición de Gemini si el informe dice que Gemini no se midió.
- La bitácora registra cualquier cifra de la «comprobación conocida» que ya no coincidía con el archivo.
