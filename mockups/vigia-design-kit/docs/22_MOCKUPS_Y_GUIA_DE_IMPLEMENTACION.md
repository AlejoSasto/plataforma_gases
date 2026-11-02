# 22 — Mockups y guía de implementación para Cursor

> Convierte los mockups estáticos de `mockups/` en templates Jinja2 de la plataforma. Complementa el **Plan 18** (pantallas, lenguaje, fases) y el **Plan 21** (sistema de diseño).
> **Regla de oro:** el mockup es la referencia visual y de texto. La implementación debe verse igual (comparar con `screenshots/`) y usar datos reales de la base, nunca los datos ficticios del mockup.

---

## 1. Cómo ver los mockups

```bash
python -m http.server 8765 --directory mockups
# abrir http://localhost:8765/hoy.html
```

| Mockup | Captura | Pantalla del Plan 18 |
|--------|---------|----------------------|
| `marca.html` | `00-hoja-de-marca.png` | Hoja de marca (referencia) |
| `ingresar.html` | `01-ingresar.png`, `11-ingresar-movil.png` | P1 Ingresar |
| `hoy.html` | `02-hoy.png`, `10-hoy-movil.png` | P2 Hoy |
| `avisos.html` | `03-avisos.png` | P3 Avisos |
| `aviso.html` | `04-aviso-detalle.png` | P4 Detalle del aviso |
| `confiabilidad.html` | `05-confiabilidad.png` | P8 Confiabilidad |
| `sala.html` | `06-sala-de-control.png` | P18 Sala de control |
| `equipo.html` | `07-equipo.png` | P10 Equipo |
| `laboratorio.html` | `08-laboratorio.png` | P15 Laboratorio |
| `componentes.html` | `09-componentes.png` | Catálogo `/_componentes` |

Las pantallas sin mockup propio (Zonas, Historial, Informes, Contactos, Límites, Cargar datos, Calidad de los datos, Bitácora, Mi cuenta) se construyen **con los mismos componentes**. Toman como patrón: listas = `avisos.html`, tablas = `equipo.html`, detalle = `aviso.html`, formularios = `ingresar.html`.

---

## 2. Dónde va cada archivo en la app

| Kit | Destino en el repositorio |
|-----|---------------------------|
| `mockups/assets/css/tokens.css` | `app/static/css/tokens.css` (copiar tal cual) |
| `mockups/assets/css/app.css` | Dividir en `app/static/css/base.css` (base y tipografía), `layout.css` (riel, barra superior, rejillas, responsivo) y `components.css` (el resto) |
| `mockups/assets/fonts/*` | `app/static/fonts/` |
| `mockups/assets/js/echarts.min.js` | `app/static/vendor/echarts.min.js` |
| `mockups/assets/icons/sprite.svg` | `app/static/icons/sprite.svg` |
| `mockups/assets/js/vigia.js` | Separar en `app/static/js/charts.js` (gráficos), `mine-map.js` (corte y lista de zonas) y `app.js` (íconos, contraseña, utilidades). **Eliminar** `ZONES` y `methaneSeries()`: los datos llegan del servidor |
| `mockups/assets/img/*.svg` | `app/static/img/` |
| `brand/*` | `app/static/brand/` y `docs/marca/` |
| htmx | `npm i htmx.org` → copiar `dist/htmx.min.js` a `app/static/vendor/` |

> **Cambio respecto al Plan 18 §2:** nada se carga desde CDN. Fuentes, íconos, ECharts y htmx se sirven desde `app/static/` para que la plataforma funcione sin internet en bocamina. Actualizar la CSP del Plan 19 §4 (`default-src 'self'`).

### Base de templates

```
app/templates/
├── base.html                 # <head>, tokens, fuentes, scripts, bloque content
├── layouts/
│   ├── app.html              # riel + barra superior + main + barra móvil
│   ├── auth.html             # dos columnas de Ingresar
│   └── sala.html             # data-theme="sala", sin navegación
├── components/               # macros (ver §3)
├── fragments/                # piezas que refresca htmx
│   ├── estado_general.html
│   ├── mapa_mina.html
│   ├── avisos_abiertos.html
│   └── gases_zona.html
└── pages/
    ├── hoy.html  avisos/lista.html  avisos/detalle.html  confiabilidad.html
    ├── equipo.html  laboratorio/*.html  sala.html  ingresar.html ...
```

