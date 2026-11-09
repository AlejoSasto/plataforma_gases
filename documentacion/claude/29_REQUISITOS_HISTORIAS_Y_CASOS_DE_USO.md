# 29 — Requisitos, historias de usuario y casos de uso

**Ejecutor:** Claude.  
**Contrato:** [`27_PAQUETE_DISENO_INDICE.md`](27_PAQUETE_DISENO_INDICE.md).  
**Salidas:**

- `docs/diseno/word/01_requisitos_historias_casos.docx`
- `docs/diseno/excel/historias_y_trazabilidad.xlsx`
- `docs/diseno/drawio/12_casos_de_uso.drawio`

**Bitácora:** `docs/diseno/bitacora/29.md`.

El enunciado de cada requisito, historia y escenario de este archivo es normativo. Claude lo transcribe. Puede partir tablas y numerar figuras. No puede fundir dos requisitos, subir una prioridad ni borrar un criterio.

## Fuentes obligatorias

- [`14_REFORMULACION_INDICE.md`](../../planes/14_REFORMULACION_INDICE.md) §1 y §2 (OE1 a OE4).
- [`19_USUARIOS_ROLES_Y_ACCESO.md`](../../planes/19_USUARIOS_ROLES_Y_ACCESO.md) y la matriz vigente en [`CONTEXTO_SISTEMA.md`](../../planes/CONTEXTO_SISTEMA.md) §7.
- [`26_ASISTENTE_CONVERSACIONAL.md`](../../planes/26_ASISTENTE_CONVERSACIONAL.md) §1.
- Rutas reales antes de cerrar la columna «pantalla» de la trazabilidad.

## Método

Requisitos al estilo de una especificación verificable (ISO/IEC/IEEE 29148, en forma breve): condición, sujeto y resultado observable.

Historias en el formato de Cohn, comprobadas con INVEST. Cada una tiene identificador estable, épica, prioridad MoSCoW, requisitos que satisface y criterios Dado / Cuando / Entonces. Una historia no reemplaza al requisito: la historia cuenta el valor para un rol; el requisito es la condición que el sistema debe cumplir.

Los requisitos no funcionales no se disfrazan de historias de persona. Van como escenarios de calidad (Bass, Clements y Kazman): fuente del estímulo, estímulo, artefacto, entorno, respuesta y medida.

Prioridad: Must es necesario para el objetivo de la tesis o para operar la mina con el sistema; Should es necesario para el uso diario completo; Could es valioso y ya está diseñado, sin ser la evidencia mínima del objetivo.

Actores, con código de rol:

- Administrador, `admin`.
- Supervisor de seguridad, `supervisor_seguridad`.
- Operador de sala, `operador`.
- Gerencia, `gerencia`.
- Analista de datos, `analista`.
- Auditor, `auditor`.
- Kiosco, dispositivo con token, sin cuenta personal.

Separación de deberes: quien entrena no aprueba umbrales, salvo el administrador.

---

## 1. Requisitos funcionales

Transcribir esta tabla al Word y a la hoja `requisitos_funcionales` del Excel.

