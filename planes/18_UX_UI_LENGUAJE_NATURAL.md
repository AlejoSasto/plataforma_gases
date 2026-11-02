# 18 — Rediseño UX/UI completo en lenguaje natural

**Objetivo de tesis:** OE4.
**Prerrequisitos:** Plan 16 (tablas), Plan 17 (pronósticos y explicaciones), Plan 19 (roles).
**Entrega:** nuevo sistema visual (colores, tipografía, gráficos, iconos), todas las pantallas rediseñadas, lenguaje no técnico en las vistas operativas, modo sala de control y verificación automática de lenguaje y accesibilidad.

---

## 1. Principios

1. **Responder tres preguntas en 3 segundos:** ¿estamos bien ahora? ¿qué viene en los próximos minutos? ¿qué tengo que hacer?
2. **Lenguaje de la operación, no de la IA.** Se habla de gases, zonas, minutos y acciones. Nunca de modelos, probabilidades ni métricas (salvo en el Laboratorio).
3. **Minimalismo funcional.** Un acento de color, mucho blanco, jerarquía tipográfica clara. El color se reserva para el **estado**.
4. **Nunca solo color.** Cada estado lleva color, ícono y palabra (accesibilidad y daltonismo).
5. **Consistencia.** Componentes reutilizables y un único archivo de tokens.

---

## 2. Stack de interfaz

| Antes | Después | Motivo |
|-------|---------|--------|
| Bootstrap 5 (componentes) | CSS propio por tokens (`app/static/css/`): `tokens.css`, `base.css`, `components.css`, `layout.css`. Bootstrap solo como *reboot* y rejilla durante la migración; se retira al final | Identidad propia y minimalista |
| Inter | **IBM Plex Sans** (interfaz) + **IBM Plex Mono** (cifras) desde Google Fonts | Tono industrial y sobrio; cifras alineadas |
| Chart.js | **Apache ECharts 5** (cdnjs) | Bandas de pronóstico, líneas de umbral, marcador de “ahora”, zoom temporal |
| Sin íconos | **Lucide** (SVG, unpkg/cdnjs) | Íconos lineales consistentes |
| `fetch` manual + polling | **htmx** (cdnjs) para refrescos parciales + `app.js` mínimo | Menos JS propio; actualización por fragmentos |

---

## 3. Tokens de diseño

### 3.1 Color — modo claro (oficinas, gerencia)

| Token | Valor | Uso |
|-------|-------|-----|
| `--bg` | `#F6F6F4` | Fondo general (blanco cálido) |
| `--surface` | `#FFFFFF` | Tarjetas y paneles |
| `--surface-2` | `#F0F1F2` | Zonas secundarias, encabezados de tabla |
| `--border` | `#E3E5E8` | Bordes de 1 px |
| `--text` | `#14181F` | Texto principal |
| `--text-2` | `#5A6472` | Texto secundario |
| `--text-3` | `#8A93A0` | Ayudas y marcas de tiempo |
| `--accent` | `#1E3A5F` | Acción principal (azul pizarra profundo) |
| `--accent-hover` | `#162C49` | |
| `--accent-soft` | `#E8EEF6` | Fondos de selección |
| `--focus` | `#3B82F6` | Anillo de foco |

### 3.2 Color — modo sala de control (oscuro)

| Token | Valor |
|-------|-------|
| `--bg` | `#0E1116` |
| `--surface` | `#161A21` |
| `--surface-2` | `#1D222B` |
| `--border` | `#2A303B` |
| `--text` | `#E8EAED` |
| `--text-2` | `#A7B0BC` |
| `--accent` | `#8FB3E8` |

### 3.3 Estados operativos (la única fuente de color fuerte)

| Estado | Palabra en la UI | Ícono Lucide | Sólido | Fondo suave | Texto sobre suave |
|--------|------------------|--------------|--------|-------------|-------------------|
| normal | **Normal** | `circle-check` | `#1F8A5B` | `#E7F4EE` | `#14603F` |
| vigilar | **Vigilar** | `eye` | `#C98A04` | `#FCF2DA` | `#7A5300` |
| actuar | **Actuar ya** | `triangle-alert` | `#D9601A` | `#FCE9DD` | `#9A3D0C` |
| evacuar | **Evacuar** | `siren` | `#C4262E` | `#FAE4E5` | `#9B1C22` |
| sin_datos | **Sin datos** | `circle-dashed` | `#8A93A0` | `#EEF0F2` | `#4B5563` |