El riel se arma desde `app/modules/dashboard/nav.py` filtrando por permisos (Plan 19 §2). La estructura de grupos e íconos está en `NAV` de `tools/build_mockups.py`.

---

## 3. Componentes (macros Jinja2) y su clase CSS

| Macro | Clases | Datos | Mockup |
|-------|--------|-------|--------|
| `status_badge(level, size="md")` | `.status .status--{level}` | `normal/vigilar/actuar/evacuar/sindatos` → palabra e ícono desde `copy.STATES` | todas |
| `state_line(summary)` | `.state-line` | `{level, title, detail, now}` | hoy |
| `mine_map(zones, layout)` | `.mine`, `.zone-list` | §7 del Plan 21 | hoy |
| `gas_table(rows)` | `.gas-table` | `{gas, zone, now, next, unit, spark[], level}` | hoy |
| `alert_item(alert)` | `.alert-item .alert-item--{level}` | `{level, kind, title, plain_message, created_at, seen_by}` | hoy, avisos |
| `alert_card(alert)` | `.alert-card` | más `readings`, `why`, `todo[]` | aviso |
| `readings(items)` | `.readings` | `[{label, value, unit, is_limit}]` | aviso, componentes |
| `why_block(text)` / `todo_block(steps)` | `.why`, `.todo` | `forecast_explanations.plain_text`, `alerts.plain_recommendation` | aviso |
| `timeline(events)` | `.timeline` | eventos del aviso (creado, notificado, visto, cerrado) | aviso |
| `chart(kind, url, height)` | `.chart` + `data-chart` | `kind ∈ now-next, monthly, lab`; `url` del JSON | hoy, aviso, sala |
| `of_ten(n)` | `.of-ten` | entero 0–10 | confiabilidad |
| `trust_card(q, answer, body, note)` | `.trust` | — | confiabilidad |
| `person(user)` / `tag(text, kind)` | `.person`, `.tag` | — | equipo |
| `empty_state(img, title, text, action)` | `.empty` | — | componentes |
| `page_head(title, text, actions)` | `.page-head` | — | todas |
| `tabs(items, active)` / `filters(...)` | `.tabs`, `.filters` | — | avisos |
| `toast(text)` | `.toast` | — | equipo |

Todos los textos de los macros salen de `app/shared/copy.py` (Plan 18 §5), nunca escritos a mano en el template.

---

## 4. Datos que necesita cada pantalla

| Pantalla | Fragmentos htmx (refresco) | Endpoints JSON |
|----------|---------------------------|----------------|
| Hoy | `estado_general`, `mapa_mina`, `avisos_abiertos`, `gases_zona?zona=` cada `grid_step_minutes` | `GET /api/pronostico/{sensor_id}/ahora-y-lo-que-viene` |
| Avisos | lista por pestaña y filtros (`hx-get` con parámetros) | — |
| Detalle del aviso | `timeline` cada 30 s | el mismo del gráfico |
| Confiabilidad | — (se calcula al cargar) | `GET /api/confiabilidad/mensual` |
| Sala | `sala_alerta`, `sala_zonas` cada paso; reloj local | gráfico de la zona con aviso más grave |
| Laboratorio | — | `GET /api/laboratorio/comparacion` |

**Contrato del gráfico “Ahora y lo que viene”:**

```json
{
  "gas": "CH4", "unit": "%", "now": "2026-11-01T10:35:00-05:00",
  "measured":  [["2026-11-01T09:35:00-05:00", 0.36], "..."],
  "expected":  [["2026-11-01T10:35:00-05:00", 0.72], "..."],
  "range_low": [["...", 0.70], "..."],
  "range_high":[["...", 0.75], "..."],
  "limits": [{"level": "vigilar", "value": 0.5}, {"level": "actuar", "value": 1.0}, {"level": "evacuar", "value": 1.5}],
  "has_forecast": true
}
```

Si `has_forecast` es `false` (no hay modelo activo), el gráfico muestra solo lo medido y la nota de `copy.NO_FORECAST`: “Por ahora mostramos solo lo que marcan los sensores”.

---

## 5. Criterios de aceptación visual por pantalla

