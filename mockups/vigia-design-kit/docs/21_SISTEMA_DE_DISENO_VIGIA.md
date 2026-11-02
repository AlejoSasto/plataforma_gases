# 21 — Sistema de diseño Vigía (identidad minera)

> **Reemplaza la sección 3 del Plan 18** (tokens, colores y tipografía) y fija la identidad visual definitiva. El resto del Plan 18 sigue vigente: pantallas, lenguaje natural, fases y pruebas.
> **Fuente única de verdad del código:** `mockups/assets/css/tokens.css`. Si este documento y el archivo difieren, manda el archivo.
> **Referencia visual:** `screenshots/` y `mockups/*.html` (se abren con `python -m http.server 8765 --directory mockups`).

---

## 1. Identidad

**Nombre de trabajo:** **Vigía**, con el descriptor “Gases en la mina”. Un vigía es quien observa y avisa a tiempo, que es exactamente lo que hace el sistema. El nombre se puede cambiar: solo aparece en `copy.py` (`APP_NAME`) y en los recursos de `brand/`.

**Para quién es:** operadores de sala, supervisores de seguridad y gerencia de una mina subterránea de carbón en Cundinamarca. No son expertos en inteligencia artificial.

**Qué debe lograr cada pantalla:** responder en 3 segundos tres preguntas: ¿estamos bien ahora?, ¿qué viene en los próximos minutos? y ¿qué tengo que hacer?

**De dónde sale la identidad.** Todo viene de la mina, no de una plantilla de software:

| Elemento de la mina | Cómo aparece en el sistema |
|---------------------|----------------------------|
| Estratos de roca y mantos de carbón | Isotipo, franja del riel, ilustración de ingreso, fondo del corte esquemático |
| Planos de ventilación: azul = aire fresco, rojo = aire de retorno | El azul “Aire fresco” es el color de acción. El rojo de retorno solo se usa en ilustraciones |
| Polvo de roca inertizante (blanco grisáceo) | Fondo general de la interfaz |
| Lámpara del minero | Brillos cálidos en las ilustraciones (nunca en la interfaz) |
| Señalética minera semicondensada | Archivo al 88 % de ancho en títulos y frases de estado |
| Corte transversal de la mina | **Elemento distintivo**: el inicio muestra la mina como un corte esquemático con el estado de cada zona |

**Dónde se gasta la audacia:** en un solo lugar, el corte esquemático de la mina en la pantalla Hoy. Todo lo demás es sobrio y disciplinado.

---

## 2. Principios

1. **El color fuerte es solo para el estado de los gases.** Verde, ámbar, naranja y rojo nunca se usan como decoración, ni en botones, gráficos de marca o encabezados.
2. **Nunca solo color.** Cada estado lleva color, ícono y palabra (“Actuar ya”). Esto cubre daltonismo y pantallas con mala luz.
3. **Frases antes que números.** Primero se dice qué pasa (“El metano podría llegar al límite en unos 7 minutos”) y después se muestra la cifra.
4. **Lenguaje de la operación.** Gases, zonas, minutos y acciones. Cero jerga de IA fuera del Laboratorio (Plan 18 §5).
5. **Jerarquía por forma, no por adorno.** El radio, el borde y el peso comunican importancia. Sin sombras en tarjetas, sin degradados decorativos.
6. **Funciona sin internet.** Fuentes, íconos y gráficos se sirven localmente (el equipo en bocamina opera sin red).

---

## 3. Color

### 3.1 Paleta base

| Nombre | Hex | Token | Uso |
|--------|-----|-------|-----|
| Antracita | `#1A1E24` | `--c-antracita` | Texto principal, riel de navegación |
| Pizarra | `#4A525E` | `--c-pizarra` | Texto secundario |
| Estéril | `#5F6772` | `--c-esteril` | Ayudas, marcas de tiempo |
| Entibado | `#DCE0E3` | `--c-entibado` | Bordes y separadores |
| Polvo de roca | `#EEF0EF` | `--c-polvo-roca` | Fondo general |
| Aire fresco | `#1C5A8E` | `--c-ventilacion` | Acción principal, enlaces, foco de selección |
| Aire fresco oscuro | `#154672` | `--c-ventilacion-700` | Hover de la acción |
| Aire fresco suave | `#E5EEF6` | `--c-ventilacion-50` | Fondos de selección |
| Retorno | `#8E3B2E` | `--c-retorno` | Solo ilustraciones y planos |
| Lámpara | `#FFE3A1` | `--c-lampara` | Solo brillos de ilustración |

