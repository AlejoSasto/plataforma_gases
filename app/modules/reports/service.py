"""Servicio de generación, persistencia y descarga de reportes."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.audit.service import record_audit
from app.modules.ml_training.repository import get_model
from app.modules.reports import generator as gen
from app.modules.reports.models import Report
from app.modules.stakeholders.models import StakeholderUser
from app.modules.stakeholders.service import alert_ids_visible_to_user
from app.modules.users.models import User
from app.shared.exceptions import NotFoundError, PermissionDeniedError, ValidationError

REPORT_TYPES = {"alertas_periodo", "desempeno_modelo", "resumen_ejecutivo", "confiabilidad"}


def _ensure_dir() -> Path:
    root = Path(settings.reports_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _date_to_dt(d: date, *, end: bool = False) -> datetime:
    t = time(23, 59, 59) if end else time(0, 0, 0)
    return datetime.combine(d, t, tzinfo=timezone.utc)


def _to_response(row: Report) -> dict[str, Any]:
    return {
        "id": row.id,
        "type": row.type,
        "period_start": row.period_start,
        "period_end": row.period_end,
        "file_path": row.file_path,
        "generated_by": row.generated_by,
        "created_at": row.created_at,
        "download_url": f"/api/reports/{row.id}/download",
    }


def _visible_for_user(db: Session, user: User) -> Optional[set[int]]:
    """None = sin restricción; set = solo esas alertas."""
    if "interesado" in user.role_names and "admin" not in user.role_names:
        return alert_ids_visible_to_user(db, user.id)
    return None


def _assert_interesado_owns_stakeholder(db: Session, user: User, stakeholder_id: int) -> None:
    if "admin" in user.role_names:
        return
    link = (
        db.query(StakeholderUser)
        .filter(
            StakeholderUser.user_id == user.id,
            StakeholderUser.stakeholder_id == stakeholder_id,
        )
        .first()
    )
    if link is None and "interesado" in user.role_names:
        raise PermissionDeniedError("No puedes generar reportes de ese stakeholder")


def _save_bytes(
    db: Session,
    *,
    report_type: str,
    content: bytes,
    ext: str,
    user: User,
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
) -> Report:
    folder = _ensure_dir()
    fname = f"{report_type}_{uuid4().hex[:12]}.{ext}"
    path = folder / fname
    path.write_bytes(content)
    row = Report(
        type=report_type,
        period_start=period_start,
        period_end=period_end,
        file_path=str(path).replace("\\", "/"),
        generated_by=user.id,
    )
    db.add(row)
    db.flush()
    record_audit(
        db,
        action="report.generate",
        user_id=user.id,
        resource_type="report",
        resource_id=row.id,
        metadata={"type": report_type, "file_path": row.file_path},
    )
    db.commit()
    db.refresh(row)
    return row


def create_alertas_report(db: Session, user: User, start: date, end: date) -> dict[str, Any]:
    if end < start:
        raise ValidationError("end debe ser >= start")
    visible = _visible_for_user(db, user)
    content = gen.generate_alertas_periodo(
        db,
        _date_to_dt(start),
        _date_to_dt(end, end=True),
        visible_ids=visible,
    )
    row = _save_bytes(
        db,
        report_type="alertas_periodo",
        content=content,
        ext="pdf",
        user=user,
        period_start=_date_to_dt(start),
        period_end=_date_to_dt(end, end=True),
    )
    return _to_response(row)


def create_modelo_report(db: Session, user: User, model_registry_id: int) -> dict[str, Any]:
    if get_model(db, model_registry_id) is None:
        raise NotFoundError("Modelo no encontrado")
    content = gen.generate_desempeno_modelo(db, model_registry_id)
    row = _save_bytes(
        db,
        report_type="desempeno_modelo",
        content=content,
        ext="pdf",
        user=user,
    )
    return _to_response(row)


def create_comparativa_report(db: Session, user: User) -> dict[str, Any]:
    content = gen.generate_comparativa_modelos(db)
    row = _save_bytes(
        db,
        report_type="comparativa_modelos",
        content=content,
        ext="xlsx",
        user=user,
    )
    return _to_response(row)


def create_ejecutivo_report(
    db: Session,
    user: User,
    start: date,
    end: date,
    stakeholder_id: Optional[int] = None,
    formato: str = "pdf",
) -> dict[str, Any]:
    if end < start:
        raise ValidationError("end debe ser >= start")
    if formato not in {"pdf", "xlsx"}:
        raise ValidationError("El formato tiene que ser pdf o xlsx")
    if stakeholder_id is not None:
        _assert_interesado_owns_stakeholder(db, user, stakeholder_id)
    start_dt = _date_to_dt(start)
    end_dt = _date_to_dt(end, end=True)
    who = user.full_name or user.email
    restricted = user.id if "interesado" in user.role_names and "admin" not in user.role_names else None
    if formato == "xlsx":
        content = gen.generate_resumen_ejecutivo(
            db,
            start_dt,
            end_dt,
            stakeholder_id=stakeholder_id,
            user_id=restricted,
        )
        ext = "xlsx"
    else:
        content = gen.generate_resumen_pdf(
            db,
            start_dt,
            end_dt,
            stakeholder_id=stakeholder_id,
            user_id=restricted,
            who=who,
        )
        ext = "pdf"
    row = _save_bytes(
        db,
        report_type="resumen_ejecutivo",
        content=content,
        ext=ext,
        user=user,
        period_start=start_dt,
        period_end=end_dt,
    )
    return _to_response(row)


def create_confiabilidad_report(db: Session, user: User) -> dict[str, Any]:
    content = gen.generate_confiabilidad(db, who=user.full_name or user.email)
    today = datetime.now(timezone.utc)
    row = _save_bytes(
        db,
        report_type="confiabilidad",
        content=content,
        ext="pdf",
        user=user,
        period_start=today,
        period_end=today,
    )
    return _to_response(row)


def list_reports(
    db: Session,
    user: User,
    *,
    offset: int,
    limit: int,
) -> tuple[list[dict[str, Any]], int]:
    q = db.query(Report)
    # interesado solo ve los suyos
    if "interesado" in user.role_names and "admin" not in user.role_names:
        q = q.filter(Report.generated_by == user.id)
    total = q.count()
    rows = q.order_by(Report.created_at.desc()).offset(offset).limit(limit).all()
    return [_to_response(r) for r in rows], total


def get_report_for_download(db: Session, user: User, report_id: int) -> tuple[Report, Path]:
    row = db.query(Report).filter(Report.id == report_id).first()
    if row is None:
        raise NotFoundError("Reporte no encontrado")
    if (
        "interesado" in user.role_names
        and "admin" not in user.role_names
        and row.generated_by != user.id
    ):
        raise PermissionDeniedError("No puedes descargar este reporte")
    path = Path(row.file_path)
    if not path.is_file():
        raise NotFoundError("Archivo de reporte no encontrado en disco")
    record_audit(
        db,
        action="report.download",
        user_id=user.id,
        resource_type="report",
        resource_id=row.id,
        metadata={"type": row.type},
    )
    db.commit()
    return row, path


def create_assistant_report(
    db: Session,
    user: User,
    *,
    kind: str,
    start: datetime,
    end: datetime,
    gas: str | None,
    sensor_ids: list[int],
    formato: str,
    data_until: str | None,
    historic: bool,
) -> dict[str, Any]:
    """Informe pedido por el asistente. La escritura sigue en este módulo."""
    from app.modules.reports.assistant_pdf import build_pdf

    if end < start:
        raise ValidationError("La fecha final tiene que ser posterior a la inicial.")
    content, _meta = build_pdf(
        db,
        user,
        kind=kind,
        start=start,
        end=end,
        gas=gas,
        sensor_ids=sensor_ids,
        data_until=data_until,
        historic=historic,
    )
    ext = "xlsx" if formato == "xlsx" else "pdf"
    if formato == "xlsx":
        content = _assistant_xlsx(kind, data_until, historic, start, end)
    row = _save_bytes(
        db,
        report_type=kind,
        content=content,
        ext=ext,
        user=user,
        period_start=start,
        period_end=end,
    )
    record_audit(
        db,
        action="report.generate",
        user_id=user.id,
        resource_type="report",
        resource_id=row.id,
        metadata={"type": kind, "via": "asistente", "format": ext},
    )
    db.commit()
    titles = {
        "avisos_periodo": "Avisos del periodo",
        "resumen_gerencia": "Resumen para gerencia",
        "confiabilidad": "Confiabilidad",
        "comportamiento_gas": "Comportamiento del gas",
    }
    payload = _to_response(row)
    return {
        "report_id": row.id,
        "format": ext,
        "title": titles.get(kind, "Informe"),
        "download_url": payload["download_url"],
        "n": 1,
    }


def _assistant_xlsx(kind: str, data_until: str | None, historic: bool, start: datetime, end: datetime) -> bytes:
    from io import BytesIO

    from openpyxl import Workbook

    book = Workbook()
    sheet = book.active
    sheet.title = "Informe"
    origin = "histórico" if historic else "en vivo"
    sheet.append(["tipo", kind])
    sheet.append(["periodo", f"{start.date().isoformat()} a {end.date().isoformat()}"])
    sheet.append(["datos_hasta", data_until or ""])
    sheet.append(["origen", origin])
    buffer = BytesIO()
    book.save(buffer)
    return buffer.getvalue()
