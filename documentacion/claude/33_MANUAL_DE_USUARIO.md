# 33 — Manual de usuario

**Ejecutor:** Claude.  
**Contrato:** [`27_PAQUETE_DISENO_INDICE.md`](27_PAQUETE_DISENO_INDICE.md).  
**Salida:** capítulos Markdown en [`docs/manual/`](../../docs/manual/), más la regeneración del PDF si el script sigue siendo válido.  
**Bitácora:** `docs/diseno/bitacora/33.md`.

El manual ya existe y el asistente lo indexa. Este plan no lo reemplaza por un tono nuevo. Completa huecos, alinea cada capítulo con la ruta real y conserva el registro de la mina.

## Fuentes obligatorias

- Todos los archivos actuales de `docs/manual/`.
- `app/modules/assistant/manual_index.py` y `app/modules/assistant/router.py` (rutas `/ayuda` y `/ayuda/{slug}`).
- `app/shared/copy.py`, en especial `FORBIDDEN_TERMS` y los nombres de estado.
- `app/modules/dashboard/ui_router.py` para la lista de pantallas.
- [`18_UX_UI_LENGUAJE_NATURAL.md`](../../planes/18_UX_UI_LENGUAJE_NATURAL.md) y la regla de lenguaje de Vigía.
- [`scripts/export_manual_pdf.py`](../../scripts/export_manual_pdf.py).

## Reglas de redacción

El lector es operador, supervisor o gerencia. El capítulo de laboratorio puede ser más preciso y lleva, al inicio, la frase «Esta sección es para quien carga datos o revisa modelos». Aun ahí se evita el lucimiento: se dice qué botón o qué pantalla hace qué.

- Frases cortas, en presente, con verbo. Primero qué pasa, luego la cifra de ejemplo si hace falta.
- Estados, escritos así: Normal, Vigilar, Actuar ya, Evacuar, Sin datos.
- Un aviso anticipado sale antes de que la lectura llegue al límite. Un aviso confirmado sale cuando la lectura ya lo alcanzó.
- Si la pantalla mira fechas anteriores al último dato, es una revisión histórica. Cada capítulo que muestre fechas lo recuerda.
- Vigía no decide si alguien entra a un frente. Esa frase del capítulo `00` se mantiene.
- Prohibido en los capítulos operativos, porque el verificador y el índice los heredan: modelo, algoritmo, predicción, probabilidad, cuantil, percentil, recall, precisión, F1, RMSE, MAE, MASE, dataset, entrenamiento, staging, production, threshold, lead time, ML, IA, transformer, LSTM, TFT, ETL, JSON, API, ID.
- Equivalencias cuando haya que explicar una idea técnica: «lo que viene», «se espera alrededor de», «podría estar entre», «posibilidad alta, media o baja», «de cada 10 situaciones, avisó a tiempo en N», «avisa N minutos antes», «avisos innecesarios por turno».
- Números de ejemplo en es-CO. No usar como ejemplo una cifra que contradiga el diagnóstico (no inventar un metano de 4 %vol si el umbral de evacuar de la semilla es 1,0).
- Cada archivo conserva el frontmatter que el índice ya entiende: `title`, `roles`, `screens`. Los roles usan los códigos `operador`, `supervisor_seguridad`, `gerencia`, `analista`, `admin`, `auditor`. `screens` lista rutas reales.

## Qué hacer con lo que ya está

Leer `00` a `13`. No reescribir un capítulo que ya dice la verdad de la pantalla. Sí corregir una ruta, un nombre de botón o un rol que ya no coincida con el código.

Capítulos presentes a la fecha de corte, que se conservan como base:

- `00_que_es_vigia.md`
- `01_ingresar.md`
- `02_hoy.md`
- `03_avisos.md`
- `04_equipos_historial.md`
- `05_revisar_un_turno.md`
- `06_confiabilidad.md`
- `07_limites.md`
- `08_informes.md`
- `09_preguntar.md`
- `10_equipo_y_roles.md`
- `11_cargar_datos.md`
- `12_laboratorio.md`
- `13_preguntas_frecuentes.md`

## Huecos que hay que cubrir

Contrastar las rutas de `ui_router.py` con el frontmatter `screens`. Para cada ruta sin capítulo, o bien se añade una sección al capítulo dueño, o bien se crea un archivo nuevo con el mismo frontmatter. Rutas que este plan ya sabe que el menú tiene y que el manual debe nombrar si todavía no lo hace:

- `/resumen` para gerencia.
- `/sala` y `/pantallas` para el kiosco: qué ve la sala, quién crea el token, qué pasa si se revoca. Sin explicar el hash.
- `/bitacora` para el auditor: qué acciones aparecen y qué no puede cambiar.
- `/mi-cuenta`: cambiar la clave, segundo factor si la pantalla lo ofrece. Confirmar en la plantilla antes de describir un control que no esté.
- `/equipo` y `/roles` solo en la medida en que `10_equipo_y_roles.md` no los cubra ya.
- `/datos/calidad` dentro de `11_cargar_datos.md`: qué es un hueco, un salto y un valor fuera de rango, en lenguaje de turno, y que el sistema no los borra para esconderlos.
- `/ayuda`: que el manual también se lee dentro de Vigía, no solo como PDF.

No crear un capítulo «arquitectura» ni «base de datos». Eso es el manual del programador.

## Estructura de un capítulo nuevo o rehecho

1. Frontmatter.
2. Título igual a `title`.
3. Para quién es, en una frase, si el capítulo no es para todos los roles del frontmatter.
4. Qué se hace, en viñetas de acción.
5. Pasos numerados de la tarea principal.
6. Qué puede salir mal y qué hacer (sin disculpas ni «contacte al administrador» vacío: decir la condición, por ejemplo «si no ves equipos, tu cuenta no tiene zonas»).
7. Qué no hace esta pantalla, si hay un riesgo de confundirla con una decisión de seguridad.

El capítulo `09_preguntar.md` debe dejar claras tres cosas que el Plan 26 fija: las cifras salen de Vigía y no de una redacción libre; sin conexión el resto de la plataforma sigue; una emergencia se responde con el protocolo de la mina, no con una orden nueva.

El capítulo `12_laboratorio.md` es el único que puede decir «modelo», «entrenamiento» y «en producción», y debe abrir con el banner de área técnica. Debe decir que entrenar no publica solo: alguien tiene que promover. No copia la tabla de métricas del benchmark: remite a que el laboratorio muestra la corrida que haya, y que un número en rojo es un número en rojo.

`13_preguntas_frecuentes.md` incorpora las respuestas cortas de los huecos nuevos. Cada pregunta apunta al capítulo, no duplica el procedimiento entero.

## PDF

Si `scripts/export_manual_pdf.py` sigue generando `docs/manual/manual_vigia.pdf` desde estos Markdown, ejecutarlo al final y anotar en la bitácora que el PDF quedó regenerado. Si el script falla, no se improvisa otro generador: se anota el error y los Markdown quedan como entregable.

## Definición de terminado

- Toda ruta de usuario de `ui_router.py` está en algún `screens` o la bitácora explica por qué es interna (`/_componentes` y similares no van al manual).
- Un búsqueda de los términos prohibidos en los capítulos distintos de `12_laboratorio.md` no devuelve usos operativos. Si un término aparece en una negación didáctica («aquí no verás la palabra X»), se quita: el manual no enseña la jerga ni para prohibirla.
- El frontmatter de cada archivo sigue siendo válido para `manual_index.py`.
- El tono de `00_que_es_vigia.md` se conserva: Vigía muestra y avisa; la decisión de entrar al frente es del supervisor con la medición en sitio.
