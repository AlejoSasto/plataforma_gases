"""API de auditoría."""

from __future__ import annotations

from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.modules.audit import service as audit_service
from app.shared.dependencies import DbSession, require_permission
from app.shared.pagination import Page, PageParams

router = APIRouter(prefix="/api/audit", tags=["audit"])

CanAudit = Annotated[object, Depends(require_permission("audit.view"))]


class AuditEntryResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    details: Optional[str] = None
    created_at: Any


@router.get("", response_model=Page[AuditEntryResponse])
def list_audit_api(
    db: DbSession,
    _: CanAudit,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    action: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Page[AuditEntryResponse]:
    params = PageParams(page=page, page_size=page_size)
    items, total = audit_service.list_audit(
        db,
        offset=params.offset,
        limit=params.page_size,
        action=action,
        user_id=user_id,
    )
    return Page(
        items=[AuditEntryResponse(**i) for i in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )
