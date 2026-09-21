from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.logging import setup_logging
from app.modules.alerts.router import router as alerts_router
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.dashboard.api_router import router as dashboard_api_router
from app.modules.dashboard.ui_router import router as ui_router
from app.modules.ml_training.router import router as ml_router
from app.modules.predictions.router import router as predictions_router
from app.modules.predictions.scheduler import (
    shutdown_prediction_scheduler,
    start_prediction_scheduler,
)
from app.modules.reports.router import router as reports_router
from app.modules.roles_permissions.router import router as roles_router
from app.modules.sensors_ingestion.router import router as ingestion_router
from app.modules.sensors_ingestion.scheduler import (
    shutdown_inbox_scheduler,
    start_inbox_scheduler,
)
from app.modules.stakeholders.router import router as stakeholders_router
from app.modules.users.router import router as users_router
from app.shared.exceptions import AppError, NotFoundError, UnauthorizedError

setup_logging()

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Plataforma Gases", version="0.1.0")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(auth_router)
app.include_router(ui_router)
app.include_router(dashboard_api_router)
app.include_router(users_router)
app.include_router(roles_router)
app.include_router(ingestion_router)
app.include_router(ml_router)
app.include_router(predictions_router)
app.include_router(alerts_router)
app.include_router(stakeholders_router)
app.include_router(audit_router)
app.include_router(reports_router)


@app.on_event("startup")
def _startup() -> None:
    start_inbox_scheduler()
    start_prediction_scheduler()


@app.on_event("shutdown")
def _shutdown() -> None:
    shutdown_inbox_scheduler()
    shutdown_prediction_scheduler()


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse | RedirectResponse | HTMLResponse:
    accept = request.headers.get("accept", "")
    wants_html = "text/html" in accept and "application/json" not in accept.split(",")[0]
    if wants_html:
        if isinstance(exc, UnauthorizedError):
            return RedirectResponse("/login", status_code=302)
        if exc.status_code == 403:
            return templates.TemplateResponse(
                request,
                "errors/403.html",
                {"title": "Acceso denegado", "message": exc.message, "current_user": None},
                status_code=403,
            )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.code, "message": exc.message},
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/_demo/not-found")
def demo_not_found() -> None:
    """Endpoint de prueba del handler de excepciones (Plan 01)."""
    raise NotFoundError("Recurso de demostración no encontrado")


@app.get("/interesado/alertas")
def interesado_alertas_redirect() -> RedirectResponse:
    """Compatibilidad Plan 06 → resumen ejecutivo Plan 07/11."""
    return RedirectResponse("/executive", status_code=302)
