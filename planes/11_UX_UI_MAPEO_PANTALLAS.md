# Plan 11 — Mapeo UI/UX (pantallas, navegación y flujos por rol)

> Complementa el Plan 07 (sistema de diseño). Aquí se define **qué pantallas existen, qué contiene cada una y cómo se navega entre ellas**, para que la implementación en Jinja2/Bootstrap5 tenga un mapa exacto que seguir.
>
> **Plan 12 (Model Zoo):** las pantallas P7–P9 se rediseñan con matriz de métricas thesis (gates pass/fail), selector multi-algoritmo (tabulares vs deep learning), comparación descargable y detalle con umbrales. Nueva ruta opcional `/ml/compare`.

## 1. Roles y su objetivo principal en la UI

| Rol | Objetivo principal al entrar | Pantalla de aterrizaje |
|---|---|---|
| `admin` | Administrar usuarios/roles y supervisar todo el sistema | Dashboard administrativo |
| `ingeniero_datos` | Monitorear ETL, entrenar/comparar/promover modelos | Panel de datos y modelos |
| `operador_mina` | Ver estado en vivo y reaccionar a alertas | Semáforo operativo |
| `interesado` | Ver resumen ejecutivo y descargar reportes | Resumen ejecutivo |
| `auditor` | Revisar histórico y trazabilidad, sin poder de acción | Vista de auditoría (solo lectura) |

## 2. Inventario de pantallas

| # | Pantalla | Ruta | Roles con acceso |
|---|---|---|---|
| P1 | Login | `/login` | Público |
| P2 | Semáforo operativo (tiempo real) | `/` (operador) | operador, admin |
| P3 | Detalle de sitio/sensor | `/sites/{id}` | operador, ingeniero, admin |
| P4 | Bandeja de alertas | `/alerts` | operador, ingeniero, admin, auditor (lectura) |
| P5 | Detalle de alerta | `/alerts/{id}` | operador, ingeniero, admin, auditor |
| P6 | Panel de ETL / ingesta | `/ingestion` | ingeniero, admin |
| P7 | Catálogo y comparación de modelos | `/ml/models` | ingeniero, admin |
| P8 | Detalle de modelo / entrenamiento | `/ml/models/{id}` | ingeniero, admin |
| P9 | Nuevo entrenamiento (formulario) | `/ml/train` | ingeniero, admin |
| P10 | Resumen ejecutivo | `/executive` | interesado, admin |
| P11 | Reportes (generar/descargar) | `/reports` | interesado, ingeniero, admin |
| P12 | Partes interesadas (CRUD) | `/stakeholders` | admin |
| P13 | Usuarios y roles (CRUD) | `/users`, `/roles` | admin |
| P14 | Auditoría (histórico de acciones) | `/audit` | admin, auditor |
| P15 | Perfil / cerrar sesión | `/profile` | todos |

## 3. Navegación (sidebar dinámico)

El sidebar se arma según permisos (`/auth/me`), no según rol hardcodeado — así, si un rol nuevo hereda permisos parciales, la UI se ajusta sola.

```
[Logo]
├── Inicio                       (siempre, según rol → P2/P7/P10)
├── Sitios y sensores            (permiso: sensors.manage o predictions.view)  → P3
├── Alertas                      (permiso: alerts.view)                       → P4
├── Ingesta / ETL                (permiso: sensors.manage)                    → P6
├── Modelos                      (permiso: models.train)                      → P7
├── Reportes                     (permiso: reports.export)                    → P11
├── Partes interesadas           (permiso: stakeholders.manage)               → P12
├── Administración
│   ├── Usuarios                 (permiso: users.manage)                      → P13
│   └── Roles y permisos         (permiso: roles.manage)                      → P13
├── Auditoría                    (permiso: audit.view)                        → P14
└── [Avatar usuario] → Perfil / Cerrar sesión                                 → P15
```

## 4. Wireframe descriptivo por pantalla