| ID | Enunciado | MoSCoW | OE | Permiso |
|----|-----------|--------|----|---------|
| RF-01 | El sistema autentica con correo y contraseña y abre una sesión con vencimiento corto y renovación por token de refresco. | Must | OE4 | — |
| RF-02 | El sistema bloquea el ingreso tras intentos fallidos repetidos y responde con un mensaje que no revela si el correo existe. | Must | OE4 | — |
| RF-03 | El sistema ofrece invitación, recuperación, cambio obligatorio de clave y segundo factor, y deja constancia en la bitácora. | Should | OE4 | `users.manage` para invitar |
| RF-04 | Al entrar, cada rol aterriza en su vista: gerencia en el resumen, analista en el panel técnico, auditor en la bitácora y el resto en Hoy. | Must | OE4 | según rol |
| RF-05 | Hoy muestra el estado por equipo y por gas, el nivel (Normal, Vigilar, Actuar ya, Evacuar o Sin datos) y hasta qué fecha hay lecturas. | Must | OE4 | `status.view` |
| RF-06 | Un operador solo ve los equipos de sus zonas. Sin zonas asignadas, no ve equipos. | Must | OE4 | alcance |
| RF-07 | El sistema ingesta un Excel `dls_report` o el CSV consolidado, registra la corrida y sus etapas, y no admite filas sintéticas. | Must | OE2 | `data.upload` |
| RF-08 | La pantalla de calidad muestra los problemas detectados sin borrarlos del linaje. | Must | OE1 | `data.quality.view` |
| RF-09 | El sistema construye una rejilla temporal causal: rellena solo huecos cortos y deja el hueco largo como faltante. | Must | OE2 | interno |
| RF-10 | El sistema guarda un pronóstico probabilístico a 6, 12 y 18 minutos, con cuantiles, para el modelo que esté en producción. | Must | OE3 | interno |
| RF-11 | La decisión de aviso compara ese pronóstico con el umbral normativo vigente en la fecha del dato. | Must | OE3 | interno |
| RF-12 | Si la lectura ya cruzó el umbral, el sistema emite un aviso confirmado aunque el modelo no esté disponible. | Must | OE3 | interno |
| RF-13 | El aviso muestra, en lenguaje no técnico, qué pasó, por qué se avisó y qué hacer, y distingue anticipado de confirmado. | Must | OE4 | `alerts.view` |
| RF-14 | Quien tiene permiso puede marcar «Ya lo vi» y cerrar el aviso, y el cierre queda atribuido a la persona. | Must | OE4 | `alerts.acknowledge`, `alerts.resolve` |
| RF-15 | El sistema notifica los avisos en vivo a los contactos suscritos y solo registra, sin reenviar, los históricos. | Should | OE4 | `stakeholders.manage` para configurar |
| RF-16 | Confiabilidad muestra, para el rol operativo, si el pronóstico sirvió y de dónde sale esa afirmación, sin jerga de entrenamiento. | Must | OE4 | `reliability.view` |
| RF-17 | El laboratorio compara modelos con las mismas métricas y el mismo protocolo, y distingue staging de producción. | Must | OE3 | `models.train`, `models.promote` |
| RF-18 | Promover un modelo es un paso distinto de entrenarlo y queda en la bitácora. | Must | OE3 | `models.promote` |
| RF-19 | Un supervisor puede consultar y versionar los límites normativos, con la cita del decreto y la marca de si el artículo ya fue verificado. | Must | OE4 | `thresholds.manage` |
| RF-20 | Gerencia consulta el resumen y exporta informes del periodo, sin entrar al laboratorio. | Must | OE4 | `reports.export` |
| RF-21 | El auditor lee la bitácora de acciones sensibles y no modifica umbrales ni modelos. | Should | OE4 | `audit.view` |
| RF-22 | El asistente responde en lenguaje natural usando solo cifras devueltas por herramientas autorizadas para el permiso de quien pregunta. | Should | OE4 | el de cada herramienta |
| RF-23 | El manual de uso se puede leer dentro de la plataforma y el asistente puede citarlo. | Should | OE4 | sesión |
| RF-24 | El kiosco muestra la sala sin una sesión personal, mediante un token que se puede revocar. | Could | OE4 | `kiosk.manage` para crearlo |

## 2. Requisitos no funcionales

Hoja `requisitos_no_funcionales`. Característica según ISO/IEC 25010.

