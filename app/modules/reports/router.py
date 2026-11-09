"""API de reportes (Plan 08)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from app.modules.reports import service as reports_service
from app.modules.reports.schemas import (
    EjecutivoRequest,
    PeriodRequest,
    ReportCreateResponse,
    ReportResponse,
)
from app.shared.dependencies import CurrentUser, DbSession, require_permission
from app.shared.pagination import Page, PageParams

router = APIRouter(prefix="/api/reports", tags=["reports"])

CanExport = Annotated[object, Depends(require_permission("reports.export"))]


@router.get("", response_model=Page[ReportResponse])
def list_reports(
    db: DbSession,
    user: CurrentUser,
    _: CanExport,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[ReportResponse]:
    params = PageParams(page=page, page_size=page_size)
    items, total = reports_service.list_reports(
        db, user, offset=params.offset, limit=params.page_size
    )
    return Page(
        items=[ReportResponse(**i) for i in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post("/alertas", response_model=ReportCreateResponse)
def post_alertas(
    body: PeriodRequest, db: DbSession, user: CurrentUser, _: CanExport
) -> ReportCreateResponse:
    report = reports_service.create_alertas_report(db, user, body.start, body.end)
    return ReportCreateResponse(report=ReportResponse(**report))


@router.post("/modelo/{model_registry_id}", response_model=ReportCreateResponse)
def post_modelo(
    model_registry_id: int, db: DbSession, user: CurrentUser, _: CanExport
) -> ReportCreateResponse:
    report = reports_service.create_modelo_report(db, user, model_registry_id)
    return ReportCreateResponse(report=ReportResponse(**report))


@router.post("/comparativa", response_model=ReportCreateResponse)
def post_comparativa(
    db: DbSession, user: CurrentUser, _: CanExport
) -> ReportCreateResponse:
    report = reports_service.create_comparativa_report(db, user)
    return ReportCreateResponse(report=ReportResponse(**report))


@router.post("/ejecutivo", response_model=ReportCreateResponse)
def post_ejecutivo(
    body: EjecutivoRequest, db: DbSession, user: CurrentUser, _: CanExport
) -> ReportCreateResponse:
    report = reports_service.create_ejecutivo_report(
        db, user, body.start, body.end, body.stakeholder_id, body.formato
    )
    return ReportCreateResponse(report=ReportResponse(**report))


@router.post("/confiabilidad", response_model=ReportCreateResponse)
def post_confiabilidad(
    db: DbSession, user: CurrentUser, _: CanExport
) -> ReportCreateResponse:
    report = reports_service.create_confiabilidad_report(db, user)
    return ReportCreateResponse(report=ReportResponse(**report))


@router.get("/{report_id}/download")
def download_report(
    report_id: int, db: DbSession, user: CurrentUser, _: CanExport
) -> FileResponse:
    row, path = reports_service.get_report_for_download(db, user, report_id)
    media = (
        "application/pdf"
        if path.suffix.lower() == ".pdf"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return FileResponse(
        path,
        media_type=media,
        filename=path.name,
        headers={"Content-Disposition": f'attachment; filename="{path.name}"'},
    )