| Pantalla | Debe cumplirse |
|----------|----------------|
| Ingresar | Dos columnas en escritorio; ilustración solo en la izquierda; error en lenguaje natural sin revelar si el correo existe; botón “Mostrar” funciona; una columna en móvil |
| Hoy | La frase de estado resume la situación en una línea; el corte muestra todas las zonas activas sin etiquetas encimadas; el panel de la zona más grave aparece primero; en móvil se ve la lista de zonas ordenada |
| Avisos | Pestañas con conteo; cada aviso tiene barra lateral de color, insignia, tipo (anticipado o confirmado), hora relativa y acción principal |
| Detalle | Frase protagonista con el tiempo estimado; tres lecturas (ahora, esperado, límite); “Por qué avisamos” y “Qué hacer” presentes; seguimiento como secuencia |
| Confiabilidad | Tres preguntas respondidas en frase; cascos “de cada 10”; bloque honesto de lo no avisado; cero términos técnicos |
| Sala | Modo oscuro; texto ×1,35; alerta legible a 3 m; sin navegación; se ve completa en 1920 × 1080 sin desplazamiento |
| Equipo | Rol con nombre en español; zonas como etiquetas; estados “Invitado” y “Bloqueado” visibles |
| Laboratorio | Banner “Área técnica”; métricas en Plex Mono; metas en verde o rojo sin maquillar; modelo activo marcado |

---

## 6. Regresión visual

1. Las capturas de `screenshots/` son la **referencia de diseño** (no la base automática, porque usan datos ficticios).
2. Para las pruebas del Plan 20 (etapa 11) se generan capturas propias con datos de fábrica fijos y la hora congelada (`10:35`), con los mismos tamaños de `tools/screenshots.py`.
3. Primera aprobación: un humano compara cada captura de la app con su par de `screenshots/` y anota diferencias en `planes/BITACORA_BUCLE.md`.

---

## 7. Prompt para Cursor (modo agente)

```text
Eres el agente de interfaz de la Plataforma de Monitoreo y Predicción de Gases ("Vigía").
Contexto obligatorio:
- planes/CONTEXTO_SISTEMA.md, planes/14_REFORMULACION_INDICE.md
- planes/18_UX_UI_LENGUAJE_NATURAL.md (pantallas, lenguaje, fases)
- design/docs/21_SISTEMA_DE_DISENO_VIGIA.md (tokens, tipografía, color, gráficos)
- design/docs/22_MOCKUPS_Y_GUIA_DE_IMPLEMENTACION.md (este archivo)
- design/mockups/*.html y design/screenshots/*.png (referencia visual)
- .cursor/rules/vigia-*.mdc

Tarea: implementar la pantalla <NOMBRE> según su mockup, en bucle:
1. Copia los recursos de §2 si aún no están en app/static/.
2. Crea o ajusta los macros de §3 que la pantalla necesita, con textos desde copy.py.
3. Construye el template en app/templates/pages/ usando layouts/app.html.
4. Conecta los datos reales (§4): servicio → router → template/fragmento. Nada de datos ficticios.
5. Ejecuta: python scripts/verify.py --plan 18
6. Toma una captura de la pantalla (tamaños de tools/screenshots.py) y compárala con
   design/screenshots/<captura>.png. Lista diferencias de color, tipografía, espaciado y texto.
7. Corrige y repite 5–6 hasta que no queden diferencias relevantes y verify esté en verde.
8. Registra en planes/BITACORA_BUCLE.md: pantalla, archivos, iteraciones, diferencias aceptadas.

Prohibido: colores, fuentes o tamaños fuera de tokens.css; CDN externos; textos técnicos en vistas
operativas; configurar ECharts dentro de un template; desactivar pruebas para pasar.
Orden sugerido: base y componentes → Hoy → Avisos → Detalle → Sala → Ingresar → Confiabilidad →
Equipo → resto de pantallas → Laboratorio → limpieza (retirar Bootstrap, Chart.js, Inter, theme.css).
```

---

## 8. Definición de terminado
- [ ] Recursos locales copiados; ninguna referencia a CDN en `app/templates/` ni en `app/static/`.
- [ ] Todos los macros de §3 existen y aparecen en `/_componentes`.
- [ ] Las pantallas con mockup coinciden con su captura (revisión humana registrada).
- [ ] Pantallas sin mockup construidas con los mismos componentes.
- [ ] `tools/check_contrast.py` integrado al `verify.py` y en verde.
- [ ] Verificador de lenguaje natural en verde.
- [ ] `python scripts/verify.py --plan 18` en verde.
