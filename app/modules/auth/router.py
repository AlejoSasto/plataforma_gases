"""Router de autenticación y vista de login."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, EmailStr, Field

from app.core.csrf import CSRF_COOKIE, new_token
from app.core.security import REFRESH_COOKIE
from app.modules.auth import kiosk as kiosk_svc
from app.modules.auth import service as auth_service
from app.modules.auth.schemas import LoginRequest, UserMeResponse
from app.shared.dependencies import CurrentUser, DbSession, get_current_user, require_permission
from app.shared.exceptions import AppError, UnauthorizedError
from app.shared.templating import make_templates

router = APIRouter(tags=["auth"])
templates = make_templates()
CanKiosk = Annotated[object, Depends(require_permission("kiosk.manage"))]
CanUsers = Annotated[object, Depends(require_permission("users.manage"))]


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


def _csrf_for(request: Request) -> str:
    return request.cookies.get(CSRF_COOKIE) or new_token()


def _login_context(token: str, *, error: str | None = None, show_totp: bool = False) -> dict:
    return {
        "title": "Ingresar",
        "current_user": None,
        "sala": False,
        "permissions": set(),
        "roles": set(),
        "csrf_token": token,
        "error": error or "",
        "show_totp": show_totp,
        "auth_page": True,
    }


def _login_html(request: Request, *, error: str | None = None, show_totp: bool = False, status_code: int = 200) -> HTMLResponse:
    token = _csrf_for(request)
    response = templates.TemplateResponse(
        request,
        "auth/login.html",
        _login_context(token, error=error, show_totp=show_totp),
        status_code=status_code,
    )
    response.set_cookie(CSRF_COOKIE, token, httponly=False, samesite="lax", path="/")
    return response


@router.get("/ingresar", response_class=HTMLResponse, response_model=None)
def login_page(request: Request) -> HTMLResponse | RedirectResponse:
    if "email" in request.query_params or "password" in request.query_params:
        return RedirectResponse("/ingresar", status_code=302)
    return _login_html(request)


@router.post("/ingresar", response_class=HTMLResponse, response_model=None)
def login_page_post(
    request: Request,
    db: DbSession,
    email: str = Form(""),
    password: str = Form(""),
    totp: str = Form(""),
    keep: Optional[str] = Form(None),
) -> HTMLResponse | RedirectResponse:
    ip, ua = _client_meta(request)
    holder = Response()
    try:
        user = auth_service.login(
            db,
            email=email,
            password=password,
            response=holder,
            totp_code=totp or None,
            ip=ip,
            user_agent=ua,
        )
    except AppError as exc:
        show_totp = "6 dígitos" in exc.message.lower()
        return _login_html(request, error=exc.message, show_totp=show_totp, status_code=exc.status_code)
    dest = RedirectResponse("/mi-cuenta" if user.must_change_password else "/", status_code=303)
    for cookie in holder.headers.getlist("set-cookie"):
        dest.headers.append("set-cookie", cookie)
    _ = keep
    return dest


@router.get("/login")
def login_legacy() -> RedirectResponse:
    return RedirectResponse("/ingresar", status_code=301)


@router.post("/auth/login", response_model=UserMeResponse)
def login(body: LoginRequest, response: Response, request: Request, db: DbSession) -> UserMeResponse:
    ip, ua = _client_meta(request)
    user = auth_service.login(
        db,
        email=body.email,
        password=body.password,
        response=response,
        totp_code=body.totp_code,
        ip=ip,
        user_agent=ua,
    )
    return UserMeResponse(**auth_service.user_to_me(user))


@router.post("/auth/refresh", response_model=UserMeResponse)
def refresh(request: Request, response: Response, db: DbSession) -> UserMeResponse:
    raw = request.cookies.get(REFRESH_COOKIE)
    ip, ua = _client_meta(request)
    user = auth_service.refresh(db, refresh_raw=raw, response=response, ip=ip, user_agent=ua)
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


class ResetRequest(BaseModel):
    email: EmailStr


class ResetComplete(BaseModel):
    token: str
    password: str = Field(min_length=12)


@router.post("/auth/recuperar")
def pedir_recuperacion(body: ResetRequest, db: DbSession) -> dict[str, str]:
    auth_service.request_password_reset(db, email=body.email)
    return {"status": "ok", "message": "Si el correo está en el sistema, recibirás un enlace."}


@router.post("/auth/recuperar/confirmar")
def confirmar_recuperacion(body: ResetComplete, db: DbSession) -> dict[str, str]:
    auth_service.complete_password_reset(db, token=body.token, new_password=body.password)
    return {"status": "ok"}


class InviteBody(BaseModel):
    email: EmailStr
    full_name: str
    role_ids: list[int]
    site_ids: list[int] = []


@router.post("/auth/invitar")
def invitar(body: InviteBody, db: DbSession, actor: CurrentUser, _: CanUsers) -> dict:
    inv = auth_service.invite_user(
        db, actor=actor, email=body.email, full_name=body.full_name, role_ids=body.role_ids, site_ids=body.site_ids
    )
    out = {"email": inv.email, "expires_at": inv.expires_at.isoformat()}
    token = getattr(inv, "_plain_token", None)
    if token:
        out["token"] = token
    return out


class AcceptInvite(BaseModel):
    token: str
    password: str = Field(min_length=12)


@router.post("/auth/invitar/aceptar", response_model=UserMeResponse)
def aceptar_invitacion(body: AcceptInvite, response: Response, db: DbSession) -> UserMeResponse:
    user = auth_service.accept_invitation(db, token=body.token, password=body.password, response=response)
    return UserMeResponse(**auth_service.user_to_me(user))


class TotpConfirm(BaseModel):
    secret: str
    code: str


@router.post("/auth/totp/iniciar")
def totp_iniciar(user: CurrentUser) -> dict[str, str]:
    return auth_service.begin_totp(user)


@router.post("/auth/totp/activar")
def totp_activar(body: TotpConfirm, db: DbSession, user: CurrentUser) -> dict:
    codes = auth_service.enable_totp(db, user=user, secret=body.secret, code=body.code)
    return {"backup_codes": codes}


@router.get("/auth/sesiones")
def listar_sesiones(db: DbSession, user: CurrentUser) -> dict:
    from app.modules.auth import repository as auth_repo
    from app.shared.formatting import format_datetime_short

    rows = auth_repo.list_sessions(db, user.id)
    return {
        "items": [
            {
                "id": r.id,
                "user_agent": r.user_agent,
                "ip": r.ip,
                "last_used_at": format_datetime_short(r.last_used_at),
                "revoked": r.revoked_at is not None,
            }
            for r in rows
        ]
    }


@router.post("/auth/sesiones/{session_id}/cerrar")
def cerrar_sesion(session_id: int, db: DbSession, user: CurrentUser) -> dict[str, int]:
    n = auth_service.revoke_session(db, user=user, session_id=session_id)
    return {"closed": n}


@router.post("/auth/sesiones/cerrar-todas")
def cerrar_todas(db: DbSession, user: CurrentUser, response: Response) -> dict[str, int]:
    n = auth_service.revoke_session(db, user=user, all_sessions=True)
    auth_service.logout(db, user=user, refresh_raw=None, response=response)
    return {"closed": n}


class KioskCreate(BaseModel):
    name: str
    site_ids: list[int] = []


@router.post("/auth/kioscos")
def crear_kiosco(body: KioskCreate, db: DbSession, actor: CurrentUser, _: CanKiosk) -> dict:
    row, raw = kiosk_svc.create_device(db, actor=actor, name=body.name, site_ids=body.site_ids)
    return {"id": row.id, "name": row.name, "token": raw, "pair_url": f"/sala?kiosk={raw}"}


@router.get("/auth/kioscos")
def listar_kioscos(db: DbSession, _: CanKiosk) -> dict:
    rows = kiosk_svc.list_devices(db)
    return {
        "items": [
            {
                "id": r.id,
                "name": r.name,
                "revoked": r.revoked_at is not None,
                "last_seen_at": r.last_seen_at.isoformat() if r.last_seen_at else None,
            }
            for r in rows
        ]
    }


@router.post("/auth/kioscos/{device_id}/revocar")
def revocar_kiosco(device_id: int, db: DbSession, actor: CurrentUser, _: CanKiosk) -> dict:
    row = kiosk_svc.revoke_device(db, actor=actor, device_id=device_id)
    return {"id": row.id, "revoked": True}


@router.get("/recuperar", response_class=HTMLResponse)
def recuperar_page(request: Request, token: str | None = None) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "auth/recuperar.html", {"title": "Recuperar contraseña", "token": token or ""}
    )


@router.get("/invitar", response_class=HTMLResponse)
def invitar_page(request: Request, token: str | None = None) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "auth/invitar.html", {"title": "Crea tu contraseña", "token": token or ""}
    )
