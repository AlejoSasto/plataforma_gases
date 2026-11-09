# 35 — Mockups del sistema tal como está

**Ejecutor:** Claude.  
**Contrato:** [`27_PAQUETE_DISENO_INDICE.md`](27_PAQUETE_DISENO_INDICE.md).  
**Salida:** HTML estático en `mockups/estado-actual/`.  
**Bitácora:** `docs/diseno/bitacora/35.md`.

Estas maquetas retratan la interfaz que el código sirve hoy. No rediseñan Vigía y no modifican `app/`. El kit histórico `mockups/vigia-design-kit/` se deja intacto: es la referencia con la que se construyó el cascarón, no el inventario de pantallas actuales.

## Fuentes obligatorias

Antes de dibujar una pantalla, leer la plantilla que la sirve y el texto de `app/shared/copy.py`. Si el menú y la plantilla no coinciden, gana la plantilla.

- `app/templates/base.html` para el riel, la barra superior y la barra móvil.
- `app/static/css/tokens.css`, `base.css`, `layout.css` y `components.css`. No inventar hexadecimales: los mockups enlazan esos CSS, o copian las variables sin cambiarlas.
- `app/shared/copy.py`: marca «Vigía», descriptor «Gases en la mina», estados Normal, Vigilar, Actuar ya, Evacuar y Sin datos, y las etiquetas de `NAV`.
- Plantilla de cada ruta, en `app/templates/`, y la ruta en `app/modules/dashboard/ui_router.py` o `app/modules/assistant/router.py`.
- [`planes/21_SISTEMA_DE_DISENO_VIGIA.md`](../../planes/21_SISTEMA_DE_DISENO_VIGIA.md) solo para no contradecir el riel, la tipografía Archivo y el uso del color de estado.

## Reglas de la maqueta

- Un archivo HTML por pantalla, más `index.html` con el índice y la frase «Maqueta estática. No es la aplicación.»
- `lang="es-CO"`. Textos en tipo oración. Sin mayúsculas sostenidas y sin flechas en los botones.
- El color de estado solo pinta el estado del gas, junto con la palabra. Nunca decora botones ni fondos.
- IBM Plex Mono solo en Laboratorio y en Calidad de los datos. El resto usa Archivo.
- Datos de ejemplo fechados hasta el 11 de diciembre de 2025, que es el último dato del diagnóstico. La barra superior dice hasta cuándo hay datos. Un aviso de ejemplo distingue anticipado y confirmado, e histórico y en vivo.
- Ningún número de ejemplo presenta como cumplida una meta del anteproyecto.
- En las pantallas operativas no aparecen los términos prohibidos de `copy.FORBIDDEN_TERMS`. Laboratorio sí puede decir modelo, entrenamiento y producción, y abre con la marca de área técnica.
- El panel Preguntar muestra el texto de no disponibilidad sin conexión y, en otra maqueta o en un estado del mismo archivo, una respuesta que cita la evidencia y no da una orden de entrar al frente.
- Recursos locales. Si el HTML necesita la fuente o el sprite, apunta a `app/static/` con una ruta relativa desde `mockups/estado-actual/`, o duplica solo el enlace, sin copiar el binario de la fuente a otro sitio.
- No hace falta JavaScript de aplicación. Un gráfico puede ser una figura estática con la leyenda «medido», «se espera alrededor de» y la banda, sin inicializar ECharts si eso exige un servidor.

## Pantallas

Cada fila es un archivo. El nombre es estable. El contenido sale de la plantilla, no de este resumen.

| Archivo | Ruta real | Plantilla de partida |
|---------|-----------|----------------------|
| `ingresar.html` | `/ingresar` | `app/templates/auth/login.html` |
| `hoy.html` | `/` | `app/templates/dashboard/hoy.html` |
| `avisos.html` | `/avisos` | `app/templates/alerts/list.html` |
| `aviso.html` | `/avisos/{id}` | `app/templates/alerts/detail.html` |
| `equipos.html` | `/zonas` | `app/templates/sites/list.html` |
| `equipo-detalle.html` | `/zonas/{id}` y `/sensores/{id}` | `sites/detail.html`, `sites/sensor_detail.html` |
| `historial.html` | `/historial` | `app/templates/historial.html` |
| `confiabilidad.html` | `/confiabilidad` | `app/templates/dashboard/confiabilidad.html` |
| `resumen.html` | `/resumen` | `app/templates/dashboard/ejecutivo.html` |
| `informes.html` | `/informes` | `app/templates/reports/index.html` |
| `cargar.html` | `/datos/cargar` | `app/templates/ingestion/panel.html` |
| `calidad.html` | `/datos/calidad` | `app/templates/datos/calidad.html` |
| `limites.html` | `/ajustes/limites` | `app/templates/ajustes/limites.html` |
| `laboratorio.html` | `/laboratorio` | `app/templates/laboratorio/zoo.html` |
| `laboratorio-comparar.html` | `/laboratorio/comparar` | `app/templates/laboratorio/comparar.html` |
| `laboratorio-entrenar.html` | `/laboratorio/entrenar` | `app/templates/laboratorio/entrenar.html` |
| `laboratorio-resultados.html` | `/laboratorio/resultados` | `app/templates/laboratorio/resultados.html` |
| `contactos.html` | `/contactos` | `app/templates/stakeholders/list.html` |
| `equipo.html` | `/equipo` | `app/templates/users/list.html` |
| `roles.html` | `/roles` | `app/templates/roles/list.html` |
| `bitacora.html` | `/bitacora` | `app/templates/audit/list.html` |
| `mi-cuenta.html` | `/mi-cuenta` | `app/templates/profile/index.html` |
| `pantallas.html` | `/pantallas` | `app/templates/kiosk/list.html` |
| `sala.html` | `/sala` | `app/templates/sala.html` |
| `ayuda.html` | `/ayuda` | `app/templates/ayuda/index.html` |
| `preguntar.html` | botón Preguntar | `app/templates/assistant/panel.html` |

El riel de las maquetas con sesión usa los grupos de `base.html`: Operación (Hoy, Avisos, Equipos, Historial), Seguimiento (Informes, Confiabilidad, Resumen), Datos (Cargar datos, Calidad de los datos, Ajustes, Laboratorio) y Administración (Equipo, Pantallas, Contactos, Bitácora, Ayuda). La maqueta de sala no muestra el riel de administración. Ingresar no muestra el riel.

`index.html` enlaza cada archivo con el nombre visible de `NAV` y la ruta real.

## Pasos

1. Leer `base.html`, `copy.py` y las plantillas de la tabla.
2. Escribir los HTML. Si una plantilla ya no existe, no se inventa la pantalla: se anota en la bitácora y se omite el archivo.
3. Abrir `index.html` en un navegador, o comprobar que cada archivo tiene `lang="es-CO"`, el título Vigía y la nota de maqueta.
4. Escribir la bitácora con la lista de archivos y cualquier plantilla que no coincidiera con la tabla.

## Definición de terminado

- Existe `mockups/estado-actual/index.html` y un HTML por cada fila cuya plantilla siga en el repositorio.
- `mockups/vigia-design-kit/` no tiene cambios.
- Ningún archivo de `app/` fue modificado por este plan.
- Las maquetas operativas no usan la jerga prohibida. Laboratorio sí está marcado como área técnica.
- La bitácora existe en `docs/diseno/bitacora/35.md`.
