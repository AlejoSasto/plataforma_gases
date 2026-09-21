"""Helpers de navegación y contexto de plantillas."""

from __future__ import annotations

from app.modules.users.models import User


def template_context(user: User, *, title: str = "", active_nav: str = "") -> dict:
    return {
        "current_user": user,
        "permissions": set(user.permission_codes),
        "roles": set(user.role_names),
        "title": title,
        "active_nav": active_nav,
    }


def home_path_for_user(user: User) -> str:
    roles = set(user.role_names)
    if "interesado" in roles and "admin" not in roles:
        return "/executive"
    if "ingeniero_datos" in roles and "admin" not in roles and "operador_mina" not in roles:
        return "/?view=ingeniero"
    if "auditor" in roles and "admin" not in roles and "operador_mina" not in roles:
        return "/audit"
    return "/"