| ID | Característica | Enunciado | Medida | MoSCoW |
|----|----------------|-----------|--------|--------|
| RNF-01 | Exactitud de los datos | Ningún entrenamiento, validación ni métrica usa filas con `is_synthetic` verdadero. | Restricción en base y prueba automática en verde. | Must |
| RNF-02 | Exactitud del modelo | En el instante t, los rasgos y la normalización usan solo información anterior o igual a t, ajustada en el bloque de entrenamiento de esa partición. | Pruebas de no fuga. Embargo: fin de entrenamiento más embargo anterior a la emisión. | Must |
| RNF-03 | Fiabilidad | Un fallo del pronóstico no deshace una ingesta ya aceptada. | El ETL queda en éxito y el ciclo de modelo queda registrado como fallo. | Must |
| RNF-04 | Integridad | Repetir la carga del mismo archivo y del mismo par sensor-tiempo no duplica la lectura. | Único `(sensor_id, tiempo_inicio)` y huella de archivo. | Must |
| RNF-05 | Seguridad | La sesión viaja en cookies HttpOnly. Las escrituras llevan CSRF. La clave no aparece en la URL. | Revisión de `POST /ingresar` y del middleware. | Must |
| RNF-06 | Seguridad | Tras 5 ingresos fallidos la cuenta queda bloqueada 15 minutos. | Comportamiento de `users.locked_until`. | Must |
| RNF-07 | Confidencialidad | El asistente no recibe la base en el prompt, no genera SQL y cada herramienta exige un permiso. | Inspección de `app/modules/assistant/tools/`. | Must |
| RNF-08 | Integridad de la respuesta | Toda cifra de una respuesta del asistente pertenece a la evidencia de ese turno. | Verificación en `grounding.py`. | Must |
| RNF-09 | Seguridad de uso | El asistente no inventa una orden de evacuación. Ante una emergencia usa la respuesta fija y remite al protocolo de la mina. | Casos del evaluador del asistente. | Must |
| RNF-10 | Usabilidad | Las pantallas operativas no muestran la jerga prohibida en `copy.FORBIDDEN_TERMS`. | Verificador de lenguaje del Plan 20. | Must |
| RNF-11 | Adecuación funcional | Los horizontes prometidos en la interfaz son 6, 12 y 18 minutos, no 5 y 10. | `app_settings` y el visto G0. | Must |
| RNF-12 | Portabilidad de operación | Vigilar, pronosticar y avisar funciona sin internet en el equipo de bocamina. | Compose local. El asistente externo puede faltar. | Must |
| RNF-13 | Eficiencia | El modelo en producción debe poder recorrer los sensores del ciclo en menos de 1 segundo en una CPU de 4 núcleos. | Meta del Plan 17. Si la corrida no la midió, el resultado lo dice y no se da por cumplida. | Should |
| RNF-14 | Trazabilidad | Cada aviso guarda nivel, umbral, lectura o pronóstico de origen, y el resultado posterior cuando ya se pudo evaluar. | Tablas `alerts` y `alert_outcomes`. | Must |
| RNF-15 | Separación de deberes | Entrenar y promover son permisos distintos. Aprobar umbrales no viaja con el permiso de entrenar. | Matriz de roles. | Must |
| RNF-16 | Mantenibilidad | El esquema cambia solo por migraciones Alembic con downgrade. | Cadena en `migrations/versions/`. | Must |
| RNF-17 | Honestidad | Si una meta del anteproyecto no se alcanza con los datos reales, la interfaz y la tesis lo muestran. | Laboratorio en verde o rojo sin ajuste manual de la cifra. | Must |

## 3. Historias de usuario

Hoja `historias`. Columnas: ID, épica, rol, historia, beneficio, MoSCoW, RF, RNF, criterios, pantalla. El texto de la historia en el Word es: «Como [rol], quiero [historia], para [beneficio].»

### Épica Acceso

**HU-ACC-01.** Rol: cualquier persona autorizada. Historia: entrar con mi correo y mi clave. Beneficio: llegar a mi trabajo sin compartir una cuenta. Must. RF-01, RF-04. RNF-05.

- Dado que mi cuenta está activa y no bloqueada, cuando envío correo y clave correctos en `/ingresar`, entonces recibo una sesión y aterrizo en la vista de mi rol.
- Dado que la clave es incorrecta, cuando envío el formulario, entonces veo un mensaje genérico y no quedo autenticado.
- Dado que la URL trae la clave en la consulta, cuando el sistema la recibe, entonces redirige a `/ingresar` limpio y no reutiliza esa clave.

