# Vigía — Plataforma de monitoreo y predicción de gases

Monolito FastAPI + Jinja2 + PostgreSQL (tesis). En la UI la marca de trabajo es **Vigía · Gases en la mina**.

Documentación canónica:

| Documento | Contenido |
|-----------|-----------|
| [`planes/CONTEXTO_SISTEMA.md`](planes/CONTEXTO_SISTEMA.md) | Estado real del código |
| [`planes/00_INDICE_Y_ROADMAP.md`](planes/00_INDICE_Y_ROADMAP.md) | Mapa y compuertas 14–22 |
| [`planes/21_SISTEMA_DE_DISENO_VIGIA.md`](planes/21_SISTEMA_DE_DISENO_VIGIA.md) | Identidad visual |
| [`planes/BITACORA_BUCLE.md`](planes/BITACORA_BUCLE.md) | Bitácora de ejecución |

## Requisitos

- Python 3.11+
- Docker / Docker Compose

## Arranque con Docker (recomendado)

```bash
copy .env.example .env
docker compose up -d --build
curl http://localhost:8000/health
# UI: http://localhost:8000/ingresar
```

| Servicio | Puerto host |
|----------|-------------|
| App | 8000 |
| Postgres | 5433 |
| MLflow | 5000 |

Tras cambiar código Python montado: `docker compose restart app` (Gunicorn no recarga solo).

### Acceso en desarrollo

Credenciales locales (solo DEV):

- Correo: `admin@vigia.local`
- Contraseña: `AdminPass123!`
- Entrada: http://localhost:8000/ingresar

Si no existen: `python scripts/create_superadmin.py` (usa `SUPERADMIN_*` de `.env`).  
`python scripts/audit_demo_data.py` debe salir limpio (sin `@example.com`).

## Arranque local (app en el host)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env

docker compose up -d db
alembic upgrade head
python scripts/seed_roles_permissions.py
python scripts/seed_catalog.py
python scripts/create_superadmin.py

python scripts/load_processed_dataset.py --consolidado   # solo datos reales

uvicorn app.main:app --reload
```

`DATABASE_URL` en el host usa `localhost:5433`. Dentro de Compose, la app habla con `db:5432`.

## Verificación

```bash
python scripts/verify.py --plan 18
python scripts/verify.py --plan 19
python scripts/verify.py --fast
# E2E (app en :8000):
python -m pytest -q tests/e2e/test_login_playwright.py tests/e2e/test_aceptacion_tareas.py
```

DB de pruebas: `proyecto_gases_test` (`TEST_DATABASE_URL`). Nunca apunta a la DB de desarrollo.

## Estado de planes (resumen)

- **01–08, 11–13:** base / historial (varios supersedidos por 15–20).
- **15–20:** implementados en código (G0 6/12/18 min; Alembic `c1d2e3f4a5b6`).
- **21–22:** sistema de diseño Vigía aplicado (tokens, riel, login SVG, sin CDN).
- **Login seguro:** `POST /ingresar`, CSRF, sin clave en la URL.
- **09 / resto de 10:** pendientes (despliegue edge-first; k6, HSTS prod, …).
- **Humano:** visto G0 del director; sesiones SUS en mina.

## Convenciones

- Módulos en `app/modules/<nombre>/` (`models`, `schemas`, `service`, `router`, …).
- UI: solo tokens Vigía; recursos locales; textos desde `app/shared/copy.py`.
- Commits sugeridos: `feat(<módulo>): <plan>.<fase>.<paso> <descripción>`.

Mockups navegables:

```bash
python -m http.server 8765 --directory mockups/vigia-design-kit/mockups
```
