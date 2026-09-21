"""Router de roles y permisos (API JSON)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.roles_permissions import service as roles_service
from app.modules.roles_permissions.schemas import (
    PermissionResponse,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
)
from app.shared.dependencies import CurrentUser, DbSession, require_permission

router = APIRouter(prefix="/api", tags=["roles"])

ManageRoles = Annotated[object, Depends(require_permission("roles.manage"))]


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(db: DbSession, _: ManageRoles) -> list[RoleResponse]:
    return [RoleResponse(**item) for item in roles_service.list_roles(db)]


@router.post("/roles", response_model=RoleResponse, status_code=201)
def create_role(
    body: RoleCreate,
    db: DbSession,
    actor: CurrentUser,
    _: ManageRoles,
) -> RoleResponse:
    return RoleResponse(**roles_service.create_role(db, body, actor.id))


@router.patch("/roles/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    body: RoleUpdate,
    db: DbSession,
    actor: CurrentUser,
    _: ManageRoles,
) -> RoleResponse:
    return RoleResponse(**roles_service.update_role(db, role_id, body, actor.id))


@router.get("/permissions", response_model=list[PermissionResponse])
def list_permissions(db: DbSession, _: ManageRoles) -> list[PermissionResponse]:
    return [PermissionResponse(**item) for item in roles_service.list_permissions(db)]
