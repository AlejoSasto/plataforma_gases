# 28 — Diagramas de arquitectura y de flujos

**Ejecutor:** Claude.  
**Contrato:** [`27_PAQUETE_DISENO_INDICE.md`](27_PAQUETE_DISENO_INDICE.md).  
**Salidas:** doce archivos en `docs/diseno/drawio/` (este plan cubre `01` a `11`; el `12` de casos de uso lo produce el Plan 29 y el `13` de entidad-relación el Plan 30).  
**Bitácora:** `docs/diseno/bitacora/28.md`.

Este plan fija nodos y relaciones. Claude los dibuja. No agrega servicios, colas ni nubes que el código no tenga.

## Fuentes obligatorias

- [`CONTEXTO_SISTEMA.md`](../../planes/CONTEXTO_SISTEMA.md) §3, §4 y §8.
- [`planes/26_ASISTENTE_CONVERSACIONAL.md`](../../planes/26_ASISTENTE_CONVERSACIONAL.md) §2, contrastado con `app/modules/assistant/`.
- [`docs/etl/transformaciones.md`](../../docs/etl/transformaciones.md).
- Rutas de `app/modules/dashboard/ui_router.py` y `app/modules/assistant/router.py`.
- Estados de aviso en `app/modules/alerts/service.py`: `abierta`, `reconocida`, `resuelta`.

## Reglas de dibujo

- Formato `.drawio` (mxfile), una página por archivo, diagrams.net lo abre sin reparar.
- Recuadro de control en cada página: Vigía, nombre del diagrama, notación, versión 1.0, fuente, fecha de generación.
- Conectores ortogonales. Texto en español. Sin iconos de proveedores que el sistema no usa.
- C4 en `01`, `02` y `03`. UML de secuencia en `05` a `09`. UML de estados en `10`. Mapa de navegación en `11`. Flujo de actividades en `04` y `06`.
- El asistente es un módulo del monolito, no un decisor de seguridad. En todo diagrama donde aparezca, una nota dice: «No emite avisos ni órdenes de evacuación».

## 01 — `01_contexto_c4.drawio`

Notación C4, nivel de contexto.

Personas: Operador de sala, Supervisor de seguridad, Gerencia, Analista de datos, Auditor, Administrador, Pantalla de kiosco.

Sistema central: **Vigía**.

Sistemas externos, con la relación exacta:

- Detectores portátiles, vía archivos iNet `dls_report` y CSV consolidado. No hay enlace en vivo al instrumento.
- Proveedor de lenguaje (Gemini), solo si `ASSISTANT_PROVIDER` está configurado y hay red. Opcional y degradable.
- Correo SMTP, solo si las notificaciones no están en `dry_run`.

Relaciones: las personas usan Vigía; Vigía lee archivos de campo; Vigía puede consultar al proveedor de lenguaje; Vigía puede dejar avisos en correo o en `storage/outbox/`.

Nota de alcance: `alarmReport_*.xlsx` y el historial de sesiones MX6 no entran.

## 02 — `02_contenedores_c4.drawio`

Contenedores del borde (Docker Compose):

- Navegador (Jinja2, ECharts, htmx, recursos locales, sin CDN).
- Aplicación FastAPI (`app/main.py`): HTTP, sesión, ETL, ciclo de pronóstico, asistente, informes. APScheduler en el mismo proceso.
- PostgreSQL 15, base `proyecto_gases`.
- MLflow, seguimiento de experimentos.
- Volúmenes: `data/inbox`, `storage/reports`, `storage/outbox`.

Flechas: el navegador habla solo con FastAPI; FastAPI lee y escribe PostgreSQL; el ciclo de modelos lee artefactos y registra en MLflow; el asistente, si hay clave, sale hacia el proveedor. Sin clave, el botón informa que no hay asistente y el resto sigue.

Nota: el servicio `app` del Compose no monta `data/`. La carga masiva documentada corre en el host. Dibujarlo como nota, no como un contenedor extra.

## 03 — `03_componentes_c4.drawio`

Dentro de FastAPI, los módulos y la dependencia que ya declara el contexto:

`core` sostiene a `auth`, `users`, `roles_permissions`, `catalog`, `sensors_ingestion`, `ml_training`, `forecasting`, `alerts`, `stakeholders`, `dashboard`, `reports`, `audit`, `assistant`.

