"""Servicio de autenticación (Plan 19)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.passwords import validate_password
from app.core.rate_limit import too_many
from app.core.security import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    cookie_secure,
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.modules.audit.service import record_audit
from app.modules.auth import repository as auth_repo
from app.modules.auth import totp as totp_mod
from app.modules.users.models import (
    PasswordResetToken,
    User,
    UserInvitation,
    UserSiteScope,
)
from app.shared.access import TOTP_REQUIRED_ROLES, canonical_role
from app.shared.copy import LOGIN_BAD, LOGIN_LOCKED
from app.shared.exceptions import LockedError, UnauthorizedError, ValidationError
from app.shared.mailer import send_mail

MSG_BAD = LOGIN_BAD
MSG_LOCKED = LOGIN_LOCKED


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    secure = cookie_secure()
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    hours = getattr(settings, "refresh_token_expire_hours", 8)
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=int(hours) * 3600,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")


def _issue_tokens(
    db: Session,
    user: User,
    response: Response,
    *,
    user_agent: str | None = None,
    ip: str | None = None,
) -> None:
    access = create_access_token(
        user.id, roles=user.role_names, permissions=user.permission_codes
    )
    refresh_raw, expires_at = create_refresh_token(user.id)
    auth_repo.create_refresh_token_row(
        db,
        user_id=user.id,
        token_hash=hash_token(refresh_raw),
        expires_at=expires_at,
        user_agent=user_agent,
        ip=ip,
    )
    _set_auth_cookies(response, access, refresh_raw)


def _is_locked(user: User) -> bool:
    until = user.locked_until
    if until is None:
        return False
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    return until > _now()


def _fail_login(db: Session, user: User | None, *, email: str) -> None:
    record_audit(db, action="auth.login_fail", user_id=None if user is None else user.id, metadata={"email": email})
    if user is None:
        db.commit()
        raise UnauthorizedError(MSG_BAD)
    user.failed_login_count = int(user.failed_login_count or 0) + 1
    if user.failed_login_count >= settings.login_max_attempts:
        user.locked_until = _now() + timedelta(minutes=settings.login_lock_minutes)
        record_audit(db, action="auth.locked", user_id=user.id, resource_type="user", resource_id=user.id)
        db.add(user)
        db.commit()
        raise LockedError(MSG_LOCKED)
    db.add(user)
    db.commit()
    raise UnauthorizedError(MSG_BAD)


def login(
    db: Session,
    *,
    email: str,
    password: str,
    response: Response,
    totp_code: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> User:
    email_n = email.strip().lower()
    if too_many(f"login-ip:{ip or '-'}", limit=settings.login_rate_limit, window_s=settings.login_rate_window_seconds):
        raise LockedError(MSG_LOCKED)
    if too_many(f"login-mail:{email_n}", limit=settings.login_rate_limit, window_s=settings.login_rate_window_seconds):
        raise LockedError(MSG_LOCKED)

    user = auth_repo.get_user_by_email(db, email_n)
    if user is None:
        _fail_login(db, None, email=email_n)
    assert user is not None
    if _is_locked(user):
        raise LockedError(MSG_LOCKED)
    if not user.is_active:
        _fail_login(db, user, email=email_n)
    if not verify_password(password, user.password_hash):
        _fail_login(db, user, email=email_n)

    if user.totp_enabled:
        if not totp_code:
            raise UnauthorizedError("Escribe el código de 6 dígitos de tu aplicación de autenticación")
        if not _check_totp_or_backup(db, user, totp_code):
            _fail_login(db, user, email=email_n)

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = _now()
    db.add(user)
    _issue_tokens(db, user, response, user_agent=user_agent, ip=ip)
    record_audit(db, action="auth.login_ok", user_id=user.id, resource_type="user", resource_id=user.id)
    db.commit()
    db.refresh(user)
    return user


def _check_totp_or_backup(db: Session, user: User, code: str) -> bool:
    secret = user.totp_secret_enc or ""
    if secret and totp_mod.verify_code(secret, code):
        return True
    remaining = totp_mod.consume_backup(list(user.totp_backup_hashes or []), code)
    if remaining is None:
        return False
    user.totp_backup_hashes = remaining
    db.add(user)
    return True


def refresh(
    db: Session,
    *,
    refresh_raw: str | None,
    response: Response,
    ip: str | None = None,
    user_agent: str | None = None,
) -> User:
    if not refresh_raw:
        raise UnauthorizedError("Sesión ausente")

    row = auth_repo.get_refresh_by_hash(db, hash_token(refresh_raw))
    now = _now()
    if row is None:
        raise UnauthorizedError("Sesión inválida")
    if row.revoked_at is not None:
        auth_repo.revoke_all_for_user(db, row.user_id)
        record_audit(
            db,
            action="auth.session_revoked",
            user_id=row.user_id,
            resource_type="user",
            resource_id=row.user_id,
            details="reutilización de sesión",
        )
        db.commit()
        raise UnauthorizedError("Sesión inválida")
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        raise UnauthorizedError("Sesión vencida")

    user = row.user
    if user is None or not user.is_active:
        raise UnauthorizedError("Usuario no encontrado o inactivo")

    auth_repo.revoke_refresh(db, row)
    _issue_tokens(db, user, response, user_agent=user_agent, ip=ip)
    db.commit()
    db.refresh(user)
    return user


def logout(db: Session, *, user: User | None, refresh_raw: str | None, response: Response) -> None:
    if refresh_raw:
        row = auth_repo.get_refresh_by_hash(db, hash_token(refresh_raw))
        if row is not None:
            auth_repo.revoke_refresh(db, row)

    if user is not None:
        record_audit(db, action="auth.logout", user_id=user.id, resource_type="user", resource_id=user.id)

    _clear_auth_cookies(response)
    db.commit()


def revoke_session(db: Session, *, user: User, session_id: int | None = None, all_sessions: bool = False) -> int:
    from app.modules.users.models import RefreshToken

    if all_sessions:
        n = auth_repo.revoke_all_for_user(db, user.id)
        record_audit(db, action="auth.session_revoked", user_id=user.id, details="todas")
        db.commit()
        return n
    row = (
        db.query(RefreshToken)
        .filter(RefreshToken.id == session_id, RefreshToken.user_id == user.id)
        .first()
    )
    if row is None:
        return 0
    auth_repo.revoke_refresh(db, row)
    record_audit(db, action="auth.session_revoked", user_id=user.id, resource_id=session_id)
    db.commit()
    return 1


def request_password_reset(db: Session, *, email: str) -> None:
    email_n = email.strip().lower()
    if too_many(f"reset:{email_n}", limit=5, window_s=3600):
        return
    user = auth_repo.get_user_by_email(db, email_n)
    record_audit(db, action="auth.password_reset_requested", metadata={"email": email_n})
    if user is None or not user.is_active:
        db.commit()
        return
    raw = __import__("secrets").token_urlsafe(32)
    row = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(raw),
        expires_at=_now() + timedelta(minutes=30),
    )
    db.add(row)
    send_mail(
        to=user.email,
        subject="Restablece tu contraseña",
        body=f"Usa este enlace en los próximos 30 minutos:\n/recuperar?token={raw}\n",
    )
    db.commit()


def complete_password_reset(db: Session, *, token: str, new_password: str) -> None:
    row = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == hash_token(token))
        .first()
    )
    if row is None or row.used_at is not None:
        raise ValidationError("El enlace ya no es válido. Solicita uno nuevo.")
    exp = row.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < _now():
        raise ValidationError("El enlace ya no es válido. Solicita uno nuevo.")
    user = auth_repo.get_user_by_id(db, row.user_id)
    if user is None:
        raise ValidationError("El enlace ya no es válido. Solicita uno nuevo.")
    err = validate_password(new_password, email=user.email, full_name=user.full_name)
    if err:
        raise ValidationError(err)
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.password_changed_at = _now()
    user.failed_login_count = 0
    user.locked_until = None
    row.used_at = _now()
    db.add(user)
    db.add(row)
    auth_repo.revoke_all_for_user(db, user.id)
    record_audit(db, action="auth.password_reset_done", user_id=user.id)
    db.commit()


def change_password(db: Session, *, user: User, current: str, new: str) -> None:
    if not verify_password(current, user.password_hash):
        raise ValidationError("La contraseña actual no es correcta")
    err = validate_password(new, email=user.email, full_name=user.full_name)
    if err:
        raise ValidationError(err)
    user.password_hash = hash_password(new)
    user.must_change_password = False
    user.password_changed_at = _now()
    db.add(user)
    db.commit()


def invite_user(
    db: Session,
    *,
    actor: User,
    email: str,
    full_name: str,
    role_ids: list[int],
    site_ids: list[int] | None = None,
) -> UserInvitation:
    email_n = email.strip().lower()
    existing = auth_repo.get_user_by_email(db, email_n)
    if existing is not None:
        raise ValidationError("Esa persona ya tiene cuenta")
    raw = __import__("secrets").token_urlsafe(32)
    inv = UserInvitation(
        email=email_n,
        full_name=full_name,
        role_ids=role_ids,
        site_ids=site_ids or [],
        token_hash=hash_token(raw),
        invited_by=actor.id,
        expires_at=_now() + timedelta(hours=72),
    )
    db.add(inv)
    send_mail(
        to=email_n,
        subject="Invitación a Plataforma Gases",
        body=f"Hola {full_name}. Crea tu contraseña con este enlace (72 h):\n/invitar?token={raw}\n",
    )
    record_audit(db, action="user.invited", user_id=actor.id, metadata={"email": email_n})
    db.commit()
    db.refresh(inv)
    inv._plain_token = raw  # type: ignore[attr-defined]
    return inv


def accept_invitation(db: Session, *, token: str, password: str, response: Response) -> User:
    inv = db.query(UserInvitation).filter(UserInvitation.token_hash == hash_token(token)).first()
    if inv is None or inv.accepted_at is not None:
        raise ValidationError("El enlace de invitación ya no es válido.")
    exp = inv.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < _now():
        raise ValidationError("El enlace de invitación ya no es válido.")
    err = validate_password(password, email=inv.email, full_name=inv.full_name or "")
    if err:
        raise ValidationError(err)
    from app.modules.roles_permissions.models import Role

    roles = db.query(Role).filter(Role.id.in_(inv.role_ids or [])).all()
    user = User(
        email=inv.email,
        full_name=inv.full_name or inv.email,
        password_hash=hash_password(password),
        is_active=True,
        must_change_password=False,
        password_changed_at=_now(),
        roles=roles,
    )
    db.add(user)
    db.flush()
    for sid in inv.site_ids or []:
        db.add(UserSiteScope(user_id=user.id, site_id=int(sid)))
    inv.accepted_at = _now()
    db.add(inv)
    record_audit(db, action="user.invitation_accepted", user_id=user.id)
    _issue_tokens(db, user, response)
    db.commit()
    db.refresh(user)
    return user


def begin_totp(user: User) -> dict[str, str]:
    secret = totp_mod.new_secret()
    return {"secret": secret, "uri": totp_mod.provisioning_uri(secret, user.email)}


def enable_totp(db: Session, *, user: User, secret: str, code: str) -> list[str]:
    if not totp_mod.verify_code(secret, code):
        raise ValidationError("Ese código no coincide. Prueba con el actual de tu aplicación.")
    codes = totp_mod.backup_codes()
    user.totp_secret_enc = secret
    user.totp_enabled = True
    user.totp_backup_hashes = [totp_mod.hash_backup(c) for c in codes]
    db.add(user)
    record_audit(db, action="auth.totp_enabled", user_id=user.id)
    db.commit()
    return codes


def user_to_me(user: User) -> dict:
    roles = [canonical_role(r) for r in user.role_names]
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "roles": user.role_names,
        "permissions": user.permission_codes,
        "must_change_password": bool(user.must_change_password),
        "totp_enabled": bool(user.totp_enabled),
        "totp_required": bool(set(roles) & TOTP_REQUIRED_ROLES and not user.totp_enabled),
    }
