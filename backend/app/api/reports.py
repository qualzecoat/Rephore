"""Laporan masalah & saran perbaikan dari user — dikelola admin."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..models.knowledge import Knowledge, KnowledgeReport, ReportReply
from ..models.user import User
from ..schemas.knowledge import ReplyIn, ReplyOut, ReportIn, ReportOut, ReportUpdate
from .deps import get_current_user, require_admin

router = APIRouter(prefix="/reports", tags=["reports"])

REPORT_KINDS = ("report", "suggestion")
REPORT_STATUSES = ("open", "resolved")


def _replies_count_sq():
    return (
        select(func.count())
        .where(ReportReply.report_id == KnowledgeReport.id)
        .scalar_subquery()
    )


def _to_out(r: KnowledgeReport, title: str, username: str, replies_count: int) -> ReportOut:
    return ReportOut(
        id=r.id,
        knowledge_id=r.knowledge_id,
        knowledge_title=title,
        username=username,
        kind=r.kind,
        message=r.message,
        status=r.status,
        replies_closed=r.replies_closed,
        replies_count=replies_count,
        created_at=r.created_at,
    )


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
        select(KnowledgeReport, Knowledge.title, User.username, _replies_count_sq())
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
        _to_out(r, title, username, replies_count or 0)
        for r, title, username, replies_count in rows
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
        select(KnowledgeReport, Knowledge.title, User.username, _replies_count_sq())
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
        _to_out(r, title, username, replies_count or 0)
        for r, title, username, replies_count in rows
    ]


@router.patch("/{report_id}")
def update_report(
    report_id: str,
    data: ReportUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin menandai laporan selesai / dibuka lagi / tutup/buka balasan."""
    r = db.get(KnowledgeReport, report_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan")
    if data.status is not None:
        if data.status not in REPORT_STATUSES:
            raise HTTPException(
                status_code=400, detail="Status harus 'open' atau 'resolved'"
            )
        r.status = data.status
    if data.replies_closed is not None:
        r.replies_closed = data.replies_closed
    db.commit()
    return {"id": r.id, "status": r.status, "replies_closed": r.replies_closed}


@router.delete("/{report_id}", status_code=204)
def delete_report(
    report_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)
):
    r = db.get(KnowledgeReport, report_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan")
    db.query(ReportReply).filter(ReportReply.report_id == r.id).delete()
    db.delete(r)
    db.commit()
    return None


def _can_view(user: User, r: KnowledgeReport) -> bool:
    return user.role == "admin" or r.user_id == user.id


@router.get("/{report_id}/replies", response_model=list[ReplyOut])
def list_replies(
    report_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Thread balasan sebuah laporan (pemilik laporan & admin)."""
    r = db.get(KnowledgeReport, report_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan")
    if not _can_view(user, r):
        raise HTTPException(status_code=403, detail="Tidak boleh melihat balasan ini")
    rows = db.execute(
        select(ReportReply, User.username, User.role)
        .join(User, ReportReply.user_id == User.id)
        .where(ReportReply.report_id == r.id)
        .order_by(ReportReply.created_at.asc())
    ).all()
    return [
        ReplyOut(
            id=rp.id,
            username=username,
            role=role,
            message=rp.message,
            created_at=rp.created_at,
        )
        for rp, username, role in rows
    ]


@router.post("/{report_id}/replies", status_code=201)
def create_reply(
    report_id: str,
    data: ReplyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kirim balasan. Admin selalu boleh; user biasa hanya setelah admin membalas."""
    r = db.get(KnowledgeReport, report_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan")
    if r.replies_closed:
        raise HTTPException(status_code=400, detail="Balasan sudah ditutup oleh admin")
    is_admin = user.role == "admin"
    if not is_admin and r.user_id != user.id:
        raise HTTPException(status_code=403, detail="Bukan laporanmu")
    if not is_admin:
        admin_replied = db.scalar(
            select(ReportReply)
            .join(User, ReportReply.user_id == User.id)
            .where(ReportReply.report_id == r.id, User.role == "admin")
            .limit(1)
        )
        if admin_replied is None:
            raise HTTPException(
                status_code=400,
                detail="Tunggu balasan admin terlebih dahulu",
            )
    message = data.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Pesan balasan tidak boleh kosong")
    rp = ReportReply(report_id=r.id, user_id=user.id, message=message)
    db.add(rp)
    db.commit()
    db.refresh(rp)
    return {"id": rp.id}