Cadena de datos: `sensors_ingestion` → `ml_training` → `forecasting` → `alerts` → `stakeholders`.

`assistant` llama a los `service.py` de esos módulos. No tiene SQL propio. `ml_core/forecasting` queda fuera del cuadro de FastAPI, como librería que `forecasting` invoca.

## 04 — `04_despliegue_borde.drawio`

Un nodo físico: equipo en bocamina, sin dependencia de internet para vigilar, pronosticar y avisar.

Dentro: los contenedores del diagrama 02. Puertos de desarrollo que el contexto documenta: aplicación 8000, PostgreSQL publicado en 5433, MLflow 5000. Marcarlos como puertos locales de la instalación descrita, no como exposición a internet.

Un nodo aparte, punteado y etiquetado **pendiente**: sincronización a nube del Plan 09. No dibujar Dataflow, Composer ni Looker.

## 05 — `05_secuencia_autenticacion.drawio`

Participantes: Navegador, middleware CSRF, router de auth, servicio de usuarios, PostgreSQL.

Flujo principal, en este orden:

1. `GET /ingresar` entrega formulario y cookie `csrf_token`.
2. `POST /ingresar` (formulario) o `POST /auth/login` (JSON) con el token.
3. Verificación de contraseña, bloqueo a los 5 fallos durante 15 minutos, mensaje genérico.
4. Cookie `access_token` (JWT, 15 min, HttpOnly) y `refresh_token` opaco (8 h, rotación).
5. Redirección según rol: gerencia a `/resumen`, analista a la vista de ingeniero, auditor a `/bitacora`, el resto a `/`.

Alternos, como fragmentos `alt`: credenciales inválidas; cuenta bloqueada; sin permiso (403); kiosco por `/sala?kiosk=` con token hasheado.

## 06 — `06_flujo_etl.drawio`

Actividad E1–E6, con el significado de [`docs/etl/transformaciones.md`](../../docs/etl/transformaciones.md):

- E1 Extraer. Excel hoja `Resumen`, cabecera fila 24, o CSV consolidado.
- E2 Validar. Quince columnas canónicas, lectura numérica, fechas interpretables.
- E3 Estandarizar. Gas y sensor canónicos. Metano de %LEL a %vol con LIE 5,0. CO₂ de %vol a ppm.
- E4 Calidad. Marca problemas; no borra la fila por el solo hecho de marcarla.
- E5 Cargar. Idempotente por huella del archivo y por (`sensor`, `tiempo_inicio`). `is_synthetic` solo puede ser falso.
- E6 Rejilla. Paso regular. Relleno hacia adelante solo en huecos cortos. Hueco largo queda faltante. No se interpola hacia el futuro.

Después de un E5 exitoso, el ciclo de pronóstico se dispara. Un fallo del modelo no revierte el ETL. Inbox: éxito a `processed`, error a `failed`.

Disparadores en el mismo diagrama, como carriles: carga por API, bandeja `data/inbox`, script del consolidado.

## 07 — `07_secuencia_pronostico_aviso.drawio`

Participantes: ciclo de pronóstico, `ml_core`, catálogo de umbrales, alertas, contactos.

Orden:

1. La rejilla entrega el contexto hasta el instante `t`. No entra información posterior a `t`.
2. El modelo en producción devuelve cuantiles a 6, 12 y 18 minutos.
3. La capa de decisión estima la posibilidad de cruzar cada nivel del Decreto 1886 y elige Normal, Vigilar, Actuar ya o Evacuar.
4. Si la lectura actual ya cruzó el umbral, el aviso es `confirmado` y no depende del modelo.
5. Si el cruce es futuro, el aviso es `anticipado`, ligado al pronóstico.
6. Se guardan `forecasts`, `forecast_quantiles`, `forecast_explanations` y `alerts`.
7. La notificación sale solo para origen en vivo. El histórico se registra y no se reenvía.
8. Más tarde, `alert_outcomes` compara el aviso con `threshold_events`.

Nota: la frase del aviso sale de plantillas (`narrator`), no de un modelo de lenguaje.

## 08 — `08_secuencia_entrenamiento.drawio`

Participantes: Analista, API o script de benchmark, walk-forward, adaptadores, MLflow, `model_registry`, quien tiene `models.promote`.

Orden:

