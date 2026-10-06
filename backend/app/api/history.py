"""Riwayat deteksi perangkat & pemakaian knowledge.

- POST /history/detections: user mencatat hasil deteksi (butuh login)
- GET /history/detections|usages: ringkasan semua user (admin)
- GET /history/me/*: riwayat milik user yang sedang login
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..models.device import DetectionLog, KnowledgeUsage
from ..models.knowledge import Knowledge, KnowledgeFeedback
from ..models.user import User
from ..schemas.history import (
    DetectionLogIn,
    DetectionLogOut,
    MyDetectionOut,
    MyFeedbackOut,
    MyUsageOut,
    UsageOut,
)
from .deps import get_current_user, require_admin

router = APIRouter(prefix="/history", tags=["history"])


@router.post("/detections", status_code=201)
def log_detection(
    data: DetectionLogIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log = DetectionLog(
        user_id=user.id,
        method=data.method,
        vid=data.vid,
        pid=data.pid,
        label=data.label,
        raw=data.raw,
    )
    db.add(log)
    db.commit()
    return {"id": log.id}


@router.get("/detections", response_model=list[DetectionLogOut])
def list_detections(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(DetectionLog, User.username)
        .join(User, DetectionLog.user_id == User.id)
        .order_by(DetectionLog.created_at.desc())
        .limit(200)
    ).all()
    return [
        DetectionLogOut(
            id=log.id,
            username=username,
            method=log.method,
            vid=log.vid,
            pid=log.pid,
            label=log.label,
            created_at=log.created_at,
        )
        for log, username in rows
    ]


@router.get("/usages", response_model=list[UsageOut])
def list_usages(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(KnowledgeUsage, User.username, Knowledge.title)
        .join(User, KnowledgeUsage.user_id == User.id)
        .join(Knowledge, KnowledgeUsage.knowledge_id == Knowledge.id)
        .order_by(KnowledgeUsage.created_at.desc())
        .limit(200)
    ).all()
    return [
        UsageOut(
            id=usage.id,
            username=username,
            knowledge_id=usage.knowledge_id,
            knowledge_title=title,
            action=usage.action,
            created_at=usage.created_at,
        )
        for usage, username, title in rows
    ]


@router.get("/me/detections", response_model=list[MyDetectionOut])
def my_detections(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Riwayat deteksi perangkat milik user yang sedang login."""
    rows = db.scalars(
        select(DetectionLog)
        .where(DetectionLog.user_id == user.id)
        .order_by(DetectionLog.created_at.desc())
        .limit(200)
    ).all()
    return [
        MyDetectionOut(
            id=d.id,
            method=d.method,
            vid=d.vid,
            pid=d.pid,
            label=d.label,
            created_at=d.created_at,
        )
        for d in rows
    ]


@router.get("/me/usages", response_model=list[MyUsageOut])
def my_usages(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Riwayat knowledge yang dibuka user yang sedang login."""
    rows = db.execute(
        select(KnowledgeUsage, Knowledge.title)
        .join(Knowledge, KnowledgeUsage.knowledge_id == Knowledge.id)
        .where(KnowledgeUsage.user_id == user.id)
        .order_by(KnowledgeUsage.created_at.desc())
        .limit(200)
    ).all()
    return [
        MyUsageOut(
            id=usage.id,
            knowledge_id=usage.knowledge_id,
            knowledge_title=title,
            action=usage.action,
            created_at=usage.created_at,
        )
        for usage, title in rows
    ]


@router.get("/me/feedbacks", response_model=list[MyFeedbackOut])
def my_feedbacks(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Testimoni (like / berhasil) yang diberikan user yang sedang login."""
    rows = db.execute(
        select(KnowledgeFeedback, Knowledge.title)
        .join(Knowledge, KnowledgeFeedback.knowledge_id == Knowledge.id)
        .where(KnowledgeFeedback.user_id == user.id)
        .order_by(KnowledgeFeedback.created_at.desc())
        .limit(200)
    ).all()
    return [
        MyFeedbackOut(
            id=fb.id,
            knowledge_id=fb.knowledge_id,
            knowledge_title=title,
            kind=fb.kind,
            created_at=fb.created_at,
        )
        for fb, title in rows
    ]