### P1 — Login
- Centrado, tarjeta blanca con sombra suave, logo arriba.
- Campos: email, password, botón "Iniciar sesión" (verde, `--bs-primary`).
- Enlace "¿Olvidaste tu contraseña?" (puede quedar deshabilitado/fase futura).
- Estado de error: alerta roja bajo el formulario ("Credenciales inválidas").

### P2 — Semáforo operativo (home de operador)
- Barra superior: selector de sitio (si hay más de uno) + hora de última actualización.
- Grid de tarjetas por sensor: nombre, gas, última lectura, badge de color según `risk_level` (`_risk_badge.html`).
- Panel lateral derecho (o sección inferior en móvil): "Alertas activas" (top 5, con enlace a P4).
- Actualización automática cada 5–10s (polling, Plan 07 paso 5).
- **Estado vacío:** si no hay sensores configurados, mensaje "Aún no hay sensores registrados" + botón (solo admin/ingeniero) para ir a configuración.

### P3 — Detalle de sitio/sensor
- Encabezado: nombre del sensor, sitio, gas, unidad.
- Gráfico de serie de tiempo (`Leyendo` vs. umbral STEL/TWA) — Chart.js, rango seleccionable (24h/7d/30d).
- Tabla de últimas lecturas (paginada).
- Sección "Predicciones recientes" con `risk_level` y probabilidad.

### P4 — Bandeja de alertas
- Filtros arriba: estado (abierta/reconocida/resuelta), nivel, sitio, rango de fechas.
- Tabla: nivel (badge de color), sitio/sensor, mensaje, recomendación (truncada), estado, fecha, acción rápida (reconocer/resolver si el usuario tiene permiso).
- Paginación server-side.
- **Estado vacío:** "No hay alertas con estos filtros" (evitar mensaje alarmante tipo "todo está mal" cuando en realidad no hay resultados).

### P5 — Detalle de alerta
- Cabecera con badge de nivel grande.
- Datos de la lectura y predicción asociada (probabilidad, modelo usado).
- Recomendación completa.
- Historial de estado (creada → reconocida por X → resuelta por Y, con timestamps) — línea de tiempo vertical simple.
- Sección "Notificaciones enviadas" (a qué stakeholders, canal, estado de envío).
- Botones de acción según permiso: "Reconocer", "Resolver" (con campo de nota).

### P6 — Panel de ETL / ingesta
- Botón "Subir archivo(s)" (drag & drop + selector).
- Tabla de corridas (`etl_runs`): fecha, estado, filas ingeridas/rechazadas, duración.
- Al hacer clic en una corrida: modal o vista de detalle con el log de transformaciones (texto estructurado, no JSON crudo).
- **Estado de carga:** barra de progreso mientras se procesa el archivo subido.

### P7 — Catálogo y comparación de modelos
- Tabla de modelos: nombre, versión, algoritmo, F1, recall, precisión, estado (`staging`/`production`/`archived`), fecha de entrenamiento.
- Resaltar visualmente (borde o fondo verde claro) el modelo `production` activo.
- Botón "Entrenar nuevo modelo" → P9.
- Gráfico de barras comparando F1/recall entre los últimos N modelos.

### P8 — Detalle de modelo
- Métricas completas, parámetros usados, enlace a la corrida en MLflow.
- Botón "Promover a producción" (con confirmación, ya que archiva el modelo anterior).

### P9 — Nuevo entrenamiento
- Formulario simple: selección de dataset/rango de fechas, algoritmo(s) a entrenar, parámetros opcionales avanzados (colapsados por defecto).
- Al enviar: redirige a P7/P8 mostrando el job en estado "en progreso" (con polling de estado).

### P10 — Resumen ejecutivo (interesados)
- Tarjetas KPI: alertas totales del periodo por nivel, tiempo promedio de resolución, sitio con más incidencias.
- Gráfico de tendencia de alertas en el tiempo.
- Botón "Descargar reporte ejecutivo" → dispara P11.
- Sin acceso a detalles técnicos de modelos ni a acciones de resolución.

