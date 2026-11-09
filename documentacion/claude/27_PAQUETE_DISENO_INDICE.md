# 27 — Índice del paquete documental de diseño

**Ejecutor de los planes 28 a 35:** Claude. Este archivo es el contrato de esa ejecución. Vive en `documentacion/claude/`, aparte de la arquitectura del sistema en `planes/`. No es el capítulo de tesis: es la instrucción para producir los entregables en draw.io, Word, Excel, HTML de maqueta y Markdown.

**Qué no hace este paquete:** no modifica `app/`, `ml_core/`, migraciones, pruebas ni métricas. No reentrena modelos. No inventa resultados.

**Fecha de corte de las fuentes citadas en el paquete:** 2026-11-09. Al ejecutar, se vuelven a leer los archivos. Si un número cambió en el reporte, gana el reporte y la diferencia se anota en la bitácora del plan.

---

## 1. Cómo debe trabajar Claude

1. Leer este índice y el plan que se va a ejecutar. Cada plan se puede ejecutar solo.
2. Leer las fuentes que el plan marca como obligatorias antes de escribir una cifra, un campo o una ruta.
3. Transcribir el contenido normativo que el plan ya redactó (requisitos, historias, nodos, limitaciones). Se puede maquetar. No se puede cambiar el enunciado ni suavizar una limitación.
4. Completar solo lo que el plan encarga al código (tipos del diccionario, rutas HTTP, valores de enumeraciones). Si el código y el plan discrepan, gana el código y la discrepancia queda en `docs/diseno/bitacora/NN.md`.
5. Si un dato no está en la fuente, escribir «no consta en las fuentes a la fecha de corte». Nunca estimarlo.
6. Cerrar el plan con la definición de terminado, punto por punto, en esa bitácora.

Registro: español académico de Colombia, impersonal, frases completas, sigla definida en el primer uso. En la prosa, números en es-CO (coma decimal). En Excel, las celdas de cálculo quedan como número, no como texto. Cuando el dato traiga zona horaria, expresarla en 24 h, América/Bogotá.

## 2. Barra de calidad

El lector es un jurado de maestría en inteligencia artificial y un revisor de ingeniería. El texto debe sostenerse sin el autor en la sala.

- Cada afirmación de diseño apunta a un módulo, una tabla o un plan. Cada afirmación de resultado apunta a un archivo de `reports/`.
- Los diagramas nombran su notación (C4, UML de secuencia, UML de estados, UML de casos de uso, entidad-relación pata de gallo). Llevan título, leyenda y recuadro de control: sistema Vigía, versión 1.0, fuente, fecha.
- Los requisitos son verificables. Las historias de usuario cumplen INVEST y traen criterios en Dado / Cuando / Entonces. Los requisitos no funcionales se expresan además como escenarios de calidad (estímulo, entorno, respuesta, medida).
- El pronóstico y la decisión normativa están separados. El asistente no emite avisos ni órdenes de seguridad.
- Cuando un entregable cite la interfaz operativa, usa el registro de `app/shared/copy.py`: Normal, Vigilar, Actuar ya, Evacuar, Sin datos. El laboratorio y el diseño de IA sí usan el vocabulario técnico.
- Word: portada, control de versiones, tabla de contenido, encabezados numerados, lista de tablas, lista de figuras, referencias. Sin celdas combinadas en las tablas de datos.
- Excel: hojas Portada y Control, encabezado congelado, una fila por registro, sin color decorativo. El color se reserva para un estado que ya existe en Vigía.
- draw.io: un archivo `.drawio` por diagrama, XML que diagrams.net abre sin reparar, conectores ortogonales, legible en A3 (arquitectura y entidad-relación) o A4 (secuencias y estados).

## 3. Fuentes y prioridad

1. Código en `app/`, `ml_core/` y `migrations/versions/`: qué existe.
2. [`CONTEXTO_SISTEMA.md`](../../planes/CONTEXTO_SISTEMA.md): mapa vigente.
3. Planes 14 a 26 y [`docs/etl/transformaciones.md`](../../docs/etl/transformaciones.md): decisiones de diseño.
4. `reports/diagnostico/`, `reports/thesis/`, `reports/eda/`, `reports/real_platform/`, `reports/assistant/`: resultados.
5. Planes 01 a 13: solo si el código todavía los implementa.

