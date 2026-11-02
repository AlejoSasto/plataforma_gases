# 19 — Usuarios, roles, inicio de sesión y acceso

**Objetivo:** un control de acceso claro para la empresa, seguro y con buena experiencia: roles con nombres comprensibles, alcance por zona, inicio de sesión robusto, recuperación de contraseña, invitaciones, verificación en dos pasos y pantallas de sala de control sin sesión personal.
**Prerrequisitos:** Plan 16 (M8).

---

## 1. Roles nuevos (nombre visible → código)

| Rol visible | Código | Para quién | Qué puede hacer |
|-------------|--------|------------|-----------------|
| **Administrador** | `admin` | TI de la empresa / equipo de tesis | Todo |
| **Supervisor de seguridad** | `supervisor_seguridad` | Jefe de seguridad y salud en el trabajo | Ver todo; gestionar avisos; definir límites; gestionar contactos; informes |
| **Operador de sala** | `operador` | Personal de la sala de control y supervisores de turno | Ver estado y avisos de sus zonas; marcar “Ya lo vi” y cerrar avisos |
| **Gerencia** | `gerencia` | Directivos | Resumen, confiabilidad e informes (solo lectura) |
| **Analista de datos** | `analista` | Ingeniería de datos | Cargar datos, calidad, Laboratorio, promover modelos |
| **Auditor** | `auditor` | Control interno / autoridad | Solo lectura de todo + bitácora |

Migración desde los roles actuales: `ingeniero_datos` → `analista`, `operador_mina` → `operador`, `interesado` → `gerencia`. Se crea `supervisor_seguridad`; `admin` y `auditor` no cambian. Script idempotente `scripts/migrate_roles_v2.py`.

## 2. Matriz de permisos

| Permiso | admin | supervisor | operador | gerencia | analista | auditor |
|---------|:-----:|:----------:|:--------:|:--------:|:--------:|:-------:|
| `status.view` (Hoy, zonas) | ✔ | ✔ | ✔ (sus zonas) | ✔ | ✔ | ✔ |
| `alerts.view` | ✔ | ✔ | ✔ (sus zonas) | ✔ | ✔ | ✔ |
| `alerts.acknowledge` | ✔ | ✔ | ✔ | | | |
| `alerts.resolve` | ✔ | ✔ | ✔ | | | |
| `history.view` | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| `reliability.view` | ✔ | ✔ | | ✔ | ✔ | ✔ |
| `reports.export` | ✔ | ✔ | | ✔ | ✔ | ✔ |
| `thresholds.manage` | ✔ | ✔ | | | | |
| `stakeholders.manage` | ✔ | ✔ | | | | |
| `data.upload` | ✔ | | | | ✔ | |
| `data.quality.view` | ✔ | | | | ✔ | ✔ |
| `models.train` | ✔ | | | | ✔ | |
| `models.promote` | ✔ | | | | ✔ | |
| `users.manage` | ✔ | | | | | |
| `roles.manage` | ✔ | | | | | |
| `kiosk.manage` | ✔ | ✔ | | | | |
| `audit.view` | ✔ | | | | | ✔ |

- **Alcance por zona** (`user_site_scopes`): el operador ve solo sus zonas. Sin filas asignadas = todas las zonas, pero solo para los roles distintos de operador; un operador sin zonas asignadas no ve nada y la UI se lo explica.
- La matriz vive en `scripts/seed_roles_permissions.py` y se prueba de forma **parametrizada** (cada celda es una prueba).
- Separación de funciones: quien entrena (`models.train`) no aprueba umbrales (`thresholds.manage`), salvo el admin.

## 3. Inicio de sesión (UX)

Pantalla `/ingresar`, en dos columnas en escritorio:
- **Izquierda:** marca, una frase (“Información a tiempo para trabajar seguros”) y el estado del sistema (“Funcionando · datos actualizados hace 1 min”), sin datos sensibles.
- **Derecha:** formulario con **Correo** y **Contraseña** (botón mostrar/ocultar), casilla “Mantener la sesión durante mi turno”, botón **Ingresar** y enlace “¿Olvidaste tu contraseña?”.

| Situación | Mensaje (natural, sin revelar si el correo existe) |
|-----------|----------------------------------------------------|
| Credenciales incorrectas | “El correo o la contraseña no coinciden. Revisa e intenta de nuevo.” |
| 5 intentos fallidos | “Por seguridad bloqueamos el acceso por 15 minutos. Si necesitas entrar ya, contacta al administrador.” |
| Cuenta desactivada | Mismo mensaje que credenciales incorrectas (no se revela el estado) |
| Debe cambiar la contraseña | Redirige a “Crea tu nueva contraseña” |
| Verificación en dos pasos | Paso 2: “Escribe el código de 6 dígitos de tu aplicación de autenticación” |