**HU-ACC-02.** Rol: cualquier persona autorizada. Historia: que la cuenta se detenga si alguien prueba claves una y otra vez. Beneficio: reducir el acceso forzoso. Must. RF-02. RNF-06.

- Dado que ya hubo 5 fallos, cuando intento de nuevo antes de 15 minutos, entonces la cuenta sigue bloqueada y el mensaje no dice si el correo existe.

**HU-ACC-03.** Rol: administrador. Historia: invitar a una persona con un rol y un plazo corto. Beneficio: no compartir la clave del administrador. Should. RF-03.

- Dado que tengo `users.manage`, cuando invito un correo, entonces existe una invitación de 72 horas y la bitácora registra `user.invited`.

**HU-ACC-04.** Rol: operador. Historia: ver solo los equipos de mis zonas. Beneficio: no actuar sobre un frente que no me corresponde. Must. RF-06.

- Dado que tengo zonas asignadas, cuando abro Hoy, entonces no aparecen equipos de otras zonas.
- Dado que no tengo zonas, cuando abro Hoy, entonces no aparece ningún equipo.

### Épica Turno

**HU-OPE-01.** Rol: operador. Historia: ver al entrar si algún gas está en Vigilar, Actuar ya o Evacuar. Beneficio: atender primero lo que exige acción. Must. RF-05. RNF-10, RNF-11.

- Dado que hay lecturas, cuando abro Hoy, entonces cada equipo muestra nivel, lectura y la fecha hasta la cual hay datos.
- Dado que miro fechas anteriores al último dato, cuando la pantalla carga, entonces se entiende que es una revisión histórica y no la situación de este momento.

**HU-OPE-02.** Rol: supervisor. Historia: revisar un turno ya pasado con los mismos nombres de estado. Beneficio: reconstruir qué se avisó sin interpretar una gráfica cruda. Must. RF-05, RF-16.

- Dado que elijo un periodo cerrado, cuando abro el historial, entonces veo estados y avisos de ese periodo, marcados como históricos.

**HU-GER-01.** Rol: gerencia. Historia: abrir un resumen del periodo sin entrar al laboratorio. Beneficio: rendir cuentas sin leer métricas de entrenamiento. Must. RF-04, RF-20. RNF-10.

- Dado que mi único rol operativo de aterrizaje es gerencia, cuando ingreso, entonces llego a `/resumen` y no veo el laboratorio en el menú.

### Épica Avisos

**HU-AVI-01.** Rol: operador. Historia: leer qué pasó, por qué se avisó y qué hacer, en frases de la mina. Beneficio: actuar sin un intermediario técnico. Must. RF-13. RNF-10, RNF-14.

- Dado un aviso abierto, cuando abro su detalle, entonces veo el mensaje, la recomendación y si es anticipado o confirmado.
- Dado ese texto, cuando lo reviso, entonces no contiene los términos prohibidos del registro operativo.

**HU-AVI-02.** Rol: operador. Historia: marcar «Ya lo vi» y cerrar el aviso cuando el turno terminó la acción. Beneficio: que el siguiente turno no herede un aviso ya atendido. Must. RF-14.

- Dado un aviso abierto y el permiso de reconocer, cuando marco «Ya lo vi», entonces el estado pasa a reconocida y queda mi usuario y la hora.
- Dado un aviso ya resuelto, cuando intento reconocerlo, entonces el sistema no lo reabre.

**HU-AVI-03.** Rol: supervisor. Historia: que un gas que ya cruzó el límite avise aunque el pronóstico falle. Beneficio: no dejar la seguridad apoyada solo en el modelo. Must. RF-12. RNF-03.

- Dado que la lectura actual supera el umbral vigente, cuando corre el ciclo, entonces existe un aviso confirmado.
- Dado que el modelo lanza un error, cuando la ingesta ya se aceptó, entonces las lecturas siguen guardadas.

