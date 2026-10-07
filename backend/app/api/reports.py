"""Laporan masalah & saran perbaikan dari user — dikelola admin."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..models.knowledge import Knowledge, KnowledgeReport
from ..models.user import User
from ..schemas.knowledge import ReportIn, ReportOut, ReportUpdate
from .deps import get_current_user, require_admin

router = APIRouter(prefix="/reports", tags=["reports"])

REPORT_KINDS = ("report", "suggestion")
REPORT_STATUSES = ("open", "resolved")


@router.post("/knowledge/{knowledge_id}", status_code=201)
def create_report(
    knowledge_id: str,
    data: ReportIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """User melaporkan masalah / memberi saran perbaikan untuk sebuah knowledge."""
    k = db.get(Knowledge, knowledge_id)
    if k is None:
        raise HTTPException(status_code=404, detail="Knowledge tidak ditemukan")
    if data.kind not in REPORT_KINDS:
        raise HTTPException(
            status_code=400, detail="Kind harus 'report' atau 'suggestion'"
        )
    message = data.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Alasan/saran tidak boleh kosong")
    r = KnowledgeReport(
        user_id=user.id,
        knowledge_id=k.id,
        kind=data.kind,
        message=message,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return {"id": r.id}


@router.get("/me", response_model=list[ReportOut])
def my_reports(
    status: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Laporan & saran yang dikirim user yang sedang login + status penanganannya."""
    q = (
        select(KnowledgeReport, Knowledge.title, User.username)
        .join(Knowledge, KnowledgeReport.knowledge_id == Knowledge.id)
        .join(User, KnowledgeReport.user_id == User.id)
        .where(KnowledgeReport.user_id == user.id)
        .order_by(KnowledgeReport.created_at.desc())
        .limit(200)
    )
    if status:
        q = q.where(KnowledgeReport.status == status)
    rows = db.execute(q).all()
    return [
        ReportOut(
            id=r.id,
            knowledge_id=r.knowledge_id,
            knowledge_title=title,
            username=username,
            kind=r.kind,
            message=r.message,
            status=r.status,
            created_at=r.created_at,
        )
        for r, title, username in rows
    ]


@router.get("", response_model=list[ReportOut])
def list_reports(
    status: str | None = None,
    kind: str | None = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Daftar laporan/saran untuk admin (filter opsional)."""
    q = (
        select(KnowledgeReport, Knowledge.title, User.username)
        .join(Knowledge, KnowledgeReport.knowledge_id == Knowledge.id)
        .join(User, KnowledgeReport.user_id == User.id)
        .order_by(KnowledgeReport.created_at.desc())
        .limit(200)
    )
    if status:
        q = q.where(KnowledgeReport.status == status)
    if kind:
        q = q.where(KnowledgeReport.kind == kind)
    rows = db.execute(q).all()
    return [
        ReportOut(
            id=r.id,
            knowledge_id=r.knowledge_id,
            knowledge_title=title,
            username=username,
            kind=r.kind,
            message=r.message,
            status=r.status,
            created_at=r.created_at,
        )
        for r, title, username in rows
    ]


@router.patch("/{report_id}")
def update_report(
    report_id: str,
    data: ReportUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin menandai laporan selesai / dibuka lagi."""
    r = db.get(KnowledgeReport, report_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan")
    if data.status is not None:
        if data.status not in REPORT_STATUSES:
            raise HTTPException(
                status_code=400, detail="Status harus 'open' atau 'resolved'"
            )
        r.status = data.status
    db.commit()
    return {"id": r.id, "status": r.status}


@router.delete("/{report_id}", status_code=204)
def delete_report(
    report_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)
):
    r = db.get(KnowledgeReport, report_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan")
    db.delete(r)
    db.commit()
    return None