### 3.2 Estados de los gases

| Estado | Palabra | Ícono (Lucide) | Sólido | Fondo suave | Texto sobre suave |
|--------|---------|----------------|--------|-------------|-------------------|
| normal | Normal | `circle-check` | `#1F8A5B` | `#E5F3EC` | `#14603F` |
| vigilar | Vigilar | `eye` | `#B97E00` | `#FBF0D6` | `#6E4B00` |
| actuar | Actuar ya | `triangle-alert` | `#D2581A` | `#FCE7DA` | `#93390A` |
| evacuar | Evacuar | `siren` | `#C1262E` | `#FAE3E4` | `#921A20` |
| sindatos | Sin datos | `circle-dashed` (borde punteado) | `#7D8590` | `#ECEEF0` | `#454C56` |

- “Evacuar” es la **única** insignia con fondo sólido y texto blanco. Así destaca sobre las demás.
- Sala de control (modo oscuro): valores propios en `[data-theme="sala"]`, también verificados.

### 3.3 Contraste (verificado)

`python tools/check_contrast.py` comprueba 35 pares (claro y sala) contra WCAG 2.2: texto ≥ 4,5:1 y marcas de gráfico ≥ 3:1. **Resultado actual: todos pasan.** Esta verificación entra al `verify.py` del Plan 20 (etapa de accesibilidad).

---

## 4. Tipografía

**Dos familias, cada una con un rol claro:**

| Familia | Rol | Dónde |
|---------|-----|-------|
| **Archivo** (variable, peso 100–900, ancho 62–125 %) | Toda la interfaz: títulos, texto, lecturas | Todas las vistas |
| **IBM Plex Mono** | Cifras técnicas | **Solo** Laboratorio y Calidad de los datos |

Archivo tiene raíz de grotesca industrial; su eje de ancho permite títulos semicondensados al estilo de la señalética minera sin cargar otra fuente. Las lecturas usan Archivo con **cifras tabulares** (`font-variant-numeric: tabular-nums`) para que los números no “bailen” al actualizarse. La monoespaciada queda solo para el área técnica, donde comunica “dato de laboratorio”.

### 4.1 Escala

| Rol | Tamaño / interlineado | Peso | Ancho | Token |
|-----|-----------------------|------|-------|-------|
| Sala de control (alerta) | 56 / 59 px | 650 | 85 % | `--fs-kiosk` |
| Frase de estado | 40 / 44 px | 650 | 88 % | `--fs-display` |
| Título de página | 30 / 36 px | 600 | 88 % | `--fs-h1` |
| Título de bloque | 22 / 28 px | 600 | 88 % | `--fs-h2` |
| Título de tarjeta | 18 / 24 px | 600 | 100 % | `--fs-h3` |
| Cuerpo | 16 / 24 px | 400 | 100 % | `--fs-body` |
| Pequeño | 14 / 20 px | 400 | 100 % | `--fs-small` |
| Marca de tiempo | 13 / 18 px | 400 | 100 % | `--fs-micro` |
| Lectura protagonista | 44 px | 600 tabular | 100 % | `--fs-read-xl` |
| Lectura en tarjeta | 24 px | 600 tabular | 100 % | `--fs-read-l` |
| Lectura en tabla | 16 px | 600 tabular | 100 % | `--fs-read-m` |

**Reglas:**
- Todo en **tipo oración** (“Avisos abiertos”, no “AVISOS ABIERTOS”). Sin mayúsculas sostenidas en etiquetas.
- Sin resaltar una sola palabra del titular con otro color o cursiva.
- Líneas de texto ≤ 70 caracteres (`max-width: 68ch`).
- La unidad va después del número, más pequeña y en gris: `0,72 %`.
- Formato **es-CO**: coma decimal, hora de 24 h (`10:42`), zona horaria de Bogotá.
- Sala de control: toda la escala ×1,35 (se hereda con `font-size: 135%`).

---

## 5. Espaciado, forma y elevación

- **Espaciado** base 4: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64 (`--sp-*`).
- **El radio comunica jerarquía:**

| Elemento | Radio |
|----------|-------|
| Insignias de estado | 999 px (píldora) |
| Botones y campos | 6 px |
| Paneles | 10 px |
| Diálogos flotantes | 14 px |