**HU-AVI-04.** Rol: contacto suscrito. Historia: recibir el aviso en vivo y no recibir otra vez los históricos cuando alguien revisa el pasado. Beneficio: no tratar una revisión como emergencia. Should. RF-15.

- Dado un aviso de origen en vivo y una suscripción que cubre ese equipo y ese nivel, cuando el aviso nace, entonces queda un intento de notificación.
- Dado un aviso histórico, cuando se consulta el periodo, entonces no se crea un envío nuevo.

### Épica Datos

**HU-DAT-01.** Rol: analista. Historia: cargar el consolidado real o un Excel de campo y ver cuántas filas entraron y cuántas se rechazaron. Beneficio: saber si la corrida quedó completa. Must. RF-07. RNF-01, RNF-04.

- Dado el CSV consolidado, cuando ejecuto la carga prevista, entonces las filas quedan ligadas a una corrida con etapas E1 a E6.
- Dado un archivo ya cargado, cuando lo cargo de nuevo, entonces no aparecen lecturas duplicadas del mismo sensor y el mismo inicio.

**HU-DAT-02.** Rol: analista. Historia: ver huecos, saltos imposibles y valores fuera de rango sin que el sistema los borre en silencio. Beneficio: explicar la calidad del dato en la tesis y en la operación. Must. RF-08, RF-09. RNF-01.

- Dado el diagnóstico de la última corrida, cuando abro calidad, entonces los códigos de problema coinciden con los que el ETL registró.
- Dado un hueco largo, cuando miro la rejilla, entonces el paso queda faltante y no relleno con un valor futuro.

### Épica Laboratorio

**HU-LAB-01.** Rol: analista. Historia: comparar el zoo contra la persistencia con el mismo protocolo temporal. Beneficio: defender qué modelo aporta y cuál no. Must. RF-17. RNF-02, RNF-17.

- Dado que hay una evaluación guardada, cuando abro comparar, entonces veo las métricas de esa corrida y si el bloque es prueba final o no.
- Dado que un modelo no supera a la persistencia, cuando miro la selección, entonces no aparece como producción por el solo hecho de ser un transformer.

**HU-LAB-02.** Rol: analista con permiso de promover, o administrador. Historia: dejar un modelo en producción solo cuando alguien lo promueve a propósito. Beneficio: evitar que un entrenamiento nocturno cambie lo que ve la mina. Must. RF-18. RNF-15.

- Dado un modelo en staging, cuando termina el entrenamiento, entonces sigue en staging hasta la promoción.
- Dado que promuevo, cuando la acción acaba, entonces la bitácora tiene `ml.promote`.

**HU-LAB-03.** Rol: supervisor. Historia: editar un límite con su cita y saber si el artículo ya se verificó. Beneficio: no presentar como norma cerrada un umbral todavía en semilla. Must. RF-19.

- Dado un umbral con `verified` falso, cuando lo consulto, entonces la ficha muestra que falta verificar el artículo.
- Dado que no tengo `thresholds.manage`, cuando intento guardarlo, entonces recibo denegación.

### Épica Informes y auditoría

**HU-INF-01.** Rol: gerencia o supervisor. Historia: exportar el periodo a un informe. Beneficio: llevar la evidencia fuera de la pantalla. Must. RF-20.

- Dado un periodo con datos, cuando pido el informe y tengo `reports.export`, entonces obtengo el archivo y queda el registro de quién lo generó.

**HU-AUD-01.** Rol: auditor. Historia: leer quién entró, quién promovió un modelo y quién cambió un límite. Beneficio: reconstruir decisiones sin pedir claves ajenas. Should. RF-21. RNF-15.

- Dado mi rol de auditor, cuando ingreso, entonces aterrizo en `/bitacora` y no tengo acciones de promover ni de editar umbrales.

### Épica Asistente

**HU-ASI-01.** Rol: operador. Historia: preguntar cómo van los gases de mis equipos y recibir cifras de la base, no una redacción suelta. Beneficio: resolver una duda sin recorrer todas las pantallas. Should. RF-22. RNF-07, RNF-08.

