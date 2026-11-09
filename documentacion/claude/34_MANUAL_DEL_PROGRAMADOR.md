# 34 — Manual del programador

**Ejecutor:** Claude.  
**Contrato:** [`27_PAQUETE_DISENO_INDICE.md`](27_PAQUETE_DISENO_INDICE.md).  
**Salida:** `docs/programador/00` a `09`, en Markdown, más `docs/programador/README.md` con el índice.  
**Bitácora:** `docs/diseno/bitacora/34.md`.

Este manual permite que otra persona mantenga Vigía sin leerse el historial de chats. No repite el manual de usuario, no copia el diccionario entero (apunta al Excel del Plan 30) y no pega secretos. Los ejemplos de entorno salen de [`.env.example`](../../.env.example), con los valores de marcador, nunca de `.env`.

## Fuentes obligatorias

- [`CONTEXTO_SISTEMA.md`](../../planes/CONTEXTO_SISTEMA.md) §3, §4, §11 y §12.
- [`README.md`](../../README.md) del repositorio, para no contradecir el arranque que el proyecto ya publica. Si el README está desactualizado respecto del código, el manual describe el código y la bitácora lo dice.
- `app/main.py`, `app/core/config.py`, `docker-compose.yml`, `alembic.ini`.
- Un módulo completo como patrón: `app/modules/alerts/` (`models`, `schemas`, `service`, `router`).
- `app/modules/ingestion/pipeline/` (`e1_extract.py` a `e6_grid.py`, `run.py`).
- `ml_core/forecasting/` el contrato del adaptador y un adaptador corto (persistencia).
- `app/modules/assistant/tools/registry.py` y `grounding.py`.
- `scripts/verify.py` en su ayuda de línea de comandos (`--help`), sin inventar etapas.
- `.env.example`.

## Registro

Español técnico, impersonal, de igual a igual con quien va a modificar el sistema. Se permiten las siglas ya definidas (ETL, JWT, CSRF, MASE, ORM). Cada capítulo abre con el propósito en cuatro líneas y cierra con «dónde mirar si falla». Los comandos van en bloque, copiables, con el directorio de trabajo supuesto: la raíz del repositorio. No se documenta un comando que no exista en `scripts/` o en el README.

## Capítulos

### `README.md`

Índice con una frase por capítulo y el orden de lectura recomendado: 00, 01, 08, y después el capítulo del área que se vaya a tocar. Tabla de los documentos hermanos: Plan 30 (diccionario), Plan 31 (diseño del pronóstico), Plan 32 (resultados), `docs/manual/` (quien opera la mina).

### `00_arranque.md`

Qué es el proceso: una aplicación FastAPI que sirve HTML y API, con PostgreSQL y, en Compose, MLflow. Versión de Python 3.11 o superior. Orden de arranque local que el README y el contexto sostengan: base, migraciones Alembic (nunca `create_all`), semilla de roles, superadmin, carga del consolidado, `uvicorn`. Puertos: aplicación 8000, Postgres publicado en 5433, MLflow 5000. Aviso literal: el contenedor de la aplicación no monta `data/`; la carga del CSV se hace en el host.

Incluir la lista de variables de `.env.example` agrupadas (base, JWT, ETL, notificaciones, asistente, superadmin), con el significado en una frase y sin valores reales. Dejar escrito que `GEMINI_API_KEY` solo vive en el servidor y que, sin autorización de la empresa, no se envían datos de la mina a un proveedor externo.

### `01_mapa_del_codigo.md`

Árbol real de `app/`, `ml_core/`, `migrations/`, `scripts/`, `tests/`, `docs/`. Convención de módulo: `models.py`, `schemas.py`, `repository.py` si existe, `service.py`, `router.py`. Tabla del contexto con el estado real de cada módulo (cuáles no tienen repository). Dependencias entre módulos: la cadena ingesta → entrenamiento → pronóstico → avisos → contactos; tablero y reportes consumen; auditoría es transversal; el asistente llama servicios ajenos y no escribe SQL.

Regla de lenguaje de interfaz: los textos visibles salen de `app/shared/copy.py`. Quien añada una plantilla operativa no escribe la frase en el HTML.

### `02_datos_y_migraciones.md`

Cómo se añade una columna: revisión de Alembic con `downgrade` probado, modelo SQLAlchemy, esquema Pydantic si cruza HTTP. Cabeza actual: leerla de la carpeta de migraciones el día de la escritura y ponerla en el capítulo. Apuntar al diccionario del Plan 30 en lugar de pegarlo. Explicar tres invariantes con el archivo donde viven: único de lectura por sensor y tiempo; check de no sintético; umbral vigente por fecha. Decir cómo se reconstruyen episodios si el repositorio tiene `scripts/rebuild_events.py`; si el script tiene otro nombre, usar el real.