Todas las combinaciones de texto deben cumplir un contraste ≥ 4,5:1 (WCAG 2.2 AA); se verifica con una prueba automática (Plan 20).

### 3.4 Tipografía

| Rol | Fuente | Tamaño / interlineado / peso |
|-----|--------|------------------------------|
| Display (estado general) | Plex Sans | 32 / 40 / 600 |
| Título de página | Plex Sans | 24 / 32 / 600 |
| Título de sección | Plex Sans | 18 / 26 / 600 |
| Cuerpo | Plex Sans | 15 / 24 / 400 |
| Pequeño | Plex Sans | 13 / 20 / 400 |
| Cifra grande | Plex Mono | 36 / 40 / 500, `font-variant-numeric: tabular-nums` |
| Cifra en tabla | Plex Mono | 14 / 20 / 400 |

En modo sala de control, toda la escala se multiplica por 1,35.

### 3.5 Espaciado, forma y movimiento

- Espaciado en base 4: 4, 8, 12, 16, 24, 32, 48, 64.
- Radio: 8 px en controles y 12 px en tarjetas. Sombra: solo en elementos flotantes (`0 8px 24px rgba(20,24,31,.08)`). Las tarjetas usan borde, no sombra.
- Movimiento: 150 ms *ease-out*. Respeta `prefers-reduced-motion`. **Sin animaciones parpadeantes**, salvo un pulso suave en el estado “Evacuar”.

---

## 4. Gráficos (convenciones ECharts)

Módulo `app/static/js/charts.js` con una única función por tipo; nadie configura ECharts a mano en los templates.

| Gráfico | Convención |
|---------|------------|
| **“Ahora y lo que viene”** (principal) | Línea sólida = medido (últimos 60 min). Línea punteada = valor esperado. **Banda suave** = rango probable (q10–q90). Línea vertical “Ahora”. Líneas horizontales de umbral con la etiqueta directa (“Actuar ya · 1,0 %”). Sin leyenda: etiquetas sobre la propia línea. |
| Historial | Línea medida + bandas de color tenues en los periodos con aviso. Zoom por arrastre. |
| Confiabilidad (gerencia) | Barras horizontales simples con número grande al lado. Sin ejes innecesarios. |
| Laboratorio | Comparativas técnicas (solo en el Laboratorio). |

Reglas: rejilla mínima (solo eje Y punteado), máximo 2 colores de serie más los estados, tooltips con la frase completa (“A las 10:42 se esperan 0,8 % de metano; rango probable 0,6–1,0 %”), formato numérico **es-CO** (coma decimal) y hora local de Bogotá en formato de 24 h.

---

## 5. Diccionario de lenguaje natural

`app/shared/copy.py` centraliza **todos** los textos. Los templates no escriben textos técnicos sueltos.

| Concepto técnico | Lo que ve la operación |
|------------------|------------------------|
| Predicción / pronóstico | **Lo que viene** · “En los próximos 10 minutos” |
| Valor esperado (q50) | “Se espera alrededor de **0,8 %**” |
| Intervalo q10–q90 | “Podría estar **entre 0,6 % y 1,0 %**” |
| Probabilidad de superar el umbral | “**Alta / Media / Baja** posibilidad de llegar a *Actuar ya*” (alta ≥ π, media ≥ π/2) |
| Confianza (ancho del intervalo) | “Estimación **muy confiable / confiable / poco confiable** por ahora” |
| Aviso anticipado | “**Aviso anticipado:** el sistema espera que el metano llegue al límite en unos **7 minutos**” |
| Aviso confirmado | “**El sensor ya marca** un nivel por encima del límite” |
| Explicación (factores) | “**Por qué avisamos:** el metano viene subiendo de forma sostenida en los últimos 20 minutos y el monóxido en la misma zona también aumentó” |
| Recomendación | “**Qué hacer:** verificar la ventilación del frente 3 y preparar la salida del personal” |
| Recall / precisión / lead time | “De cada 10 situaciones peligrosas, el sistema avisó a tiempo **9**” · “Avisa en promedio **7 minutos antes**” · “**1** aviso innecesario por turno” |
| Modelo en producción | No se menciona. En el Laboratorio: “Modelo activo” |
| Sin modelo activo | “Por ahora mostramos solo lo que marcan los sensores” |
| Dato faltante | “Este sensor no ha enviado datos desde hace **15 min**” |
| Sensor / sitio | **Sensor** (con nombre del lugar) / **Zona** |
| ETL / ingesta | “**Cargar datos**” |