- **Elevación:** los paneles usan borde de 1 px y nunca sombra. La sombra (`--shadow-float`) es solo para lo que flota: menús, diálogos y avisos emergentes.
- **Acento lateral:** los avisos llevan una barra de 4 px del color de su estado a la izquierda. La franja de estado general lleva 6 px.

---

## 6. Layout

```
┌────────────┬──────────────────────────────────────────────────────┐
│  RIEL      │ Barra superior 56 px: mina · datos al día · avisos   │
│ antracita  ├──────────────────────────────────────────────────────┤
│ 232 px     │ Franja de estado (frase grande + hora)               │
│            ├───────────────────────────────────┬──────────────────┤
│ Operación  │ La mina ahora (corte esquemático) │ Avisos abiertos  │
│ Seguimiento│                                   │                  │
│ Administr. ├───────────────────────────────────┤ Turno            │
│ Laboratorio│ Zona en alerta: gráfico + gases   │                  │
│ (Técnico)  │                                   │                  │
└────────────┴───────────────────────────────────┴──────────────────┘
```

- Contenido alineado a la izquierda, ancho máximo 1360 px, márgenes de 32 px.
- Rejilla de inicio: `minmax(0, 1fr) 380px`; bajo 1180 px pasa a una columna.
- Bajo 900 px: el riel desaparece, aparece una **barra inferior** de 4 ítems y el corte de la mina se reemplaza por una **lista de zonas ordenada por gravedad**.
- El riel agrupa por tarea: Operación, Seguimiento, Administración. El Laboratorio lleva la marca “Técnico”.

---

## 7. El corte esquemático de la mina (componente distintivo)

**Qué es.** Un dibujo simple de la mina vista de lado: superficie con trama, mantos de carbón como bandas, galerías como trazos y cada zona como un nodo con el color de su estado.

**Contrato de datos** (`GET /fragmentos/mapa` devuelve el SVG ya renderizado, o `/api/estado/zonas` en JSON):

```json
[
  {"id": "f3s", "name": "Frente 3 Sur", "state": "actuar",
   "x": 802, "y": 272, "label": "CH₄ 0,72 % y subiendo"}
]
```

- Las coordenadas `x, y` se guardan por zona en `sites.map_x`, `sites.map_y` (agregar en una migración junto con M2 del Plan 16) y se editan en Ajustes. El trazado de galerías se guarda una vez por mina en `app_settings.mine_layout` (lista de polilíneas).
- **Nodo:** círculo de 13 px con borde de 4 px del color del estado. “Sin datos” lleva borde punteado y sin punto central. “Actuar ya” y “Evacuar” llevan un pulso suave (desactivado con `prefers-reduced-motion`).
- **Etiqueta:** nombre de zona (16 px, 600) más la lectura principal (15 px, tabular). Las etiquetas no deben cruzar flechas ni nodos (revisar con capturas).
- **Accesible:** cada nodo es `role="button"` con `aria-label="Frente 3 Sur: Actuar ya. CH₄ 0,72 % y subiendo"` y abre la zona con Enter.
- **Móvil:** se reemplaza por `zone-list` (misma información, ordenada: evacuar, actuar, vigilar, sin datos, normal).
- Implementación de referencia: `renderMine()` y `renderZoneList()` en `mockups/assets/js/vigia.js`. En la app conviene renderizarlo en el servidor (Jinja2 + SVG) y refrescarlo con htmx.

---

## 8. Gráficos (ECharts 5, servido localmente)

### 8.1 “Ahora y lo que viene” (gráfico principal)

| Elemento | Estilo |
|----------|--------|
| Lo que marcó el sensor (última hora) | Línea sólida antracita (`--chart-measured`), 2,2 px |
| Lo que se espera (próximos 10 min) | Línea punteada azul aire fresco (`--chart-expected`), 2,4 px, con punto final |
| Rango probable (q10–q90) | Banda azul al 14 % (`--chart-band`) |
| Ahora | Línea vertical punteada gris con la etiqueta “Ahora” |
| Límites | Líneas horizontales del color de cada estado, con **etiqueta directa** al final (“Actuar ya 1,0 %”) |
| Rejilla | Solo líneas horizontales punteadas tenues |
| Leyenda | No va dentro del gráfico. Va debajo, en frases (“Lo que marcó el sensor”) |
| Tooltip | Frase completa: “A las 10:42 se espera alrededor de 1,05 %. Podría estar entre 0,80 % y 1,22 %” |