Flujos:
1. **Invitación:** el admin invita (correo + rol + zonas) → correo con enlace de un solo uso (72 h) → la persona crea su contraseña → entra. Ya no se crean contraseñas a mano.
2. **Recuperación:** “¿Olvidaste tu contraseña?” → correo → enlace de un solo uso (30 min, token con hash) → nueva contraseña → se cierran todas las sesiones. La respuesta es siempre la misma, exista o no el correo.
3. **Primer ingreso / reinicio por admin:** `must_change_password=true`.
4. **Dos pasos (TOTP):** obligatorio para `admin` y `analista`, opcional para el resto. Se activa en Mi cuenta con código QR más 8 códigos de respaldo de un solo uso (con hash).

Sin SMTP configurado (local), los correos se escriben en `storage/outbox/` y en el log, para poder probar los flujos.

## 4. Política de contraseñas y sesiones

- Contraseñas (guía NIST SP 800-63B): mínimo 12 caracteres, sin reglas de composición forzadas, con verificación contra una lista local de contraseñas comunes (`app/core/common_passwords.txt`, 10 000 entradas) y contra el nombre o correo del usuario. Medidor de fortaleza en lenguaje natural.
- Hash bcrypt (actual); se deja preparado `argon2id` como opción futura.
- **Acceso:** JWT de 15 min (antes 30). **Renovación:** 8 h, alineada al turno, con rotación en cada uso y detección de reutilización (si se reutiliza un token revocado, se revocan todas las sesiones del usuario).
- **Inactividad:** 30 min sin interacción → pantalla “¿Sigues ahí?”, y a los 60 s cierra la sesión. No aplica al kiosco.
- **Sesiones activas** visibles en Mi cuenta (dispositivo, IP aproximada, último uso) con “Cerrar esta sesión” y “Cerrar todas”.
- **CSRF:** como la autenticación es por cookie, se agrega un token CSRF *double-submit* en todos los POST, PATCH y DELETE de formularios y htmx (cabecera `X-CSRF-Token`).
- **Límite de intentos:** `slowapi` en `/auth/login`, recuperación e invitación (por IP y por correo).
- Cookies `HttpOnly`, `SameSite=Lax` y `Secure` en producción, más las cabeceras de seguridad (CSP con los CDN permitidos, `X-Frame-Options`, `Referrer-Policy`), dejando lo restante para el Plan 10.

## 5. Pantallas de sala de control (kiosco)

- El admin o el supervisor crea un **dispositivo** (“Pantalla sala principal”) con las zonas que muestra → se genera un enlace o código de emparejamiento de un solo uso.
- El dispositivo recibe un token de larga duración con hash en `kiosk_devices`: **solo lectura** de `/sala`, sin acceso a nada más.
- Revocable en cualquier momento; `last_seen_at` permite alertar si la pantalla se desconecta (“La pantalla de la sala no se actualiza desde hace 5 min”).

## 6. Gestión del equipo (pantalla P10)

- Tabla: nombre, correo, rol, zonas, último ingreso, estado (activo / invitado / bloqueado / desactivado).
- Acciones: invitar, cambiar rol, asignar zonas, reenviar invitación, desbloquear, forzar cambio de contraseña, desactivar (baja lógica). **No** se borran personas, para mantener la bitácora.
- Todo queda en la bitácora con frases naturales: “Carlos invitó a Ana como Operadora de sala (zonas: Frente 3)”.

## 7. Auditoría (acciones nuevas)

`auth.login_ok`, `auth.login_fail`, `auth.locked`, `auth.logout`, `auth.password_reset_requested`, `auth.password_reset_done`, `auth.totp_enabled`, `auth.session_revoked`, `user.invited`, `user.invitation_accepted`, `user.role_changed`, `user.scope_changed`, `user.unlocked`, `kiosk.created`, `kiosk.revoked`, `threshold.changed`.

## 8. Fases

| Fase | Contenido | Definición de terminado |
|------|-----------|-------------------------|
| F1 | Roles v2, matriz, migración de roles, alcance por zona en los repositorios (filtro central `scoped_sites(user)`) | Matriz parametrizada en verde; un operador no ve zonas ajenas ni por API |
| F2 | Login nuevo, bloqueo, límite de intentos, CSRF, sesiones de 15 min / 8 h, rotación y reutilización | Pruebas de bloqueo, reutilización y CSRF |
| F3 | Invitaciones, recuperación, cambio forzado, outbox | Pruebas E2E de cada flujo |
| F4 | TOTP + códigos de respaldo | Pruebas con reloj simulado |
| F5 | Kiosco | `/sala` accesible solo con token de dispositivo; revocación inmediata |
| F6 | Pantallas Equipo y Mi cuenta, más la bitácora en frases | Pruebas de UI por rol |

---

## Definición de terminado del Plan 19
- [x] Seis roles con nombres visibles en español y matriz probada celda por celda.
- [x] Alcance por zona aplicado en API y HTML.
- [x] Login con bloqueo, límite de intentos, CSRF y rotación con detección de reutilización.
- [x] Invitación, recuperación y dos pasos operativos (con outbox en local).
- [x] Kiosco seguro y revocable.
- [x] Mensajes de acceso en lenguaje natural que no revelan si una cuenta existe.
- [x] `python scripts/verify.py --plan 19` en verde.