**Términos prohibidos en las vistas operativas** (lista en `copy.py::FORBIDDEN_TERMS`, verificada por prueba): `modelo`, `algoritmo`, `predicción`, `probabilidad`, `inferencia`, `cuantil`, `percentil`, `recall`, `precisión`, `F1`, `RMSE`, `MAE`, `MASE`, `dataset`, `entrenamiento`, `staging`, `production`, `threshold`, `lead time`, `ML`, `machine learning`, `IA`, `transformer`, `LSTM`, `TFT`, `ETL`, `JSON`, `API`, `ID`.

**Tono:** frases cortas, en presente, con verbos de acción y sin culpar. Se habla de “nosotros/el sistema”, nunca “el algoritmo”. Las horas van en relativo cuando sirve (“hace 2 min”) con la hora exacta en el tooltip.

**Plantilla de aviso** (`copy.alert_card()`):

```
[Ícono] ACTUAR YA · Metano · Frente 3 – Galería norte
Se espera que llegue al límite en unos 7 minutos.
Ahora: 0,72 %   ·   Esperado: 1,05 %   ·   Límite: 1,0 %
Por qué avisamos: viene subiendo sin pausa desde hace 20 minutos.
Qué hacer: revisar la ventilación y preparar la salida del personal.
[Ya lo vi]   [Ver detalle]
```

---

## 6. Arquitectura de navegación

```
┌─────────────────────────────────────────────────────────┐
│ ▣ Plataforma Gases   Mina XX        🔔 3   Ana · Supervisora ▾ │  ← barra superior 56 px
├──────────┬──────────────────────────────────────────────┤
│ Hoy      │                                              │
│ Avisos   │              contenido                       │
│ Zonas    │                                              │
│ Historial│                                              │
│ Informes │                                              │
│ Confiab. │                                              │
│ ──────── │                                              │
│ Equipo   │  (según permisos)                            │
│ Ajustes  │                                              │
│ Laborat. │  (solo analista/admin, con etiqueta "técnico")│
└──────────┴──────────────────────────────────────────────┘
```

La barra lateral es colapsable (íconos solos a 64 px). En móvil se convierte en una barra inferior de 4 ítems.

---

## 7. Pantallas

