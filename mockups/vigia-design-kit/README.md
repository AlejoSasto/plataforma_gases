# Vigía — kit de diseño para Cursor

Identidad visual, sistema de diseño, mockups navegables, imágenes y reglas para los agentes de Cursor de la **Plataforma de Monitoreo y Predicción de Gases** (minería de carbón).

## Cómo instalarlo en el repositorio

1. Copia la carpeta completa del kit a la raíz del repositorio con el nombre `design/`.
2. Mueve `design/.cursor/rules/*.mdc` a `.cursor/rules/` del repositorio (si ya existe la carpeta, solo agrega los tres archivos).
3. Copia `design/docs/21_*.md` y `design/docs/22_*.md` a `planes/` junto a los planes 14–20.
4. Abre Cursor en modo agente y pega el prompt de `docs/22_MOCKUPS_Y_GUIA_DE_IMPLEMENTACION.md` §7.

## Qué contiene

```
design/
├── README.md
├── docs/
│   ├── 21_SISTEMA_DE_DISENO_VIGIA.md       identidad, color, tipografía, layout, gráficos, ilustración
│   └── 22_MOCKUPS_Y_GUIA_DE_IMPLEMENTACION.md   pantalla por pantalla, macros, datos, prompt de Cursor
├── .cursor/rules/
│   ├── vigia-ui.mdc                         reglas visuales (templates, CSS, JS)
│   ├── vigia-lenguaje.mdc                   lenguaje no técnico
│   └── vigia-graficos.mdc                   convenciones ECharts
├── tokens/tokens.json                       tokens en JSON (espejo de tokens.css)
├── mockups/                                 HTML estático navegable (abrir con un servidor local)
│   ├── marca.html ingresar.html hoy.html avisos.html aviso.html
│   ├── confiabilidad.html sala.html equipo.html laboratorio.html componentes.html
│   └── assets/
│       ├── css/tokens.css                   FUENTE DE VERDAD de los tokens
│       ├── css/app.css                      base, layout y componentes
│       ├── js/vigia.js                      corte de la mina, gráficos, íconos (datos ficticios)
│       ├── js/echarts.min.js                ECharts 5 local
│       ├── fonts/                           Archivo variable + IBM Plex Mono (woff2)
│       ├── icons/                           Lucide + sprite.svg
│       └── img/                             isotipo, favicon e ilustraciones SVG
├── brand/                                   logos e imágenes exportadas (SVG y PNG)
├── screenshots/                             capturas PNG de referencia (escritorio y móvil)
└── tools/
    ├── build_mockups.py                     regenera los HTML desde un shell común
    ├── screenshots.py                       regenera las capturas (Playwright)
    ├── export_brand.py                      regenera los PNG de marca
    ├── build_sprite.py                      regenera el sprite de íconos
    └── check_contrast.py                    verifica contraste WCAG de los tokens
```

## Ver los mockups

```bash
python -m http.server 8765 --directory mockups
# http://localhost:8765/hoy.html  ·  /sala.html  ·  /marca.html
```

Todo funciona sin internet: fuentes, íconos y gráficos son locales.

## Regenerar

```bash
python tools/build_mockups.py          # HTML
python tools/check_contrast.py         # contraste (debe salir todo OK)
pip install playwright && playwright install chromium
python tools/screenshots.py http://localhost:8765
python tools/export_brand.py http://localhost:8765
```

## Licencias de terceros

- Archivo: SIL Open Font License 1.1 (Omnibus-Type).
- IBM Plex Mono: SIL Open Font License 1.1 (IBM).
- Lucide: ISC.
- Apache ECharts: Apache 2.0.

Las ilustraciones, el isotipo y los mockups son originales de este kit. Los datos que aparecen en los mockups (zonas, lecturas, personas, métricas) son **ficticios** y solo sirven de referencia visual.
