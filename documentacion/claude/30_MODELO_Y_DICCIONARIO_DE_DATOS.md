# 30 — Modelo entidad-relación y diccionario de datos

**Ejecutor:** Claude.  
**Contrato:** [`27_PAQUETE_DISENO_INDICE.md`](27_PAQUETE_DISENO_INDICE.md).  
**Salidas:**

- `docs/diseno/drawio/13_er_logico.drawio`
- `docs/diseno/excel/diccionario_datos.xlsx`

**Bitácora:** `docs/diseno/bitacora/30.md`.

El diagrama resume. El diccionario es la autoridad de campos y sale de los `models.py` y de Alembic, no de la memoria de este plan. Si este plan nombra una tabla que el código ya no tiene, no se dibuja y se anota. Si el código tiene una tabla que este plan omite, se agrega y se anota.

## Fuentes obligatorias

Leer antes de escribir una fila del diccionario:

- `app/modules/users/models.py`
- `app/modules/roles_permissions/models.py`
- `app/modules/catalog/models.py`
- `app/modules/sensors_ingestion/models.py`
- `app/modules/ml_training/models.py`
- `app/modules/forecasting/models.py`
- `app/modules/alerts/models.py`
- `app/modules/stakeholders/models.py`
- `app/modules/reports/models.py`
- `app/modules/audit/models.py`
- `app/modules/assistant/models.py`
- `ml_core/columns.py` para el mapeo de las quince columnas del archivo.
- [`docs/etl/transformaciones.md`](../../docs/etl/transformaciones.md) para el significado de E1–E6.
- La cabeza Alembic vigente, citada en [`CONTEXTO_SISTEMA.md`](../../planes/CONTEXTO_SISTEMA.md), para la hoja de control. Si la cabeza del archivo de contexto y la de `migrations/versions/` no coinciden, gana la carpeta de migraciones.

## Diagrama

Notación: entidad-relación con pata de gallo. Una página A3, agrupada en seis regiones con título, no en seis archivos:

1. Acceso. `users`, `user_roles`, `roles`, `role_permissions`, `permissions`, `user_site_scopes`, `user_instrument_scopes`, `refresh_tokens`, `password_reset_tokens`, `user_invitations`, `kiosk_devices`.
2. Catálogo. `gas_types`, `normative_thresholds`, `app_settings`.
3. Campo. `sites`, `instruments`, `sensors`, `gas_readings`, `etl_runs`, `etl_run_steps`, `data_quality_issues`, `reading_grid`, `threshold_events`.
4. Modelos. `model_registry`, `model_evaluations`, `training_jobs`, `benchmark_runs`, `backtest_forecasts`.
5. Pronóstico y avisos. `forecasts`, `forecast_quantiles`, `forecast_explanations`, `alerts`, `alert_outcomes`, `alert_notifications`, `stakeholders`, `stakeholder_user`, `stakeholder_subscriptions`.
6. Salidas. `reports`, `audit_log`, `assistant_turns`, `assistant_feedback`.

Reglas del dibujo:

- La tabla `predictions` no aparece. El pronóstico vive en `forecasts` y `forecast_quantiles`.
- Cardinalidades que el contexto ya fija y el código debe confirmar: usuario a rol, muchos a muchos; rol a permiso, muchos a muchos; sitio a sensor, uno a muchos; sensor a lectura, uno a muchos; lectura a corrida ETL, muchos a uno; pronóstico a cuantiles, uno a muchos; pronóstico a aviso, uno a muchos opcionales; aviso a resultado, uno a uno opcional; aviso a notificaciones, uno a muchos.
- `user_site_scopes` sin filas significa, para el rol que lo permite, todos los sitios. Esa regla va como nota, porque no es una cardinalidad.
- `gas_readings.is_synthetic` lleva la nota de la restricción que solo admite falso.

No hace falta dibujar cada columna en el ER. El detalle vive en el Excel. En el ER, cada entidad muestra la clave primaria y dos o tres atributos que identifican el negocio (por ejemplo, en `forecasts`: sensor, modelo, `issued_at`, nivel).

## Excel

Hojas, en este orden.

