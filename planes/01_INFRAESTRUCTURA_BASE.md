# Plan 01 — Infraestructura Base (F0)

## Objetivo
Dejar un esqueleto de proyecto ejecutable: FastAPI arrancando, PostgreSQL conectado, migraciones funcionando, Docker Compose levantando todo, y las convenciones que usarán TODOS los módulos posteriores.

## Prerrequisitos
- Docker y Docker Compose instalados.
- PostgreSQL local disponible (ya tienes uno: db `proyecto_gases`, host `localhost`, puerto `5432`, usuario `postgres`) o se levanta vía Compose.
- Python 3.11+.

## Paso a paso

### 1. Crear estructura de carpetas
```
plataforma-gases/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── security.py
│   │   └── logging.py
│   ├── modules/
│   ├── templates/
│   ├── static/{css,js,img}/
│   └── shared/
│       ├── __init__.py
│       ├── exceptions.py
│       ├── dependencies.py
│       └── pagination.py
├── ml_core/
├── migrations/
├── tests/{unit,integration}/
├── scripts/
├── docker/
├── docker-compose.yml
├── .env.example
├── alembic.ini
├── requirements.txt
└── pyproject.toml   # (opcional: black/ruff config)
```
**Prueba:** `tree -L 3 plataforma-gases` muestra la estructura anterior.

### 2. Definir dependencias (`requirements.txt`)
Incluir como mínimo: `fastapi`, `uvicorn[standard]`, `gunicorn`, `sqlalchemy>=2`, `alembic`, `psycopg[binary]`, `pydantic>=2`, `pydantic-settings`, `python-jose[cryptography]`, `passlib[bcrypt]`, `python-multipart`, `jinja2`, `httpx`, `pytest`.
**Prueba:** `pip install -r requirements.txt` sin errores en un venv limpio.

### 3. `app/core/config.py` — configuración centralizada
- Clase `Settings(BaseSettings)` con: `database_url`, `jwt_secret`, `jwt_algorithm`, `access_token_expire_minutes`, `refresh_token_expire_days`, `environment` (`local`/`prod`), `mlflow_tracking_uri`, `gcs_bucket` (opcional en local).
- Cargar desde `.env` con `model_config = SettingsConfigDict(env_file=".env")`.
- Exponer un singleton `settings = Settings()`.
**Prueba:** `python -c "from app.core.config import settings; print(settings.database_url)"` imprime la URL esperada.

### 4. `.env.example` y `.env` local
```
DATABASE_URL=postgresql+psycopg://postgres:${DB_PASSWORD}@localhost:5432/proyecto_gases
JWT_SECRET=cámbiame-en-produccion
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ENVIRONMENT=local
MLFLOW_TRACKING_URI=http://localhost:5000
```
`DB_PASSWORD` se define como variable de entorno del sistema o en un `.env` que **no** se versiona (`.gitignore` debe incluir `.env`).
**Prueba:** `.env` está en `.gitignore`; `git status` no lo muestra como archivo nuevo trackeable.

### 5. `app/core/database.py`
- `engine = create_engine(settings.database_url, pool_pre_ping=True)`.
- `SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)`.
- `class Base(DeclarativeBase): pass`.
- Dependencia `get_db()` (generador que abre/cierra sesión).
**Prueba:** un script `scripts/check_db.py` que hace `SELECT 1` y confirma conexión contra `proyecto_gases`.

### 6. Inicializar Alembic
- `alembic init migrations`.
- Editar `migrations/env.py` para importar `Base` y usar `settings.database_url` (no hardcodear).
- Configurar `target_metadata = Base.metadata`.
**Prueba:** `alembic revision --autogenerate -m "init"` genera un archivo vacío (aún no hay modelos) sin errores de conexión.

### 7. `app/core/security.py` (esqueleto, se completa en Plan 02)
- Funciones `hash_password`, `verify_password` (passlib/bcrypt).
- Placeholder de `create_access_token` / `decode_token` (se implementan a fondo en Plan 02).

### 8. `app/core/logging.py`
- Configurar logging en JSON estructurado (nivel desde `settings.environment`: `DEBUG` en local, `INFO` en prod).

### 9. `app/main.py`
- Instanciar `FastAPI(title="Plataforma Gases", version="0.1.0")`.
- Montar `/static` con `StaticFiles`.
- Configurar `Jinja2Templates(directory="app/templates")`.
- Endpoint `GET /health` → `{"status": "ok"}` (usado por Cloud Run y Compose healthcheck).
- Placeholder de `app.include_router(...)` (se irá llenando en cada plan siguiente).
**Prueba:** `uvicorn app.main:app --reload` y `curl localhost:8000/health` responde `200 {"status":"ok"}`.

### 10. Dockerfiles
- `docker/Dockerfile.app`: imagen `python:3.11-slim`, instala `requirements.txt`, copia `app/` y `ml_core/`, comando `gunicorn -k uvicorn.workers.UvicornWorker app.main:app`.
- `docker/Dockerfile.worker`: mismo base, usado luego por Celery (Plan 03/04).
**Prueba:** `docker build -f docker/Dockerfile.app -t plataforma-gases-app .` construye sin error.

### 11. `docker-compose.yml`
Servicios mínimos en esta fase: `app`, `db` (postgres:15, volumen `pgdata`, variables desde `.env`).
```yaml
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: proyecto_gases
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]
  app:
    build: { context: ., dockerfile: docker/Dockerfile.app }
    env_file: .env
    depends_on: [db]
    ports: ["8000:8000"]
volumes:
  pgdata:
```
**Prueba:** `docker compose up -d db app` y `curl localhost:8000/health` responde OK; `docker compose logs app` sin tracebacks.

### 12. Convenciones de módulo (aplican desde Plan 02 en adelante)
Cada carpeta `app/modules/<dominio>/` tendrá:
- `models.py` — clases SQLAlchemy (heredan de `Base`).
- `schemas.py` — Pydantic (`XCreate`, `XUpdate`, `XRead`).
- `repository.py` — funciones de acceso a datos (sin lógica de negocio).
- `service.py` — lógica de negocio, orquesta repository(s).
- `router.py` — endpoints FastAPI, delgados, llaman a `service.py`.
- Registro: en `app/main.py`, `app.include_router(modulo.router.router, prefix="/modulo", tags=["modulo"])`.

### 13. Manejo de errores global (`app/shared/exceptions.py`)
- Definir excepciones de dominio (`NotFoundError`, `PermissionDeniedError`, `ValidationError`).
- Registrar `@app.exception_handler(...)` en `main.py` para devolver JSON consistente: `{"error": "codigo", "message": "..."}`.
**Prueba:** un endpoint de ejemplo que lanza `NotFoundError` devuelve `404` con ese formato.

## Checklist de validación (Definition of Done)
- [ ] `docker compose up` levanta `db` y `app` sin errores.
- [ ] `GET /health` responde 200 dentro y fuera de Docker.
- [ ] `alembic upgrade head` corre sin fallos contra la base local.
- [ ] `.env` fuera de git; `.env.example` sí versionado.
- [ ] Estructura de carpetas coincide con la definida en el paso 1.
- [ ] Excepciones de dominio devuelven JSON consistente.

**Siguiente paso:** `02_AUTENTICACION_USUARIOS_ROLES_PERMISOS.md`.
