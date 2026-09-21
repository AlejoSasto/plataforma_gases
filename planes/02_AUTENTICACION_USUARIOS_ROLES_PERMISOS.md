# Plan 02 — Autenticación, Usuarios, Roles y Permisos (F1)

## Objetivo
Login funcional con JWT, CRUD de usuarios, y un sistema RBAC (roles + permisos granulares) reutilizable por `require_permission("codigo")` en cualquier router futuro.

## Prerrequisitos
- Plan 01 validado (DB, Alembic, estructura de módulos funcionando).

## Paso a paso

### 1. Modelos (`app/modules/users/models.py`, `roles_permissions/models.py`)
Tablas:
```
users(id, email UNIQUE, password_hash, full_name, is_active, created_at, updated_at)
roles(id, name UNIQUE, description)
permissions(id, code UNIQUE, description)
role_permissions(role_id FK, permission_id FK, PK compuesta)
user_roles(user_id FK, role_id FK, PK compuesta)
refresh_tokens(id, user_id FK, token_hash, expires_at, revoked_at)
```
**Prueba:** `alembic revision --autogenerate -m "auth_users_roles"` genera las 6 tablas; `alembic upgrade head` las crea en `proyecto_gases`.

### 2. Seed inicial (`scripts/seed_roles_permissions.py`)
- Crear permisos base: `users.manage`, `roles.manage`, `sensors.manage`, `models.train`, `models.promote`, `predictions.view`, `alerts.view`, `alerts.resolve`, `stakeholders.manage`, `reports.export`, `dashboard.view_all_sites`.
- Crear roles: `admin` (todos los permisos), `ingeniero_datos` (sensors, models, predictions, alerts.view), `operador_mina` (alerts.view, alerts.resolve, predictions.view), `interesado` (alerts.view, reports.export limitado), `auditor` (solo lectura).
- Crear un superusuario inicial (`scripts/create_superadmin.py`) pidiendo email/password por variable de entorno, nunca hardcodeado.
**Prueba:** tras correr el script, `SELECT * FROM roles;` muestra 5 roles; login con el superadmin funciona (ver paso 6).

### 3. Seguridad (`app/core/security.py`, completar)
- `hash_password(raw) -> str` (bcrypt).
- `verify_password(raw, hashed) -> bool`.
- `create_access_token(user_id, roles, permissions) -> str` (exp corto, `ACCESS_TOKEN_EXPIRE_MINUTES`).
- `create_refresh_token(user_id) -> str` (exp largo, `REFRESH_TOKEN_EXPIRE_DAYS`), y guardar su hash en `refresh_tokens`.
- `decode_access_token(token) -> payload | None`.
**Prueba:** unit test que crea un token y lo decodifica, verificando `user_id` y `permissions` presentes.

### 4. Dependencias de autorización (`app/shared/dependencies.py`)
- `get_current_user(request, db) -> User`: lee cookie httpOnly `access_token`, decodifica, carga usuario.
- `require_permission(code: str)`: factory de dependencia que valida que `code` esté en los permisos del usuario actual; si no, lanza `PermissionDeniedError` (403).
**Prueba:** endpoint de prueba protegido con `require_permission("users.manage")` responde 403 a un usuario sin ese permiso y 200 al admin.

### 5. `modules/auth/router.py`
Endpoints:
- `POST /auth/login` — recibe `email`/`password` (`OAuth2PasswordRequestForm` o JSON propio), valida, setea cookies httpOnly `access_token` y `refresh_token`, responde datos básicos del usuario.
- `POST /auth/refresh` — valida refresh token contra `refresh_tokens`, emite nuevo access token.
- `POST /auth/logout` — revoca refresh token, borra cookies.
- `GET /auth/me` — retorna usuario + roles + permisos actuales (para que el frontend arme el menú).
**Prueba:** flujo completo con `httpx.Client` en test de integración: login → `/auth/me` devuelve 200 → logout → `/auth/me` devuelve 401.

### 6. `modules/users/router.py` (protegido con `users.manage`)
- `GET /users` (paginado), `POST /users`, `GET /users/{id}`, `PATCH /users/{id}`, `DELETE /users/{id}` (soft delete vía `is_active=false`).
- `POST /users/{id}/roles` — asignar/quitar roles.
**Prueba:** admin crea un usuario, le asigna rol `operador_mina`, ese usuario hace login y `/auth/me` refleja el rol y sus permisos.

### 7. `modules/roles_permissions/router.py` (protegido con `roles.manage`)
- `GET /roles`, `POST /roles`, `PATCH /roles/{id}` (asignar/quitar permisos).
- `GET /permissions` (catálogo, solo lectura).
**Prueba:** crear un rol nuevo con un subconjunto de permisos y confirmar que un usuario con ese rol solo accede a los endpoints permitidos.

### 8. Vistas mínimas (Jinja2) — placeholder hasta Plan 07
- `templates/auth/login.html` — formulario simple Bootstrap5 (aún sin theme final).
- Ruta `GET /login` en `dashboard/router.py` (o en `auth/router.py`) que renderiza el formulario y hace POST a `/auth/login` vía fetch.
**Prueba:** navegar a `/login`, autenticarse, ser redirigido a `/` sin error.

### 9. Auditoría básica (`modules/audit/`)
- Middleware o dependencia que registra en `audit_log` cada login, logout, creación/edición de usuario y cambio de rol.
**Prueba:** tras un login y una edición de usuario, `SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 5;` muestra ambos eventos con `user_id` correcto.

## Checklist de validación (Definition of Done)
- [ ] Login/logout/refresh funcionan de extremo a extremo (test de integración).
- [ ] `require_permission` bloquea correctamente accesos no autorizados (403) y permite los autorizados (200).
- [ ] Los 5 roles base y sus permisos existen en la base tras el seed.
- [ ] CRUD de usuarios y asignación de roles operativo solo para `admin`.
- [ ] `audit_log` registra login y cambios de usuario/rol.
- [ ] Contraseñas nunca se guardan en texto plano (verificar columna `password_hash`).

**Siguiente paso:** `03_INGESTA_ETL_SENSORES.md`.
