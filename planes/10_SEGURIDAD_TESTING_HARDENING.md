# Plan 10 — Seguridad, Testing y Hardening (F9)

## Objetivo
Cerrar brechas de seguridad, garantizar cobertura de pruebas sobre los flujos críticos y validar que la plataforma soporta la carga esperada antes de considerarla lista para operación real.

## Prerrequisitos
- Planes 01–09 desplegados y funcionando en GCP.

## Paso a paso

### 1. Endurecimiento de autenticación
- Rate limiting en `/auth/login` (ej. `slowapi` o lógica propia con Redis: N intentos fallidos por IP/usuario en X minutos → bloqueo temporal).
- Expiración y rotación de refresh tokens; invalidar todos los refresh tokens de un usuario al cambiar su password.
- Forzar HTTPS (Cloud Run ya lo hace) y cookies con `Secure`, `HttpOnly`, `SameSite=Lax` o `Strict`.
**Prueba:** simular 10 intentos fallidos de login y confirmar bloqueo temporal; confirmar que las cookies tienen los flags correctos (DevTools → Application → Cookies).

### 2. Cabeceras de seguridad HTTP
- Middleware que agregue `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`.
**Prueba:** `curl -I` contra el servicio en producción muestra las cabeceras esperadas.

### 3. Validación de entrada y salida
- Revisar que todos los `schemas.py` usan `Pydantic` con validadores estrictos (tipos, longitudes, rangos) — especialmente en `sensors_ingestion` (archivos subidos) y `ml_training` (parámetros de entrenamiento).
- Sanitizar cualquier dato que se renderice en Jinja2 (autoescape activo por defecto, no desactivarlo).
**Prueba:** enviar payloads malformados/adversariales a los endpoints críticos y confirmar respuestas 422 controladas, no errores 500.

### 4. Revisión de permisos (RBAC)
- Auditoría cruzada: por cada endpoint del sistema, confirmar que tiene un `require_permission(...)` explícito (o está intencionalmente público, como `/health` o `/login`).
- Generar una tabla de "endpoint → permiso requerido" como documentación viva.
**Prueba:** checklist manual recorriendo todos los routers; ningún endpoint de escritura queda sin protección.

### 5. Testing automatizado
- **Unit tests** por módulo: `service.py` de `auth`, `alerts`, `ml_training`, `sensors_ingestion` (mockeando repositorios/DB donde tenga sentido).
- **Integration tests**: flujos completos con base de datos de prueba (ej. contenedor Postgres efímero vía `testcontainers` o una BD de test dedicada) — login, ETL→predicción→alerta→notificación, generación de reportes.
- Meta de cobertura sugerida: ≥ 70% en `service.py` y `router.py` de los módulos críticos (auth, alerts, ml_training).
**Prueba:** `pytest --cov=app` reporta la cobertura objetivo; pipeline de CI falla si baja del umbral.

### 6. Pruebas de carga
- Herramienta: `locust` o `k6`.
- Escenarios: N usuarios consultando el dashboard simultáneamente, ingestas concurrentes, ráfaga de alertas.
- Objetivo: definir junto con el equipo el SLA esperado (ej. p95 < 500ms en endpoints de lectura) y ajustar `min-instances`/`max-instances` de Cloud Run según resultados.
**Prueba:** reporte de `k6`/`locust` con percentiles de latencia y tasa de error bajo la carga simulada.

### 7. Gestión de dependencias y vulnerabilidades
- `pip-audit` o `safety` en el pipeline de CI para detectar dependencias con CVEs conocidos.
- Actualizar imagen base (`python:3.11-slim`) periódicamente.
**Prueba:** CI falla si se detecta una vulnerabilidad de severidad alta/crítica sin resolver.

### 8. Copias de seguridad y recuperación
- Configurar backups automáticos de Cloud SQL (point-in-time recovery si el SLA lo requiere).
- Documentar (en un `RUNBOOK.md`) el procedimiento de restauración y de rollback de una migración fallida.
**Prueba:** ejercicio de restauración en un entorno de prueba, confirmando que los datos vuelven a un punto anterior sin corrupción.

### 9. Revisión final de auditoría
- Confirmar que `audit_log` cubre: login/logout, cambios de usuario/rol, entrenamiento/promoción de modelos, resolución de alertas, generación de reportes, cambios en stakeholders.
**Prueba:** recorrido manual de cada acción sensible del sistema, verificando su registro correspondiente.

## Checklist de validación (Definition of Done)
- [ ] Rate limiting y cookies seguras activos en producción.
- [ ] Cabeceras de seguridad presentes en todas las respuestas.
- [ ] Cobertura de tests ≥ umbral definido en los módulos críticos.
- [ ] Prueba de carga documentada con resultados dentro del SLA acordado.
- [ ] Pipeline de CI bloquea vulnerabilidades críticas conocidas.
- [ ] Procedimiento de backup/restauración probado al menos una vez.
- [ ] `audit_log` cubre el 100% de las acciones sensibles listadas.

---

**Con esto se cierra el ciclo completo (Planes 01–10).** La plataforma queda funcionando de extremo a extremo: ingesta → ETL trazado → entrenamiento y registro de modelos → predicción automática → alertas con recomendación → notificación a partes interesadas → dashboard en tiempo (cuasi-)real → reportes → despliegue escalable en GCP → hardening de seguridad y pruebas.
