# Plan 06 — Partes Interesadas y Notificaciones (F5)

## Objetivo

Registrar a las partes interesadas (gerencia, seguridad industrial, entes de control, etc.), permitirles suscribirse a alertas relevantes, y notificarles automáticamente cuando ocurren — cumpliendo la parte de "recomendaciones a los posibles usuarios" del objetivo 4.

## Prerrequisitos

- Plan 05 validado (existen alertas que notificar).

## Paso a paso

### 1. Modelos (`app/modules/stakeholders/models.py`)

```
stakeholders(id, name, type, organization, email, phone,
             notify_channels JSONB, created_at)
stakeholder_user(stakeholder_id FK, user_id FK NULLABLE)  -- si además tiene login
stakeholder_subscriptions(id, stakeholder_id FK, site_id FK NULLABLE,
                           sensor_id FK NULLABLE, min_level, created_at)
alert_notifications(id, alert_id FK, stakeholder_id FK, channel, status, sent_at, error)
```

`type`: `interno` | `externo`. `min_level`: nivel mínimo de alerta que le interesa (ej. solo ALERTA/CRÍTICO).
**Prueba:** migración aplica sin error.

### 2. `stakeholders/service.py` y `router.py` (protegido con `stakeholders.manage`)

- CRUD de stakeholders.
- CRUD de suscripciones (`sitio`/`sensor`/`nivel mínimo`).
**Prueba:** crear un stakeholder externo suscrito solo a nivel CRÍTICO del sitio "Mina Norte".



### 3. Resolver destinatarios por alerta (`stakeholders/service.py`)

- `get_recipients_for_alert(db, alert) -> list[Stakeholder]`: cruza `alert.sensor.site_id`/`sensor_id` y `alert.level` contra `stakeholder_subscriptions`.
**Prueba:** una alerta CRÍTICA en "Mina Norte" devuelve al stakeholder del paso 2; una alerta PRECAUCIÓN no lo incluye (porque su `min_level` es CRÍTICO).



### 4. Envío de notificaciones (`stakeholders/notifier.py`)

- Canal mínimo viable: **email** (SMTP configurable vía `.env`/Secret Manager).
- Función `send_alert_notification(stakeholder, alert) -> NotificationResult`.
- Registrar cada intento en `alert_notifications` (`status`: `enviado`/`fallido`, `error` si aplica).
- Diseñar la interfaz de forma que agregar un canal nuevo (SMS/WhatsApp) en el futuro no requiera tocar `alerts/service.py` (patrón estrategia: `channel -> handler`).
**Prueba:** con credenciales SMTP de prueba (ej. Mailtrap), disparar una alerta y confirmar la recepción del correo con nivel, sitio, sensor y recomendación.



### 5. Enganchar con el motor de alertas (Plan 05)

- En `alerts/service.py`, tras crear una alerta exitosamente, invocar `get_recipients_for_alert` + `send_alert_notification` para cada destinatario (idealmente en background/cola, no bloqueando la respuesta HTTP del ETL).
**Prueba:** flujo end-to-end: ingesta con lectura crítica → predicción → alerta → notificación enviada, todo verificable en las tablas correspondientes.



### 6. Portal de interesados (vista mínima, se refina en Plan 07)

- Vista de solo lectura para el rol `interesado`: alertas relevantes a sus suscripciones + estado de resolución.
**Prueba:** un usuario `interesado` ve únicamente las alertas de los sitios/sensores a los que su stakeholder está suscrito.



## Checklist de validación (Definition of Done)

- [ ] CRUD de stakeholders y suscripciones operativo y protegido por permisos.
- [ ] La resolución de destinatarios respeta sitio/sensor/nivel mínimo.
- [ ] El envío de notificaciones queda registrado (éxito o fallo) en `alert_notifications`.
- [ ] Agregar un nuevo canal de notificación no implica modificar el motor de alertas (verificado por diseño, no solo en teoría).
- [ ] Un usuario con rol `interesado` solo ve lo que le corresponde.

**Siguiente paso:** `07_DASHBOARD_UI.md`.<