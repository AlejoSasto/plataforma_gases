"""Router de autenticación y vista de login."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.security import REFRESH_COOKIE
from app.modules.auth import service as auth_service
from app.modules.auth.schemas import LoginRequest, UserMeResponse
from app.shared.dependencies import CurrentUser, DbSession, get_current_user
from app.shared.exceptions import UnauthorizedError

router = APIRouter(tags=["auth"])

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "auth/login.html", {})


@router.post("/auth/login", response_model=UserMeResponse)
def login(body: LoginRequest, response: Response, db: DbSession) -> UserMeResponse:
    user = auth_service.login(db, email=body.email, password=body.password, response=response)
    return UserMeResponse(**auth_service.user_to_me(user))


@router.post("/auth/refresh", response_model=UserMeResponse)
def refresh(request: Request, response: Response, db: DbSession) -> UserMeResponse:
    raw = request.cookies.get(REFRESH_COOKIE)
    user = auth_service.refresh(db, refresh_raw=raw, response=response)
    return UserMeResponse(**auth_service.user_to_me(user))


@router.post("/auth/logout")
def logout(
    request: Request,
    response: Response,
    db: DbSession,
) -> dict[str, str]:
    raw = request.cookies.get(REFRESH_COOKIE)
    user = None
    try:
        user = get_current_user(request, db)
    except UnauthorizedError:
        pass
    auth_service.logout(db, user=user, refresh_raw=raw, response=response)
    return {"status": "ok"}


@router.get("/auth/me", response_model=UserMeResponse)
def me(user: CurrentUser) -> UserMeResponse:
    return UserMeResponse(**auth_service.user_to_me(user))