**Portada.** Sistema, documento «Diccionario de datos», versión 1.0, cabeza Alembic leída, fecha, lista de archivos `models.py` consultados.

**Control.** Una fila por dominio del diagrama, con el número de tablas encontradas en código.

**catalogo_tablas.** Una fila por tabla: nombre físico, dominio, propósito en una frase, módulo dueño, volumen esperado en una palabra (catálogo, transaccional, bitácora). El propósito sale del significado de negocio, no de repetir el nombre.

**diccionario.** Una fila por columna. Columnas del libro, fijas:

- tabla
- campo
- tipo PostgreSQL (traducido desde SQLAlchemy: Integer, String(n), Text, Boolean, DateTime with time zone, Numeric, JSONB)
- nulo (sí o no)
- clave (PK, FK, UK, o vacío)
- referencia (tabla.campo si es FK, con la acción `ondelete` si el modelo la declara)
- dominio o valores (enumeración real; si es libre, «texto libre» o el ejemplo del negocio)
- descripción (qué significa para la mina o para el experimento, una frase)
- fuente (ruta del `models.py` y nombre de la clase)

Descripciones que no se pueden dejar genéricas, porque son el corazón de la tesis:

- `gas_readings.value_canonical` y `unit_canonical`: valor después de E3, en la unidad del catálogo.
- `gas_readings.quality_status`: resultado de E4.
- `reading_grid.is_imputed` e `is_missing`: hueco corto rellenado frente a hueco largo.
- `threshold_events`: verdad de referencia de un episodio, del cruce al regreso.
- `forecasts.issued_at`: último instante de rejilla usado. No es el instante futuro pronosticado.
- `forecast_quantiles`: q10, q50, q90, q95 por horizonte en minutos.
- `alerts.kind`: anticipado o confirmado. `alerts.origin`: en vivo o histórico. `alerts.status`: abierta, reconocida, resuelta.
- `alert_outcomes.lead_minutes`: anticipación medida, no una constante.
- `normative_thresholds.verified`: falso mientras el artículo no esté cotejado.
- `model_registry.status`: staging, production o archived. Confirmar literales en código.
- `model_evaluations.is_final_test`: verdadero solo en el bloque reservado.
- `assistant_turns`: turno del asistente, con la evidencia que usó la verificación de cifras. Describir los campos que el modelo declare, sin suponer columnas que no estén.

**enumeraciones.** Una fila por valor permitido que el código compare con una cadena: niveles de aviso, estados, kinds, orígenes, outcomes, familias de modelo, etapas E1–E6, `quality_status`. Columna «dónde se asigna» con archivo y función.

**rol_permiso.** Filas del seed vigente (`scripts/seed_roles_permissions.py`). Columnas: rol visible, código de rol, código de permiso, ¿lo tiene? Claude lee el script. No copie una matriz recordada si el script difiere; anote la diferencia.

**mapeo_archivo.** Quince columnas de `ml_core/columns.py` hacia tabla y campo, o «no se persiste» con el motivo (descripción, número de periodo, factores). Incluir la transformación E3 cuando cambie la unidad.

**restricciones.** Únicos, checks y reglas que no caben en una celda de nulo: único de lectura por sensor y tiempo; check de sintético; único de umbral por gas, nivel y vigencia; único de pronóstico por sensor, modelo e instante de emisión. Cada una con el archivo donde se declara.

## Criterio de una buena descripción

La descripción dice el papel del dato en la decisión o en la evidencia. «Identificador» a secas solo es aceptable en una clave subrogada, y aun así se dice de qué cosa es identidad. No se copia el comentario vacío de un ORM si el campo no tiene comentario: se redacta a partir del uso en el `service.py` dueño. Si el uso no se encuentra, la descripción es «no consta el significado de negocio en el código revisado» y entra a la bitácora.

## Definición de terminado

- El `.drawio` abre en diagrams.net, muestra las seis regiones y no incluye `predictions`.
- Toda clase con `__tablename__` en los `models.py` listados tiene filas en `diccionario`.
- `mapeo_archivo` cubre las quince columnas canónicas.
- La hoja Control cita la cabeza Alembic leída del repositorio.
- La bitácora lista tablas añadidas o retiradas respecto de la lista de este plan.
