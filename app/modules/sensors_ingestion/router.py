"""Router de ingesta de sensores."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.modules.sensors_ingestion import repository as repo
from app.modules.sensors_ingestion import service as ingestion_service
from app.modules.sensors_ingestion.schemas import EtlRunResponse
from app.shared.dependencies import CurrentUser, DbSession, require_permission
from app.shared.exceptions import NotFoundError, ValidationError
from app.shared.pagination import Page, PageParams

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])

ManageSensors = Annotated[object, Depends(require_permission("sensors.manage"))]


@router.post("/upload", response_model=EtlRunResponse)
async def upload_files(
    db: DbSession,
    actor: CurrentUser,
    _: ManageSensors,
    files: list[UploadFile] = File(...),
) -> EtlRunResponse:
    if not files:
        raise ValidationError("Debe enviar al menos un archivo")

    saved: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="etl_upload_") as tmp:
        tmp_dir = Path(tmp)
        for upload in files:
            name = upload.filename or "upload.xlsx"
            if not name.lower().endswith((".xlsx", ".xls")):
                raise ValidationError(f"Formato no soportado: {name}")
            dest = tmp_dir / Path(name).name
            content = await upload.read()
            dest.write_bytes(content)
            saved.append(dest)

        run = ingestion_service.ingest_excel_paths(
            db,
            saved,
            triggered_by_user_id=actor.id,
            audit=True,
        )
    return EtlRunResponse(**ingestion_service.etl_run_to_dict(run))


@router.get("/runs", response_model=Page[EtlRunResponse])
def list_runs(
    db: DbSession,
    _: ManageSensors,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[EtlRunResponse]:
    params = PageParams(page=page, page_size=page_size)
    items, total = repo.list_etl_runs(db, offset=params.offset, limit=params.page_size)
    return Page(
        items=[EtlRunResponse(**ingestion_service.etl_run_to_dict(r)) for r in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/runs/{run_id}", response_model=EtlRunResponse)
def get_run(run_id: int, db: DbSession, _: ManageSensors) -> EtlRunResponse:
    run = repo.get_etl_run(db, run_id)
    if run is None:
        raise NotFoundError("Corrida ETL no encontrada")
    return EtlRunResponse(**ingestion_service.etl_run_to_dict(run))