1. Lecturas reales desde PostgreSQL. Se rechaza cualquier fila sintética.
2. Partición temporal con purga y embargo: el fin de entrenamiento más el embargo es anterior al instante de emisión.
3. Cada adaptador implementa el mismo contrato: ajustar y devolver cuantiles.
4. Métricas de pronóstico y, cuando hay episodios suficientes, métricas de evento.
5. El candidato queda en `staging`. Pasar a producción es un acto explícito, auditado, de otro permiso (`models.promote`).
6. Si nadie supera a la persistencia (MASE menor que 1), la persistencia sigue activa y el laboratorio lo dice.

Nota visible: la corrida publicada a la fecha de corte no recorre este zoo completo. El diagrama es el diseño; la evidencia medida está en el Plan 32.

## 09 — `09_secuencia_asistente.drawio`

Participantes: Navegador, `POST /api/asistente`, proveedor de lenguaje, herramientas, servicios de dominio, PostgreSQL (lectura acotada al permiso del usuario).

Orden, tomado del Plan 26 y verificado contra `app/modules/assistant/`:

1. El cuerpo trae el historial y el token CSRF. El prompt de sistema no lleva cifras de la mina.
2. El modelo pide una herramienta por nombre y parámetros tipados. Máximo cinco rondas.
3. El servidor valida parámetros, aplica el alcance del usuario y ejecuta el `service.py` dueño del dato.
4. El resultado vuelve como evidencia. El texto final solo puede usar cifras de esa evidencia.
5. La respuesta puede incluir bloques (tabla, gráfico, enlace a informe o al manual).
6. El turno queda en auditoría.

Alternos: emergencia con respuesta fija y remisión al protocolo; pregunta fuera de tema; sin red o sin clave, mensaje de no disponibilidad y la plataforma operativa intacta.

## 10 — `10_estados_aviso.drawio`

UML de estados del campo `alerts.status`:

- Inicial: `abierta`.
- `abierta` → `reconocida` cuando alguien con `alerts.acknowledge` marca «Ya lo vi».
- `reconocida` o `abierta` → `resuelta` cuando alguien con `alerts.resolve` cierra, con nota opcional.
- `resuelta` no vuelve atrás. El servicio rechaza reconocer una alerta ya resuelta.

Estados paralelos, en un segundo rectángulo, no mezclados con el ciclo de vida:

- `kind`: `anticipado` o `confirmado`. Se fija al nacer.
- `origin`: `en_vivo` o histórico. Solo el vivo notifica.
- `alert_outcomes.outcome`: empieza en `pendiente` y luego registra si el episodio ocurrió y con cuánta anticipación. Claude confirma los literales de `outcome` en el código antes de escribirlos; si hay más valores, los añade y lo anota en la bitácora.

## 11 — `11_mapa_pantallas.drawio`

Mapa de navegación. Nodos con la ruta real. Aristas solo si el menú o el aterrizaje del rol llevan ahí. Permiso junto al nodo, no el rol suelto, porque el menú se arma por permiso.

Incluir al menos: `/ingresar`, `/`, `/avisos`, `/avisos/{id}`, `/historial`, `/confiabilidad`, `/resumen`, `/informes`, `/datos/cargar`, `/datos/calidad`, `/ajustes/limites`, `/laboratorio`, `/laboratorio/comparar`, `/laboratorio/entrenar`, `/contactos`, `/equipo`, `/roles`, `/bitacora`, `/mi-cuenta`, `/pantallas`, `/sala`, `/ayuda`.

Aterrizaje: gerencia pura → `/resumen`; analista puro → vista de ingeniero; auditor puro → `/bitacora`; los demás → `/`.

## Pasos

1. Leer las fuentes y anotar cualquier literal de estado que el §10 no liste.
2. Generar los once `.drawio`.
3. Abrir cada XML y comprobar que tiene `mxfile`, un título y las relaciones de este plan. No hace falta un navegador si el XML está bien formado; si hay forma de validar con diagrams.net, hacerlo.
4. Escribir la bitácora.

## Definición de terminado

- Existen `docs/diseno/drawio/01_contexto_c4.drawio` a `11_mapa_pantallas.drawio`, con los nombres de la sección de cada diagrama.
- Ningún diagrama muestra microservicios, un modelo de lenguaje decidiendo avisos, ni la nube del Plan 09 como si ya estuviera construida.
- La bitácora marca cada punto de esta definición.
