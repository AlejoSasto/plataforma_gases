# Plan 07 — Dashboard y UI (F6)

## Objetivo
Interfaz de visualización en tiempo (cuasi-)real, por rol, con paleta verde-azul/fondo blanco/tipografía Inter sobre Bootstrap5, que muestre predicciones, alertas y recomendaciones — cumple directamente el objetivo 4.

## Prerrequisitos
- Planes 02, 05 y 06 validados (hay usuarios/roles, alertas y stakeholders reales que mostrar).

## Paso a paso

### 1. Sistema de diseño (`app/static/css/theme.css`)
- Importar Inter (Google Fonts o self-host en `static/fonts/`).
- Definir variables CSS que sobreescriben Bootstrap5:
```css
:root {
  --bs-font-sans-serif: 'Inter', system-ui, sans-serif;
  --bs-primary: #0E9F6E;      /* verde */
  --bs-primary-rgb: 14,159,110;
  --bs-info: #0EA5E9;         /* azul */
  --bs-body-bg: #FFFFFF;
  --bs-body-color: #111827;
  --risk-normal: #16A34A;
  --risk-precaucion: #F59E0B;
  --risk-alerta: #EA580C;
  --risk-critico: #DC2626;
}
```
**Prueba:** una página de ejemplo con botones/badges de Bootstrap5 refleja la paleta sin tocar clases, solo el CSS de variables.

### 2. Layout base (`templates/base.html`)
- `<head>` con Bootstrap5 CDN o vendorizado + `theme.css`.
- Sidebar de navegación que se arma dinámicamente según los permisos del usuario (`current_user.permissions`), reutilizando `/auth/me`.
- Bloque `{% block content %}` para cada vista.
**Prueba:** un `operador_mina` no ve en el sidebar las opciones de "Usuarios" ni "Entrenar modelo" (porque no tiene esos permisos).

### 3. Vista principal por rol (`modules/dashboard/router.py` + `templates/dashboard/`)
- `GET /` — redirige según rol a la vista más relevante:
  - **Operador:** semáforo por sitio/sensor (tarjetas con color según `risk_level` actual), lista de alertas activas.
  - **Ingeniero de datos:** estado de últimas corridas ETL, comparación de modelos (tabla de `model_registry` con métricas), gráfico de distribución de gases.
  - **Interesado:** resumen ejecutivo (conteo de alertas por nivel en el periodo), acceso a reportes.
**Prueba:** iniciar sesión con cada rol y confirmar que la vista mostrada corresponde a la lista anterior.

### 4. Endpoints JSON de soporte para gráficos (`modules/dashboard/router.py`)
- `GET /dashboard/api/semaforo` — último `risk_level` por sensor/sitio.
- `GET /dashboard/api/series/{sensor_id}` — serie de tiempo de `Leyendo` + umbral STEL/TWA para graficar.
- `GET /dashboard/api/alertas-activas` — lista resumida para polling.
**Prueba:** cada endpoint responde JSON válido y consistente con lo que hay en `gas_readings`/`alerts`.

### 5. Actualización "tiempo real"
- **Fase inicial (recomendada para el taller):** polling cada 5–10 segundos vía `fetch()` desde JS a los endpoints del paso 4, con `setInterval`.
- **Fase futura (si se requiere verdadero tiempo real):** WebSocket (`/ws/alerts`) que empuja alertas nuevas al navegador sin polling.
**Prueba:** generar una alerta nueva (repitiendo el flujo del Plan 05) y confirmar que aparece en el dashboard dentro del intervalo de polling configurado, sin recargar la página.

### 6. Gráficos
- Usar Chart.js o ApexCharts (vía CDN) para: serie de tiempo por gas, distribución de niveles de riesgo, comparación de métricas de modelos.
- Aplicar la paleta del paso 1 a los datasets de cada gráfico.
**Prueba:** revisión visual: los colores de los gráficos coinciden con la paleta definida (no colores por defecto de la librería).

### 7. Componentes reutilizables
- Tarjeta KPI (`_kpi_card.html`), badge de nivel de riesgo (`_risk_badge.html`), tabla de alertas (`_alerts_table.html`) — como *partials* Jinja2 incluidos con `{% include %}` para no duplicar HTML entre vistas.
**Prueba:** el mismo partial de badge de riesgo se usa en el dashboard de operador y en el portal de interesados sin duplicar CSS/HTML.

### 8. Accesibilidad y responsividad
- Verificar contraste de colores (verde/azul sobre blanco) cumple WCAG AA para texto pequeño.
- Layout responsivo con el grid de Bootstrap5 (probar en viewport móvil).
**Prueba:** Lighthouse (Chrome DevTools) reporta accesibilidad ≥ 90 en la vista principal.

## Checklist de validación (Definition of Done)
- [ ] Cada rol ve una vista adaptada a sus permisos, sin acceso a secciones no autorizadas.
- [ ] El semáforo de riesgo refleja el estado real de `alerts`/`predictions` más recientes.
- [ ] Las alertas nuevas aparecen en el dashboard sin recargar manualmente la página.
- [ ] La paleta verde-azul/Inter/fondo blanco está aplicada de forma consistente (no clases Bootstrap por defecto).
- [ ] Accesibilidad y responsividad verificadas.

**Siguiente paso:** `08_REPORTES.md`.
