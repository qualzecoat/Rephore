"""CRUD knowledge + parser BBCode."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..models.device import KnowledgeUsage
from ..models.knowledge import Knowledge, KnowledgeFeedback
from ..models.user import User
from ..schemas.knowledge import (
    FeedbackIn,
    KnowledgeCreate,
    KnowledgeDetail,
    KnowledgeOut,
    KnowledgeUpdate,
    ParseOut,
)
from ..services.knowledge import apply_parsed
from ..services.parser import parse_bbcode
from .deps import get_current_user, require_admin

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

# urutan antrian review: belum direview dulu, lalu paling lama
STATUS_ORDER = case((Knowledge.status == "belum_direview", 0), else_=1)


def _tags(k: Knowledge) -> list[str]:
    """Satu artikel bisa punya beberapa tag sekaligus,
    misal belum direview tapi sudah ada testimoni."""
    tags = ["sudah direview" if k.status == "sudah_direview" else "belum direview"]
    if k.like_count + k.success_count > 0:
        tags.append("ada testimoni")
    return tags


def _to_out(k: Knowledge) -> KnowledgeOut:
    return KnowledgeOut(
        id=k.id,
        title=k.title,
        brand=k.brand,
        model=k.model,
        codes=k.codes or [],
        category=k.category,
        subcategory=k.subcategory,
        difficulty=k.difficulty,
        est_time=k.est_time,
        tools=k.tools or [],
        troubleshooting=k.troubleshooting,
        source=k.source,
        status=k.status,
        tags=_tags(k),
        like_count=k.like_count,
        success_count=k.success_count,
        created_at=k.created_at,
        updated_at=k.updated_at,
    )


def _to_detail(k: Knowledge) -> KnowledgeDetail:
    base = _to_out(k)
    return KnowledgeDetail(
        **base.model_dump(),
        content_json=k.content_json or {},
        content_markdown=k.content_markdown,
    )


@router.post("/parse", response_model=ParseOut)
def parse_preview(
    data: KnowledgeCreate, _: User = Depends(require_admin)
):
    """Parse BBCode tanpa menyimpan — untuk preview sebelum disimpan."""
    parsed = parse_bbcode(data.bbcode)
    return ParseOut(data=parsed, warnings=parsed["warnings"])


@router.post("", response_model=KnowledgeDetail, status_code=201)
def create_knowledge(
    data: KnowledgeCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if data.source not in ("manual", "ai"):
        raise HTTPException(status_code=400, detail="Source harus 'manual'/'ai'")
    parsed = parse_bbcode(data.bbcode)
    if not parsed["title"]:
        raise HTTPException(
            status_code=400,
            detail={"message": "Judul wajib ada", "warnings": parsed["warnings"]},
        )
    k = Knowledge(source=data.source, created_by=admin.id)
    apply_parsed(k, parsed, data.bbcode)
    db.add(k)
    db.commit()
    db.refresh(k)
    return _to_detail(k)


@router.get("", response_model=list[KnowledgeOut])
def list_knowledge(
    status_filter: str | None = None,
    category: str | None = None,
    q: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Knowledge)
    if status_filter:
        stmt = stmt.where(Knowledge.status == status_filter)
    if category:
        stmt = stmt.where(Knowledge.category == category)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Knowledge.title.ilike(like),
                Knowledge.brand.ilike(like),
                Knowledge.model.ilike(like),
            )
        )
    stmt = stmt.order_by(STATUS_ORDER, Knowledge.created_at.asc())
    return [_to_out(k) for k in db.scalars(stmt).all()]


@router.get("/{knowledge_id}", response_model=KnowledgeDetail)
def get_knowledge(
    knowledge_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    k = db.get(Knowledge, knowledge_id)
    if k is None:
        raise HTTPException(status_code=404, detail="Knowledge tidak ditemukan")
    return _to_detail(k)


@router.patch("/{knowledge_id}", response_model=KnowledgeDetail)
def update_knowledge(
    knowledge_id: str,
    data: KnowledgeUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    k = db.get(Knowledge, knowledge_id)
    if k is None:
        raise HTTPException(status_code=404, detail="Knowledge tidak ditemukan")
    if data.bbcode is not None:
        parsed = parse_bbcode(data.bbcode)
        if not parsed["title"]:
            raise HTTPException(
                status_code=400,
                detail={"message": "Judul wajib ada", "warnings": parsed["warnings"]},
            )
        apply_parsed(k, parsed, data.bbcode)
    if data.status is not None:
        if data.status not in ("belum_direview", "sudah_direview"):
            raise HTTPException(status_code=400, detail="Status tidak valid")
        k.status = data.status
    db.commit()
    db.refresh(k)
    return _to_detail(k)


@router.post("/{knowledge_id}/review", response_model=KnowledgeDetail)
def review_knowledge(
    knowledge_id: str,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    k = db.get(Knowledge, knowledge_id)
    if k is None:
        raise HTTPException(status_code=404, detail="Knowledge tidak ditemukan")
    k.status = "sudah_direview"
    db.commit()
    db.refresh(k)
    return _to_detail(k)


@router.delete("/{knowledge_id}", status_code=204)
def delete_knowledge(
    knowledge_id: str,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    k = db.get(Knowledge, knowledge_id)
    if k is None:
        raise HTTPException(status_code=404, detail="Knowledge tidak ditemukan")
    # hapus testimoni & histori pemakaian dulu agar tidak mentok foreign key
    db.query(KnowledgeFeedback).filter(
        KnowledgeFeedback.knowledge_id == k.id
    ).delete()
    db.query(KnowledgeUsage).filter(KnowledgeUsage.knowledge_id == k.id).delete()
    db.delete(k)
    db.commit()
    return None


@router.post("/{knowledge_id}/view", status_code=204)
def log_view(
    knowledge_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Catat bahwa user membuka knowledge (untuk histori admin)."""
    k = db.get(Knowledge, knowledge_id)
    if k is None:
        raise HTTPException(status_code=404, detail="Knowledge tidak ditemukan")
    db.add(KnowledgeUsage(user_id=user.id, knowledge_id=k.id, action="view"))
    db.commit()
    return None