- Dado que pregunto por un equipo fuera de mi alcance, cuando el asistente consulta, entonces no recibe esas filas.
- Dado que la respuesta incluye un número, cuando el servidor la verifica, entonces ese número está en la evidencia del turno.

**HU-ASI-02.** Rol: cualquier persona en la mina. Historia: que una pregunta de emergencia no dependa del modelo de lenguaje. Beneficio: no recibir una instrucción inventada. Must. RF-22. RNF-09.

- Dado un texto clasificado como emergencia, cuando pregunto, entonces la respuesta es la fija del protocolo y no una orden nueva del modelo.

**HU-ASI-03.** Rol: operador. Historia: seguir usando Hoy y los avisos cuando no hay red para el asistente. Beneficio: que la ayuda conversacional no sea un punto único de fallo. Must. RF-05. RNF-12.

- Dado que no hay clave o no hay red, cuando miro el botón, entonces dice que el asistente no está disponible y Hoy sigue cargando.

**HU-ASI-04.** Rol: persona nueva en el turno. Historia: preguntar cómo cerrar un aviso y caer en el manual. Beneficio: aprender la pantalla sin una capacitación aparte. Should. RF-23.

- Dado que pregunto cómo se usa una pantalla, cuando el asistente responde, entonces cita una sección de `docs/manual/` y el enlace abre `/ayuda`.

### Épica Kiosco

**HU-KIO-01.** Rol: supervisor. Historia: dejar una pantalla de sala encendida sin la cuenta de una persona. Beneficio: publicar el estado del turno en el cuarto de control. Could. RF-24.

- Dado un token de kiosco no revocado, cuando abro `/sala` con ese token, entonces veo la sala sin el menú de administración.
- Dado que revoco el token, cuando la pantalla vuelve a pedir datos, entonces ya no entra.

## 4. Escenarios de calidad

Hoja `escenarios_calidad`. No son historias de usuario.

| ID | RNF | Fuente | Estímulo | Entorno | Respuesta | Medida |
|----|-----|--------|----------|---------|-----------|--------|
| EC-01 | RNF-01 | Analista | Intenta evaluar con filas sintéticas | Base de desarrollo | El cargador y la restricción lo impiden | Cero filas `is_synthetic` verdaderas en la métrica |
| EC-02 | RNF-02 | Corrida de benchmark | Parte el tiempo | Datos irregulares del caso | El pliegue de prueba no entra al ajuste | `train_end + embargo < issued_at` |
| EC-03 | RNF-05 | Atacante de sesión | Envía un POST sin CSRF | Navegador de la mina | La escritura se rechaza | Ningún cambio de estado |
| EC-04 | RNF-08 | Operador | Pregunta una concentración | Asistente con herramientas | El texto solo usa la evidencia | El verificador no encuentra cifras ajenas |
| EC-05 | RNF-10 | Operador | Lee un aviso | Vista operativa | Frases de `copy.py` | El verificador de lenguaje pasa |
| EC-06 | RNF-12 | Bocamina | Se corta internet | Docker local | Hoy, avisos y pronóstico local siguen | El asistente externo puede mostrar no disponible |
| EC-07 | RNF-13 | Ciclo de inferencia | Pronostica todos los sensores | CPU de 4 núcleos | Completa el ciclo | Menos de 1 s, o «no medido» si la corrida no lo trae |
| EC-08 | RNF-17 | Jurado | Pide el recall del anteproyecto | Datos con pocos episodios de CH₄ | Se muestra el intervalo y la limitación | No aparece un 95 % sin episodios suficientes |

## 5. Casos de uso

Diagrama `12_casos_de_uso.drawio`, UML. Un sistema: Vigía. Actores como en la lista inicial. El kiosco es un actor no humano. Incluir los casos CU-01 a CU-12 y las relaciones de inclusión que aquí se nombran.