### `03_etl.md`

Carril E1 a E6 con el archivo de cada etapa y el contrato `StageResult`. Qué es puro (E1–E4) y qué toca la base (E5–E6), según `run.py`. Disparadores: `POST` de carga, bandeja, `scripts/load_processed_dataset.py --consolidado`. Idempotencia. Qué archivos de `data/raw` no tienen parser. Después del éxito, el ciclo de pronóstico; un fallo de modelo no revierte la carga. Dónde se leen las incidencias (`data_quality_issues` y `docs/etl/transformaciones.md`).

### `04_pronostico.md`

Contrato `Forecaster`: ajustar y devolver cuantiles. Dónde vive cada adaptador. Qué pasa si la librería no está: error de no disponible, no una métrica ficticia. Horizontes 6, 12 y 18. Separación entre cuantiles, calibración, decisión y regla dura del aviso confirmado. Dónde se persiste (`forecasts`, `forecast_quantiles`, `forecast_explanations`). Promoción explícita y permisos `models.train` y `models.promote`. Cómo se lanza el benchmark con el comando que exista (`python -m ml_core.experiments.run_benchmark` u otro que el código exponga; verificar). Recordar que `legacy/` no se extiende.

Sección «añadir un adaptador», en pasos: implementar el contrato, registrarlo en el zoo, declarar la familia, cubrir el caso de librería ausente, entrar en la misma evaluación que el resto. No incluir hiperparámetros inventados.

### `05_acceso.md`

JWT de acceso 15 minutos, refresco opaco 8 horas con rotación, CSRF de doble envío, bloqueo a los 5 fallos. Cookies HttpOnly. El menú se arma por permiso; el aterrizaje sí mira el rol. Lista de permisos canónicos leída del seed, no memorizada. Alcance por sitio y por instrumento: qué significa una tabla de alcance vacía. Kiosco: token hasheado, revocable. Dónde se escribe la bitácora.

### `06_asistente.md`

Flujo de un turno: validar cuerpo, prompt sin datos, herramienta, evidencia, verificación de cifras, respuesta. Una herramienta por archivo, registrada en `registry.py`, con permiso y esquema. No se añade SQL dentro de la herramienta: se llama al servicio dueño. Límite de rondas. Proveedores: Gemini y la alternativa local, más el proveedor falso de pruebas. Degradación sin clave. Indexación BM25 del manual, sin embeddings. Tablas `assistant_turns` y `assistant_feedback`. Cómo añadir una herramienta, en pasos comprobables.

Advertencia de gobernanza, copiada en sustancia del informe de evaluación: no apuntar el proveedor externo a datos de la mina sin la autorización escrita.

### `07_pruebas.md`

Cómo se corre `scripts/verify.py`, qué significa `--plan`, y que la base de prueba es `proyecto_gases_test`, distinta de la de desarrollo. Dónde viven pruebas unitarias, de integración y de extremo a extremo (Playwright). Qué no hacer: desactivar una prueba, bajar cobertura o marcar `skip` para ver el verde. Si se documenta un subcomando, tiene que salir del `--help` real.

### `08_configuracion.md`

Tabla completa derivada de `.env.example` y de los campos de `app/core/config.py` que no estén en el ejemplo: nombre, obligatorio o no, efecto si falta, valor de ejemplo no secreto. Grupos: datos, sesión, bandeja ETL, ciclo de pronóstico, notificaciones, informes, asistente. `NOTIFICATIONS_DRY_RUN` y `ETL_INBOX_ENABLED` con el comportamiento por defecto del ejemplo.

### `09_como_extender.md`

Tres recetas cortas, cada una con los archivos que hay que tocar y la prueba que debe seguir en verde:

1. Un gas nuevo en el catálogo: `gas_types`, umbral, alias en el normalizador, etiqueta visible en `copy.py`, sin romper los códigos ya canónicos.
2. Un adaptador de pronóstico: la receta del capítulo 04, resumida y con el enlace al capítulo.
3. Una herramienta del asistente: permiso existente o nuevo en el seed, esquema Pydantic, función que llama a un servicio, frase de manual si la persona usuaria debe descubrirla, caso en el evaluador si `app/modules/assistant/eval.py` es el lugar de esos casos.

Cierra con lo que no se extiende: clonado de meses, etiqueta `evento_final`, tabla `predictions`, CDN en las plantillas, texto operativo escrito directo en el HTML.

## Definición de terminado

- Existen los diez archivos de capítulo más el `README.md`, y cada comando citado se encontró en el repositorio.
- No hay claves, correos reales ni contraseñas de `.env`.
- El capítulo 04 no presenta `legacy/` como el lugar donde se añade un modelo.
- El capítulo 06 dice que la herramienta no contiene SQL propio.
- La bitácora lista los comandos del README que ya no existen, si apareció alguno.