### P11 — Reportes
- Formulario por tipo de reporte (alertas por periodo, desempeño de modelo, ejecutivo) con sus parámetros.
- Tabla de reportes generados previamente con enlace de descarga.

### P12 — Partes interesadas
- Tabla de stakeholders (nombre, tipo, organización, canal).
- Formulario de alta/edición + gestión de suscripciones (sitio/sensor/nivel mínimo) en la misma vista o modal.

### P13 — Usuarios y roles
- Tabla de usuarios (nombre, email, roles, estado activo/inactivo).
- Modal de asignación de roles.
- Vista separada "Roles y permisos": matriz roles × permisos (checkboxes), solo editable por `admin`.

### P14 — Auditoría
- Tabla de solo lectura: usuario, acción, entidad, fecha, detalle (expandible).
- Filtros por usuario, tipo de acción, rango de fechas.

### P15 — Perfil
- Datos básicos del usuario, cambio de contraseña, botón "Cerrar sesión".

## 5. Flujos de usuario clave (user journeys)

**Flujo A — Operador reconoce y resuelve una alerta**
1. Entra a P2, ve tarjeta en rojo (CRÍTICO).
2. Clic en la alerta → P5.
3. Lee recomendación, clic "Reconocer" → estado cambia, se registra en auditoría.
4. Atiende la situación físicamente, vuelve a P5, clic "Resolver" con nota → estado `resuelta`.
5. La tarjeta en P2 vuelve a verde en el siguiente ciclo de polling.

**Flujo B — Ingeniero entrena y promueve un modelo**
1. Entra a P7, revisa métricas actuales.
2. Clic "Entrenar nuevo modelo" → P9, configura y envía.
3. Ve el job "en progreso", espera o navega a otra vista y vuelve.
4. Job termina → nuevo modelo aparece en P7 en `staging`.
5. Compara métricas contra el `production` actual → si es mejor, entra a P8 y "Promueve a producción".

**Flujo C — Interesado revisa impacto y descarga reporte**
1. Entra a P10, revisa KPIs del periodo.
2. Ajusta rango de fechas.
3. Clic "Descargar reporte ejecutivo" → se genera y descarga (P11 en background).

**Flujo D — Admin da de alta a un nuevo operador**
1. Entra a P13, "Nuevo usuario".
2. Completa datos, asigna rol `operador_mina`.
3. El nuevo usuario recibe sus credenciales (fuera de alcance de este plan: proceso de entrega segura de password inicial — definir si es manual o por correo).
4. El usuario hace login (P1) y aterriza en P2 con el menú ya filtrado a sus permisos.

## 6. Estados transversales a definir en cada pantalla con datos
- **Cargando:** skeleton o spinner (no dejar la pantalla en blanco).
- **Vacío:** mensaje específico al contexto (no un genérico "no hay datos").
- **Error:** mensaje claro + acción de reintento cuando aplique (no solo "Error 500").
- **Sin permiso:** si se llega a una ruta sin el permiso (enlace directo), mostrar una página 403 propia, no un stacktrace.

## 7. Responsive / breakpoints
- Sidebar colapsa a menú hamburguesa por debajo de `768px` (breakpoint `md` de Bootstrap5).
- Tablas con scroll horizontal en móvil en lugar de romper el layout.
- Tarjetas del semáforo (P2) pasan de grid de 4 columnas (desktop) a 1 columna (móvil).

## Checklist de validación (Definition of Done)
- [ ] Las 15 pantallas existen y respetan el acceso por permiso definido en la tabla del punto 2.
- [ ] El sidebar se genera dinámicamente según permisos, no según un `if rol == "x"` hardcodeado.
- [ ] Los 4 flujos de usuario (A–D) se pueden completar de principio a fin sin fricción ni pasos faltantes.
- [ ] Cada pantalla con datos maneja explícitamente sus estados de carga/vacío/error.
- [ ] La navegación es usable en móvil (sidebar colapsable, tablas con scroll).

**Este plan se implementa en paralelo/dentro del Plan 07 (Dashboard y UI)**, como su guía de contenido pantalla por pantalla.