| # | Pantalla | Ruta | Quién | Contenido |
|---|----------|------|-------|-----------|
| P1 | **Ingresar** | `/ingresar` | Público | Ver Plan 19 |
| P2 | **Hoy** (inicio) | `/` | Operador, supervisor, admin | Franja de estado general grande (“Todo normal” / “2 zonas requieren atención”). Rejilla de tarjetas por zona y gas: estado **Ahora** y **En 10 min**, mini gráfico. Panel lateral de avisos abiertos. Se refresca solo (htmx, cada paso de rejilla). |
| P3 | **Avisos** | `/avisos` | Con `alerts.view` | Pestañas Abiertos / Vistos / Cerrados. Tarjetas con la plantilla de aviso. Filtros por zona, gas y nivel. |
| P4 | **Detalle del aviso** | `/avisos/{id}` | Ídem | Gráfico “Ahora y lo que viene”, por qué avisamos, qué hacer, línea de tiempo (creado → visto por → cerrado por), botones **Ya lo vi** y **Cerrar aviso** (con nota). |
| P5 | **Zonas y sensores** | `/zonas`, `/zonas/{id}`, `/sensores/{id}` | `predictions.view` | Mapa simple en lista por zona; detalle del sensor con gráfico, estado y último dato. |
| P6 | **Historial** | `/historial` | `predictions.view` | Rango de fechas, gas y zona; gráfico con periodos de aviso; descarga. |
| P7 | **Informes** | `/informes` | `reports.export` | Tarjetas para generar: “Avisos del periodo”, “Resumen para gerencia”, “Confiabilidad del sistema”. Lista de informes generados. |
| P8 | **¿Qué tan confiable es el sistema?** | `/confiabilidad` | Gerencia, supervisor, auditor, admin | Tres cifras grandes en lenguaje natural (situaciones avisadas a tiempo, minutos de anticipación, avisos innecesarios por turno), tendencia mensual, situaciones no avisadas (honestidad) y nota en lenguaje simple sobre los datos usados. |
| P9 | **Resumen para gerencia** | `/resumen` | Gerencia | Semana actual frente a la anterior, zonas con más avisos, tiempo medio de respuesta del personal. |
| P10 | **Equipo** | `/equipo` | `users.manage` | Usuarios, invitaciones, roles y zonas asignadas (Plan 19). |
| P11 | **Contactos de aviso** | `/contactos` | `stakeholders.manage` | Quién recibe qué aviso y por qué canal. |
| P12 | **Ajustes de seguridad** | `/ajustes/limites` | `thresholds.manage` | Límites por gas, con fuente normativa y estado “verificado” o “por verificar”. |
| P13 | **Cargar datos** | `/datos/cargar` | `sensors.manage` | Arrastrar Excel; progreso por etapas en lenguaje natural (“Leyendo archivo… Revisando datos… 3 lecturas con problemas”). |
| P14 | **Calidad de los datos** | `/datos/calidad` | Analista, admin | Cobertura por sensor, huecos y problemas. Muestra la decisión G0. |
| P15 | **Laboratorio** (técnico) | `/laboratorio/*` | `models.train` | Zoo, benchmark, métricas, comparativas, promoción. Aquí sí hay lenguaje técnico, con una etiqueta visible “Área técnica”. |
| P16 | **Bitácora** | `/bitacora` | `audit.view` | Quién hizo qué y cuándo, en frases (“Ana cerró el aviso #128 a las 10:51”). |
| P17 | **Mi cuenta** | `/mi-cuenta` | Autenticado | Datos, contraseña, verificación en dos pasos, sesiones activas. |
| P18 | **Sala de control** | `/sala` | Dispositivo kiosco | Modo oscuro, pantalla completa, sin menú, tipografía ×1,35, rotación de zonas cada 20 s, avisos fijos arriba. Sonido opcional para “Evacuar”. |
| P19 | Errores | 403/404/500 | — | Mensaje humano + botón “Volver al inicio”. |

Todas las rutas HTML pasan a español natural. Las rutas viejas redirigen con 301 durante una versión.

---

## 8. Componentes (Jinja2 macros en `templates/components/`)

`status_badge(level)`, `status_banner(summary)`, `zone_card(zone)`, `gas_tile(gas, now, next)`, `alert_card(alert)`, `explain_block(explanation)`, `action_block(recommendation)`, `metric_big(value, label, help)`, `chart(kind, data_url)`, `empty_state(icon, title, text, action)`, `data_table(columns, rows)`, `filter_bar(...)`, `confirm_dialog(...)`, `toast(...)`, `page_header(title, subtitle, actions)`.

Cada macro tiene una página de muestra en `/_componentes` (solo en `ENVIRONMENT=local`), que sirve como catálogo vivo y como base de las capturas de regresión visual.

---

## 9. Fases

| Fase | Pasos | Definición de terminado |
|------|-------|-------------------------|
| F1 Co-diseño | Sesión con operadores y el jefe de seguridad usando bocetos en papel o Figma de P2, P4 y P8; ajustar los textos de `copy.py` | Acta en `docs/ux/codiseno.md` |
| F2 Fundaciones | Tokens, fuentes, `base.css`, layout, macros, `charts.js`, htmx, Lucide | `/_componentes` completo; prueba de contraste en verde |
| F3 Operación | P2, P3, P4, P5, P18 | Pruebas E2E de ver aviso, “Ya lo vi” y cerrar |
| F4 Gestión | P6–P13, P16, P17 | Pruebas por rol |
| F5 Técnico | P14, P15 (migrar las vistas ML actuales) | Comparativa del Plan 17 visible |
| F6 Pulido | Estados vacíos, carga, errores, móvil, modo oscuro, `prefers-reduced-motion` | Accesibilidad sin violaciones graves; regresión visual aprobada |
| F7 Limpieza | Retirar Bootstrap, Chart.js, Inter, templates viejos y `theme.css` | Ninguna referencia (prueba de búsqueda en el código) |

---

## Definición de terminado del Plan 18
- [x] Todas las pantallas de §7 implementadas con macros y tokens.
- [x] Cero términos prohibidos en las vistas operativas (verificador de lenguaje).
- [x] Contraste AA en todas las combinaciones de estado.
- [x] Accesibilidad de P2/P3/P4/P8/P18 con landmarks y `lang=es`; axe-core vía Playwright queda opcional (se omite si no está instalado).
- [x] Captura de referencia de `/ingresar`; re-aprobación visual pixel a pixel cuando haya Playwright.
- [x] Modo sala de control operativo con dispositivo kiosco.
- [x] `python scripts/verify.py --plan 18` en verde.