Ficha corta en el Word, una por caso: actor principal, precondición, flujo principal en pasos numerados, extensiones, RF que cubre. El flujo no inventa pantallas: usa las rutas del Plan 28.

| ID | Nombre | Actor principal | Incluye | RF |
|----|--------|-----------------|---------|----|
| CU-01 | Ingresar | Persona autorizada | — | RF-01, RF-02, RF-04 |
| CU-02 | Consultar el estado del turno | Operador | CU-01 | RF-05, RF-06 |
| CU-03 | Atender un aviso | Operador | CU-01 | RF-13, RF-14 |
| CU-04 | Revisar un periodo pasado | Supervisor | CU-01 | RF-05, RF-16 |
| CU-05 | Cargar lecturas | Analista | CU-01 | RF-07, RF-08 |
| CU-06 | Comparar y promover un modelo | Analista | CU-01 | RF-17, RF-18 |
| CU-07 | Administrar límites | Supervisor | CU-01 | RF-19 |
| CU-08 | Exportar un informe | Gerencia | CU-01 | RF-20 |
| CU-09 | Consultar la bitácora | Auditor | CU-01 | RF-21 |
| CU-10 | Preguntar | Operador | CU-01 | RF-22, RF-23 |
| CU-11 | Publicar la sala en kiosco | Supervisor | — | RF-24 |
| CU-12 | Recibir un aviso en vivo | Contacto | — | RF-15 |

CU-11 no incluye CU-01: el kiosco no abre sesión de persona.

## 6. Trazabilidad

Hoja `trazabilidad`. Una fila por requisito funcional. Columnas: RF, OE, historias, caso de uso, módulo (el de `app/modules/` o `ml_core`), pantalla, RNF relacionado. Claude la arma cruzando las tablas de este plan. Si una pantalla no existe en `ui_router.py`, la celda queda «no consta» y se anota en la bitácora. No se inventa la ruta.

## 7. Estructura del Word

1. Portada. Título: Especificación de requisitos, historias de usuario y casos de uso. Sistema: Vigía. Subtítulo: plataforma de monitoreo y predicción de gases. Fecha de generación. Fuente: Plan 29.
2. Control de versiones. Fila 1.0, generación inicial desde el plan.
3. Propósito, alcance y exclusiones. Exclusiones literales: no decide el ingreso a un frente; no ingiere `alarmReport` ni el historial de sesiones MX6; el asistente no sustituye el protocolo; la nube del Plan 09 está fuera de este documento de diseño construido.
4. Definiciones. La primera vez: ETL, pronóstico cuantílico, aviso anticipado, aviso confirmado, staging, producción, horizonte, Decreto 1886 de 2015.
5. Actores.
6. Requisitos funcionales.
7. Requisitos no funcionales.
8. Historias de usuario, agrupadas por épica.
9. Escenarios de calidad.
10. Casos de uso, con el diagrama embebido o referido por nombre de archivo.
11. Matriz de trazabilidad.
12. Referencias: Decreto 1886 de 2015; ISO/IEC/IEEE 29148; ISO/IEC 25010; Cohn, *User Stories Applied*; Bass, Clements y Kazman, *Software Architecture in Practice*; planes 14, 19 y 26 de este repositorio.

## 8. Estructura del Excel

Hojas, en este orden: Portada, Control, requisitos_funcionales, requisitos_no_funcionales, historias, escenarios_calidad, casos_de_uso, trazabilidad.

Portada: sistema, documento, versión 1.0, fecha, advertencia de que el enunciado vive en el Plan 29 y el código gana si hay conflicto de rutas.

## Definición de terminado

- Los tres archivos de salida existen.
- Las 24 historias y los 8 escenarios están completos, con sus criterios, y ningún Must del §1 quedó sin historia o sin caso de uso.
- RNF-13 no aparece como cumplido: aparece como meta, condicionada a la medición.
- El diagrama de casos de uso tiene los doce casos y la nota de que CU-11 no pasa por el ingreso de persona.
- La bitácora lista las rutas que hubo que corregir contra `ui_router.py`.
