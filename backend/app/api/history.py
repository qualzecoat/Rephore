"""Riwayat deteksi perangkat & pemakaian knowledge — untuk admin."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..models.device import DetectionLog, KnowledgeUsage
from ..models.knowledge import Knowledge
from ..models.user import User
from ..schemas.history import DetectionLogIn, DetectionLogOut, UsageOut
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
