# Plan 08 — Reportes (F7)

## Objetivo
Generar y descargar reportes (PDF/Excel) para operación e interesados: histórico de alertas, desempeño de modelos, resumen ejecutivo.

## Prerrequisitos
- Planes 05, 06 y 07 validados (hay alertas, notificaciones y dashboard con datos reales).

## Paso a paso

### 1. Modelo (`app/modules/reports/models.py`)
```
reports(id, type, period_start, period_end, file_path,
        generated_by FK users, created_at)
```
`type`: `alertas_periodo`, `desempeno_modelo`, `resumen_ejecutivo`.
**Prueba:** migración aplica.

### 2. Generadores (`modules/reports/generator.py`)
- `generate_alertas_periodo(db, start, end) -> bytes` (PDF con WeasyPrint o ReportLab): tabla de alertas, conteo por nivel, tiempo promedio de resolución.
- `generate_desempeno_modelo(db, model_registry_id) -> bytes`: métricas, matriz de confusión (si se guarda), comparación contra el modelo anterior.
- `generate_resumen_ejecutivo(db, start, end, stakeholder_id=None) -> bytes` (puede ser Excel con `openpyxl` u PDF): alertas por sitio, tendencia de gases, recomendaciones acumuladas.
Reutilizar el `theme.css` (colores/tipografía) en la plantilla HTML que WeasyPrint convierte a PDF, para mantener identidad visual.
**Prueba:** cada función genera un archivo válido (abrir el PDF/Excel resultante sin errores) con datos reales del entorno de pruebas.

### 3. Almacenamiento
- Local: guardar en `storage/reports/` (montado como volumen en Compose).
- GCP: subir a Cloud Storage (`reports/`) y guardar la URL/path en `reports.file_path` (se detalla en Plan 09).
**Prueba:** el archivo generado es recuperable posteriormente por su `file_path`.

### 4. Endpoints (`modules/reports/router.py`, protegidos con `reports.export`)
- `POST /reports/alertas` — body `{start, end}` → genera y devuelve el archivo (o lo encola si es pesado y notifica cuando esté listo).
- `POST /reports/modelo/{model_registry_id}`.
- `POST /reports/ejecutivo` — body `{start, end, stakeholder_id?}`.
- `GET /reports` — historial paginado con enlaces de descarga.
- `GET /reports/{id}/download`.
**Prueba:** generar un reporte de cada tipo vía Swagger UI y descargarlo correctamente.

### 5. Integración con el dashboard (Plan 07)
- Botón "Descargar reporte" en la vista de interesados y en la de ingeniero de datos, que llama a los endpoints anteriores.
**Prueba:** desde el navegador, el botón dispara la descarga del archivo sin errores de CORS/permmisos.

### 6. Auditoría
- Registrar en `audit_log` cada generación/descarga de reporte (`user_id`, `report_id`, tipo).

## Checklist de validación (Definition of Done)
- [ ] Los tres tipos de reporte se generan correctamente con datos reales.
- [ ] Los reportes mantienen la identidad visual (paleta/tipografía) definida en Plan 07.
- [ ] Descarga funcional desde el dashboard y desde la API directamente.
- [ ] Acceso protegido por permiso `reports.export`; un `interesado` solo puede generar/ver los reportes que le correspondan.
- [ ] Toda generación queda auditada.

**Siguiente paso:** `09_DESPLIEGUE_GCP_CICD.md`.
