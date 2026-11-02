"""Router CRUD de usuarios."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.modules.users import service as users_service
from app.modules.users.schemas import UserCreate, UserResponse, UserRolesUpdate, UserSitesUpdate, UserUpdate
from app.shared.dependencies import CurrentUser, DbSession, require_permission
from app.shared.pagination import Page, PageParams

router = APIRouter(prefix="/api/users", tags=["users"])

ManageUsers = Annotated[object, Depends(require_permission("users.manage"))]


@router.get("", response_model=Page[UserResponse])
def list_users(
    db: DbSession,
    _: ManageUsers,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[UserResponse]:
    result = users_service.list_users(db, PageParams(page=page, page_size=page_size))
    return Page(
        items=[UserResponse(**item) for item in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.post("", response_model=UserResponse, status_code=201)
def create_user(
    body: UserCreate,
    db: DbSession,
    actor: CurrentUser,
    _: ManageUsers,
) -> UserResponse:
    return UserResponse(**users_service.create_user(db, body, actor.id))


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: DbSession, _: ManageUsers) -> UserResponse:
    return UserResponse(**users_service.get_user(db, user_id))


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    body: UserUpdate,
    db: DbSession,
    actor: CurrentUser,
    _: ManageUsers,
) -> UserResponse:
    return UserResponse(**users_service.update_user(db, user_id, body, actor.id))


@router.delete("/{user_id}", response_model=UserResponse)
def delete_user(
    user_id: int,
    db: DbSession,
    actor: CurrentUser,
    _: ManageUsers,
) -> UserResponse:
    return UserResponse(**users_service.soft_delete_user(db, user_id, actor.id))


@router.post("/{user_id}/roles", response_model=UserResponse)
def set_user_roles(
    user_id: int,
    body: UserRolesUpdate,
    db: DbSession,
    actor: CurrentUser,
    _: ManageUsers,
) -> UserResponse:
    return UserResponse(**users_service.set_roles(db, user_id, body, actor.id))


@router.post("/{user_id}/zonas", response_model=UserResponse)
def set_user_sites(
    user_id: int,
    body: UserSitesUpdate,
    db: DbSession,
    actor: CurrentUser,
    _: ManageUsers,
) -> UserResponse:
    return UserResponse(**users_service.set_sites(db, user_id, body, actor.id))


@router.post("/{user_id}/desbloquear", response_model=UserResponse)
def unlock_user(user_id: int, db: DbSession, actor: CurrentUser, _: ManageUsers) -> UserResponse:
    return UserResponse(**users_service.unlock_user(db, user_id, actor.id))


@router.post("/{user_id}/forzar-contrasena", response_model=UserResponse)
def force_password(user_id: int, db: DbSession, actor: CurrentUser, _: ManageUsers) -> UserResponse:
    return UserResponse(**users_service.force_password_change(db, user_id, actor.id))