### 8.2 Reglas generales

- Renderizador SVG (`echarts.init(el, null, {renderer: "svg"})`): nítido en pantallas de sala.
- Los colores siempre salen de variables CSS, así el modo sala funciona sin código extra.
- Máximo dos series de marca (medido y esperado) más los colores de estado.
- Ejes con formato es-CO; las etiquetas del eje X ocultan solapes (`hideOverlap`).
- Sin animación de entrada.
- Los gráficos de confiabilidad son barras simples con el valor encima en frase (“9 de 10”).
- Todo en `app/static/js/charts.js` con una función por tipo. Ningún template configura ECharts a mano.

### 8.3 Minigráfico de tendencia

SVG de 96 × 28 px, sin ejes. Línea gris si está normal o del color del estado si no, con un punto en el último valor.

---

## 9. Iconografía

- **Lucide** (trazo de 2 px, esquinas redondeadas), servido como sprite local `assets/icons/sprite.svg` y usado con `<svg><use href="…#i-nombre"></use></svg>`.
- Tamaños: 16 px (en línea), 20 px (navegación y botones), 24 px (encabezados), 28–56 px (franja de estado y sala).
- Un ícono siempre acompaña a una palabra. La excepción son los botones de la barra superior, que llevan `aria-label`.
- Íconos usados por rol: ver la lista en `mockups/assets/icons/`. Si hace falta uno nuevo, se copia desde `lucide-static` y se regenera el sprite (`tools/build_sprite`, ver README).

---

## 10. Ilustración

| Archivo | Uso |
|---------|-----|
| `login-hero.svg` | Panel izquierdo de Ingresar e imagen para compartir: corte de la mina con castillete, estratos, galerías, lámparas y sensores vigilando |
| `vacio-despejado.svg` | Estado vacío de Avisos (“No hay avisos abiertos”) |
| `sensor-sin-datos.svg` | Sensor sin señal |
| `error-galeria.svg` | Página no encontrada (galería que termina en roca) |

**Estilo:** línea simple de 4 px en pizarra, rellenos planos con los neutros de la paleta, un solo acento por ilustración (azul aire fresco, verde de estado o luz de lámpara). Sin personas dibujadas, sin degradados salvo el brillo de la lámpara.

**Marca exportada (`brand/`):** isotipo SVG y PNG 512 px, logo horizontal claro y oscuro, favicon e imagen para compartir de 1200 × 630.

---

## 11. Movimiento

- 120–180 ms con `cubic-bezier(.2,.7,.2,1)`, solo como respuesta a una acción (abrir, cerrar, confirmar).
- Un único movimiento automático: el pulso de los nodos en “Actuar ya” y “Evacuar”.
- `prefers-reduced-motion` desactiva todo.
- La actualización de datos (htmx) no anima: reemplaza el fragmento. El cambio de estado se comunica con color, palabra y el aviso.

---

## 12. Accesibilidad (piso de calidad)

- Contraste verificado (§3.3). Foco visible con anillo azul de 3 px.
- Todo es operable con teclado, incluidos los nodos del corte.
- La franja de estado general usa `aria-live="polite"`. Las alertas de la sala usan `role="alert"`.
- Objetivos táctiles de al menos 40 px (botones de 40 px, grandes de 48 px).
- `lang="es-CO"` en todas las páginas.

---

## 13. Lo que no se hace

| No | Por qué |
|----|---------|
| Usar verde, ámbar o rojo como color de marca o decoración | Confunde el estado de los gases |
| Tarjetas idénticas con sombra gris para todo | Es la estética de plantilla; aquí la jerarquía la da el radio y el borde |
| Etiquetas en MAYÚSCULAS sobre cada título | Ruido sin información |
| Fuente monoespaciada en la operación | Comunica “técnico”; solo en el Laboratorio |
| Flechas “→” al final de botones y enlaces | El texto del botón ya dice qué pasa |
| Mostrar probabilidades, porcentajes de confianza o nombres de modelos en vistas operativas | Lenguaje no técnico (Plan 18 §5) |
| Cargar fuentes o librerías desde CDN | El equipo de bocamina puede no tener internet |