@router.post("/{knowledge_id}/feedback")
def feedback(
    knowledge_id: str,
    data: FeedbackIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Testimoni user: like atau tombol berhasil (masing-masing 1x per user)."""
    k = db.get(Knowledge, knowledge_id)
    if k is None:
        raise HTTPException(status_code=404, detail="Knowledge tidak ditemukan")
    if data.type not in ("like", "success"):
        raise HTTPException(
            status_code=400, detail="Type harus 'like' atau 'success'"
        )
    exists = db.scalar(
        select(KnowledgeFeedback).where(
            KnowledgeFeedback.user_id == user.id,
            KnowledgeFeedback.knowledge_id == k.id,
            KnowledgeFeedback.kind == data.type,
        )
    )
    if exists:
        label = "like" if data.type == "like" else "menandai berhasil"
        raise HTTPException(
            status_code=400,
            detail=f"Kamu sudah memberi {label} untuk knowledge ini",
        )
    db.add(KnowledgeFeedback(user_id=user.id, knowledge_id=k.id, kind=data.type))
    if data.type == "like":
        k.like_count += 1
    else:
        k.success_count += 1
    try:
        db.commit()
    except IntegrityError:
        # balapan request bersamaan — index unik di DB yang menang
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Kamu sudah memberi testimoni untuk knowledge ini",
        )
    return {"like_count": k.like_count, "success_count": k.success_count}


@router.get("/{knowledge_id}/my-feedback")
def my_feedback(
    knowledge_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Testimoni apa saja yang sudah diberikan user ini untuk knowledge ini."""
    kinds = set(
        db.scalars(
            select(KnowledgeFeedback.kind).where(
                KnowledgeFeedback.user_id == user.id,
                KnowledgeFeedback.knowledge_id == knowledge_id,
                KnowledgeFeedback.kind.in_(["like", "success"]),
            )
        ).all()
    )
    return {"success_given": "success" in kinds, "like_given": "like" in kinds}