Identidad visible: **Vigía · Gases en la mina**. Nombre formal: plataforma de monitoreo y predicción de gases. Caso: mina subterránea de carbón en Colombia. Norma de umbrales: Decreto 1886 de 2015. Horizontes que los datos actuales sostienen: 6, 12 y 18 minutos ([`docs/g0_visto_director.md`](../../docs/g0_visto_director.md)).

## 4. Planes y archivos que cada uno produce

| Plan | Archivo | Entregables |
|------|---------|-------------|
| 27 | este | Contrato. Cumplido al existir. |
| 28 | [`28_DIAGRAMAS_ARQUITECTURA_Y_FLUJOS.md`](28_DIAGRAMAS_ARQUITECTURA_Y_FLUJOS.md) | `docs/diseno/drawio/01` a `11` |
| 29 | [`29_REQUISITOS_HISTORIAS_Y_CASOS_DE_USO.md`](29_REQUISITOS_HISTORIAS_Y_CASOS_DE_USO.md) | Word de requisitos, Excel de historias, diagrama de casos de uso |
| 30 | [`30_MODELO_Y_DICCIONARIO_DE_DATOS.md`](30_MODELO_Y_DICCIONARIO_DE_DATOS.md) | Entidad-relación y Excel del diccionario |
| 31 | [`31_DISENO_SOLUCION_IA.md`](31_DISENO_SOLUCION_IA.md) | Word de diseño de IA y tres draw.io |
| 32 | [`32_DOCUMENTACION_DE_RESULTADOS.md`](32_DOCUMENTACION_DE_RESULTADOS.md) | Word y Excel de resultados |
| 33 | [`33_MANUAL_DE_USUARIO.md`](33_MANUAL_DE_USUARIO.md) | Ajustes en `docs/manual/*.md` |
| 34 | [`34_MANUAL_DEL_PROGRAMADOR.md`](34_MANUAL_DEL_PROGRAMADOR.md) | `docs/programador/*.md` |
| 35 | [`35_MOCKUPS_ESTADO_ACTUAL.md`](35_MOCKUPS_ESTADO_ACTUAL.md) | HTML estático en `mockups/estado-actual/` |

Bitácora, una por plan: `docs/diseno/bitacora/28.md` … `35.md`. Plantilla: fecha, archivos escritos, fuentes leídas, discrepancias, definición de terminado punto por punto.

## 5. Hechos que ningún plan puede contradecir

- Monolito FastAPI, Jinja2, PostgreSQL 15, trabajos con APScheduler en el mismo proceso.
- El zoo vigente está en `ml_core/forecasting/`. Lo que está en `legacy/` no es el diseño actual.
- El sistema pronostica cuantiles y después decide contra umbrales. No entrena la etiqueta «la lectura de ahora ya es alta».
- Un aviso confirmado puede nacer de la regla dura, sin modelo, cuando la lectura ya cruzó el umbral.
- El asistente (`app/modules/assistant/`) usa herramientas tipadas. No escribe SQL, no recibe la base en el prompt y no sustituye el protocolo de la mina.
- `reports/thesis/benchmark.json`, a la fecha de corte, mide persistencia y ETS en `fold-0` y no es la prueba final. Documentar la corrida parcial es parte del rigor.
- Los umbrales de semilla usados para los episodios figuran con `verified=false` hasta verificar el artículo del decreto.
- El despliegue de nube (Plan 09) está pendiente. El diagrama de despliegue es el de borde, con Docker.

## 6. Definición de terminado

- Los planes 28 a 35 existen en esta carpeta, y cada uno declara ejecutor, salidas, fuentes, pasos y definición de terminado.
- [`00_INDICE_Y_ROADMAP.md`](../../planes/00_INDICE_Y_ROADMAP.md) apunta a este paquete.
- Ningún plan de este paquete pide cambiar código de producto.
