"""CSRF double-submit (cookie csrf_token + cabecera X-CSRF-Token o campo de formulario).

ASGI puro: BaseHTTPMiddleware consume el cuerpo y deja el POST nativo vacío.
"""

from __future__ import annotations

import secrets
from urllib.parse import parse_qs

from starlette.datastructures import MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"
SAFE = {"GET", "HEAD", "OPTIONS", "TRACE"}
SKIP_PATHS = {"/health", "/_demo/not-found"}
AUTH_PATHS = frozenset({"/ingresar", "/login", "/recuperar", "/invitar"})


def new_token() -> str:
    return secrets.token_urlsafe(32)


def apply_auth_headers(request: Request, response: Response) -> None:
    if request.url.path not in AUTH_PATHS:
        return
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"


def _header_from_scope(scope: Scope, name: bytes) -> str:
    for key, value in scope.get("headers") or []:
        if key == name:
            return value.decode("latin-1")
    return ""


def _csrf_fail(scope: Scope, receive: Receive, send: Send):
    accept = _header_from_scope(scope, b"accept")
    first = accept.split(",")[0] if accept else ""
    if "text/html" in accept and "application/json" not in first:
        response: Response = RedirectResponse("/ingresar", status_code=303)
    else:
        response = JSONResponse(
            {"error": "csrf", "message": "La sesión de seguridad expiró. Recarga la página e intenta de nuevo."},
            status_code=403,
        )
    return response(scope, receive, send)


async def _read_body(receive: Receive) -> bytes:
    chunks: list[bytes] = []
    more = True
    while more:
        message = await receive()
        if message["type"] != "http.request":
            break
        chunks.append(message.get("body", b"") or b"")
        more = bool(message.get("more_body"))
    return b"".join(chunks)


def _replay(body: bytes) -> Receive:
    sent = False

    async def receive() -> Message:
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    return receive


def _cookie_header(token: str) -> bytes:
    return f"{CSRF_COOKIE}={token}; Path=/; SameSite=lax".encode("latin-1")


class CsrfMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET").upper()
        path = scope.get("path", "")
        request = Request(scope, receive)
        cookie = request.cookies.get(CSRF_COOKIE)
        token = cookie or new_token()

        if method in SAFE or path in SKIP_PATHS or path.startswith("/static"):
            async def send_wrapper(message: Message) -> None:
                if cookie is None and message["type"] == "http.response.start":
                    headers = MutableHeaders(raw=message.setdefault("headers", []))
                    already = any(
                        value.startswith(f"{CSRF_COOKIE}=") for value in headers.getlist("set-cookie")
                    )
                    if not already:
                        headers.append("set-cookie", _cookie_header(token).decode("latin-1"))
                await send(message)

            await self.app(scope, receive, send_wrapper)
            return

        header = request.headers.get(CSRF_HEADER) or request.headers.get("x-csrf-token")
        body = b""
        inner_receive = receive
        if not header:
            ct = (request.headers.get("content-type") or "").lower()
            if "application/x-www-form-urlencoded" in ct or "multipart/form-data" in ct:
                body = await _read_body(receive)
                inner_receive = _replay(body)
                if "application/x-www-form-urlencoded" in ct:
                    parsed = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)
                    raw = parsed.get("csrf_token") or [None]
                    header = raw[0] if raw else None
        if not cookie or not header or not secrets.compare_digest(cookie, header):
            await _csrf_fail(scope, inner_receive, send)
            return
        await self.app(scope, inner_receive, send)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        csp = (
            "default-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; "
            "connect-src 'self'"
        )
        response.headers.setdefault("Content-Security-Policy", csp)
        apply_auth_headers(request, response)
        return response
