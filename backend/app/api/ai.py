"""AI provider generik, job generate manual, dan jadwal otomatis — khusus admin."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..models.ai import AiJob, AiProvider, AiSchedule
from ..models.user import User
from ..schemas.ai import (
    JobIn,
    JobOut,
    PreviewModelsIn,
    ProviderIn,
    ProviderOut,
    ProviderUpdate,
    ScheduleIn,
    ScheduleOut,
    ScheduleUpdate,
)
from ..services.ai import fetch_models
from ..services.crypto import decrypt_api_key, encrypt_api_key
from .deps import require_admin

router = APIRouter(prefix="/ai", tags=["ai"])


def _provider_out(p: AiProvider) -> ProviderOut:
    return ProviderOut(
        id=p.id,
        name=p.name,
        base_url=p.base_url,
        has_api_key=bool(p.api_key),
        default_model=p.default_model,
        embedding_model=p.embedding_model,
        temperature=p.temperature,
        max_tokens=p.max_tokens,
        is_active=p.is_active,
        created_at=p.created_at,
    )


# ---------- providers ----------


@router.get("/providers", response_model=list[ProviderOut])
def list_providers(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return [_provider_out(p) for p in db.scalars(select(AiProvider)).all()]


@router.post("/providers", response_model=ProviderOut, status_code=201)
def create_provider(
    data: ProviderIn, _: User = Depends(require_admin), db: Session = Depends(get_db)
):
    payload = data.model_dump()
    payload["api_key"] = encrypt_api_key(data.api_key)
    p = AiProvider(**payload)
    db.add(p)
    db.commit()
    db.refresh(p)
    return _provider_out(p)


@router.patch("/providers/{provider_id}", response_model=ProviderOut)
def update_provider(
    provider_id: str,
    data: ProviderUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    p = db.get(AiProvider, provider_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Provider tidak ditemukan")
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "api_key":
            if not value:
                continue  # string kosong = jangan ubah key yang sudah ada
            value = encrypt_api_key(value)
        setattr(p, field, value)
    db.commit()
    db.refresh(p)
    return _provider_out(p)


@router.delete("/providers/{provider_id}", status_code=204)
def delete_provider(
    provider_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)
):
    p = db.get(AiProvider, provider_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Provider tidak ditemukan")
    db.delete(p)
    db.commit()
    return None


@router.post("/providers/preview-models")
def preview_models(
    data: PreviewModelsIn, _: User = Depends(require_admin)
):
    """Ambil daftar model dari base_url + api_key tanpa menyimpan provider."""
    try:
        return {"models": fetch_models(data.base_url, data.api_key)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal mengambil model: {e}")


@router.get("/providers/{provider_id}/models")
def provider_models(
    provider_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)
):
    p = db.get(AiProvider, provider_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Provider tidak ditemukan")
    try:
        api_key = decrypt_api_key(p.api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        return {"models": fetch_models(p.base_url, api_key)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal mengambil model: {e}")


# ---------- jobs ----------


@router.post("/jobs", response_model=JobOut, status_code=201)
def create_job(
    data: JobIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    provider = db.get(AiProvider, data.provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider tidak ditemukan")
    job = AiJob(type="manual", created_by=admin.id, **data.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return list(
        db.scalars(
            select(AiJob).order_by(AiJob.created_at.desc()).limit(100)
        ).all()
    )


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(
    job_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)
):
    job = db.get(AiJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    return job


# ---------- schedules ----------


@router.get("/schedules", response_model=list[ScheduleOut])
def list_schedules(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return list(db.scalars(select(AiSchedule)).all())


@router.post("/schedules", response_model=ScheduleOut, status_code=201)
def create_schedule(
    data: ScheduleIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.get(AiProvider, data.provider_id) is None:
        raise HTTPException(status_code=404, detail="Provider tidak ditemukan")
    s = AiSchedule(created_by=admin.id, **data.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.patch("/schedules/{schedule_id}", response_model=ScheduleOut)
def update_schedule(
    schedule_id: str,
    data: ScheduleUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    s = db.get(AiSchedule, schedule_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Jadwal tidak ditemukan")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(s, field, value)
    db.commit()
    db.refresh(s)
    return s


@router.delete("/schedules/{schedule_id}", status_code=204)
def delete_schedule(
    schedule_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)
):
    s = db.get(AiSchedule, schedule_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Jadwal tidak ditemukan")
    db.delete(s)
    db.commit()
    return None
