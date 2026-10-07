"""Log watcher v1: terima laporan error frontend, kelola saran AI (admin)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..models.logwatch import AiSuggestion, ErrorEvent, LogAnalysisRun
from ..models.user import User
from ..services.logwatch import record_error_event
from .deps import get_current_user, require_admin

router = APIRouter(prefix="/logwatch", tags=["logwatch"])


class FrontendErrorIn(BaseModel):
    message: str
    stack: str | None = None


class SuggestionUpdate(BaseModel):
    # "open" | "resolved" | "dismissed"
    status: str | None = None


class SuggestionOut(BaseModel):
    id: str
    signature: str
    service: str
    severity: str
    probable_cause: str
    suggested_fix: str
    status: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class ErrorEventOut(BaseModel):
    id: str
    service: str
    signature: str
    message: str
    count: int
    first_seen: str
    last_seen: str

    model_config = ConfigDict(from_attributes=True)


class AnalysisRunOut(BaseModel):
    id: str
    trigger: str
    status: str
    incidents_found: int
    suggestions_created: int
    error: str | None
    created_at: str
    finished_at: str | None

    model_config = ConfigDict(from_attributes=True)


@router.post("/errors", status_code=201)
def report_frontend_error(
    data: FrontendErrorIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Frontend melaporkan JS error (dibatas di sisi klien)."""
    message = (data.message or "").strip()[:500]
    if not message:
        raise HTTPException(status_code=400, detail="Message kosong")
    signature = f"FrontendError:{message[:100]}"
    record_error_event(
        db,
        service="frontend",
        signature=signature,
        message=message,
        tb=(data.stack or "")[:2000] or None,
    )
    return {"ok": True}


@router.get("/errors", response_model=list[ErrorEventOut])
def list_errors(
    _: User = Depends(require_admin), db: Session = Depends(get_db)
):
    rows = db.scalars(
        select(ErrorEvent).order_by(ErrorEvent.last_seen.desc()).limit(100)
    ).all()
    return [
        ErrorEventOut(
            id=e.id,
            service=e.service,
            signature=e.signature,
            message=e.message,
            count=e.count,
            first_seen=e.first_seen.isoformat(),
            last_seen=e.last_seen.isoformat(),
        )
        for e in rows
    ]


@router.get("/suggestions", response_model=list[SuggestionOut])
def list_suggestions(
    status: str | None = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = select(AiSuggestion).order_by(AiSuggestion.created_at.desc()).limit(100)
    if status:
        q = q.where(AiSuggestion.status == status)
    rows = db.scalars(q).all()
    return [
        SuggestionOut(
            id=s.id,
            signature=s.signature,
            service=s.service,
            severity=s.severity,
            probable_cause=s.probable_cause,
            suggested_fix=s.suggested_fix,
            status=s.status,
            created_at=s.created_at.isoformat(),
        )
        for s in rows
    ]


@router.patch("/suggestions/{suggestion_id}")
def update_suggestion(
    suggestion_id: str,
    data: SuggestionUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    s = db.get(AiSuggestion, suggestion_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Saran tidak ditemukan")
    if data.status is not None:
        if data.status not in ("open", "resolved", "dismissed"):
            raise HTTPException(status_code=400, detail="Status tidak valid")
        s.status = data.status
    db.commit()
    return {"id": s.id, "status": s.status}


@router.delete("/suggestions/{suggestion_id}", status_code=204)
def delete_suggestion(
    suggestion_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)
):
    s = db.get(AiSuggestion, suggestion_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Saran tidak ditemukan")
    db.delete(s)
    db.commit()
    return None


@router.post("/analysis/run", status_code=201)
def trigger_analysis(
    _: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """Minta worker menjalankan analisis log sekarang (diproses < 1 menit)."""
    existing = db.scalar(
        select(LogAnalysisRun).where(LogAnalysisRun.status == "pending").limit(1)
    )
    if existing:
        return {"id": existing.id, "status": "pending"}
    run = LogAnalysisRun(trigger="manual", status="pending")
    db.add(run)
    db.commit()
    db.refresh(run)
    return {"id": run.id, "status": run.status}


@router.get("/analysis/runs", response_model=list[AnalysisRunOut])
def list_runs(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(LogAnalysisRun).order_by(LogAnalysisRun.created_at.desc()).limit(20)
    ).all()
    return [
        AnalysisRunOut(
            id=r.id,
            trigger=r.trigger,
            status=r.status,
            incidents_found=r.incidents_found,
            suggestions_created=r.suggestions_created,
            error=r.error,
            created_at=r.created_at.isoformat(),
            finished_at=r.finished_at.isoformat() if r.finished_at else None,
        )
        for r in rows
    ]
