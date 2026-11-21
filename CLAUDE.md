# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

**Vigía** — A thesis platform for real-time gas monitoring and forecasting in Colombian underground mining. FastAPI monolith + Jinja2 (server-rendered, no SPA) + PostgreSQL + ensemble ML forecasting. Regulated by Decreto 1886 (Colombian mining decree).

## Commands

### Local Development
```bash
# Start dev server (auto-reload)
uvicorn app.main:app --reload

# Docker stack (PostgreSQL + MLflow + app)
docker compose up -d --build
# App at http://localhost:8000/ingresar
# Default dev credentials: admin@vigia.local / (SUPERADMIN_PASSWORD from .env)
```

### Database & Setup (first time)
```bash
alembic upgrade head
python scripts/seed_roles_permissions.py
python scripts/seed_catalog.py
python scripts/create_superadmin.py
# Load real data:
python scripts/load_processed_dataset.py --consolidado
```

### Testing
```bash
# Run all fast tests (no slow ML, no E2E, no live LLM)
python scripts/verify.py --fast
# or: make verify-fast

# Run full test suite
python scripts/verify.py --full

# Run tests for a specific plan
python scripts/verify.py --plan 20

# Direct pytest by marker
pytest -m plan19
pytest -m "plan20 and not slow"

# Single test file
pytest tests/unit/test_something.py -v
```

### Linting & Type Checking
```bash
ruff check .
ruff format .
mypy app/
```

## Architecture

### Module Structure
All features live in `app/modules/<name>/` with consistent layout: `models.py`, `schemas.py`, `service.py`, `router.py`. The `app/main.py` registers 11 routers at startup.

**Key modules:** `auth`, `users`, `roles_permissions`, `sensors_ingestion` (ETL), `forecasting`, `alerts`, `catalog`, `dashboard`, `reports`, `audit`, `assistant` (optional, Plan 26).

### ML / Forecasting
Forecast models live in `ml_core/forecasting/adapters/`. Ensemble over Persistence, ETS, LightGBM, LSTM, TFT, Chronos, TimesFM — predicts gas concentration at 6/12/18 min with conformal quantiles. Tracking via MLflow.

### Frontend
Server-rendered Jinja2. No Bootstrap, no CDN resources — everything is local. Design system defined in `app/static/css/tokens.css` (Plan 21). ECharts 5 for charts, Lucide sprite for icons, htmx for interactivity.

### Startup Sequence
`app/main.py` → hydrate gas catalog → rebuild assistant index → start ETL inbox scheduler → start forecast scheduler.

## Critical Conventions

### UI Text
**All user-facing text must come from `app/shared/copy.py`.** No inline strings in templates. The UI targets non-technical operators and mine managers — forbidden terms: `modelo`, `algoritmo`, `predicción`, `probabilidad`, `ML`, `IA`, `recall`, `precision`. Use natural equivalents: "pronóstico" → "lo que viene", "probabilidad" → "posibilidad alta/media/baja". Exception: `laboratorio/` section may use technical language.

### CSS / Design Tokens
Use **only** `--token-variable` names from `tokens.css`. Never hardcode colors, spacing, or radii. Status colors (`--st-*`) are exclusively for gas alert states (Normal / Vigilar / Actuar ya / Evacuar / Sin datos) — never for decoration.

### Database Migrations
**Never call `Base.metadata.create_all()`**. Always use Alembic migrations. Dev DB: `proyecto_gases` (port 5433 via compose). Test DB: `proyecto_gases_test`.

### Commits
Follow `feat(module): plan.phase.step description` format. Example: `feat(forecasting): 17.3.2 add TFT adapter`.

## Configuration

Copy `.env.example` to `.env`. Key variables:
- `DATABASE_URL` / `TEST_DATABASE_URL` — PostgreSQL
- `JWT_SECRET` — Auth
- `MLFLOW_TRACKING_URI` — http://localhost:5000
- `ASSISTANT_PROVIDER` — `gemini` / `ollama` / `off` (default: `off`; assistant hidden when off)
- `NOTIFICATIONS_DRY_RUN=true` — Prevents real SMTP/WhatsApp in dev

## Test Markers (pytest.ini)

| Marker | Scope |
|--------|-------|
| `plan15`–`plan26` | Feature-plan aligned tests |
| `e2e` | Playwright end-to-end |
| `slow` | Heavy ML tests |
| `live_llm` | Real LLM API calls |

## Key Reference Files

- `planes/CONTEXTO_SISTEMA.md` — Canonical system state audit (source of truth for plan status)
- `planes/21_SISTEMA_DE_DISENO_VIGIA.md` — Full design system spec
- `.cursor/rules/vigia-ui.mdc` — UI/CSS rules
- `.cursor/rules/vigia-lenguaje.mdc` — Copy/language rules
- `.cursor/rules/vigia-graficos.mdc` — Chart rules
- `documentacion/claude/` — Thesis documentation suite (architecture, data model, AI design, user manual)
