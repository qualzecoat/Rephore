"""CRUD knowledge + parser BBCode + relasi + lampiran file."""

import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..models.device import KnowledgeUsage
from ..models.knowledge import (
    Knowledge,
    KnowledgeAttachment,
    KnowledgeFeedback,
    KnowledgeLink,
    KnowledgeReport,
    ReportReply,
)
from ..models.user import User
from ..schemas.knowledge import (
    AttachmentOut,
    FeedbackIn,
    KnowledgeCreate,
    KnowledgeDetail,
    KnowledgeListOut,
    KnowledgeOut,
    KnowledgeUpdate,
    LinkedArticle,
    LinkIn,
    ParseOut,
)
from ..services.knowledge import apply_parsed
from ..services.parser import parse_bbcode
from .deps import get_current_user, require_admin

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

# urutan antrian review: belum direview dulu, lalu paling lama
STATUS_ORDER = case((Knowledge.status == "belum_direview", 0), else_=1)

# --- lampiran file ---
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/app/uploads"))
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "500"))
# ekstensi yang diizinkan (file servis: firmware, driver, tool, arsip, dokumen)
ALLOWED_EXTENSIONS = {
    ".zip", ".rar", ".7z", ".tar", ".gz", ".tar.md5",
    ".img", ".bin", ".mbn", ".elf", ".sin", ".ops", ".pit",
    ".scatter", ".xml",
    ".exe", ".msi", ".apk",
    ".pdf", ".txt", ".md", ".csv",
}

LINK_RELATIONS = ("prerequisite", "related")


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


def _to_detail(k: Knowledge, db: Session) -> KnowledgeDetail:
    base = _to_out(k)

    def _linked(link_id: str, other: Knowledge, relation: str) -> LinkedArticle:
        return LinkedArticle(
            id=link_id,
            knowledge_id=other.id,
            title=other.title,
            brand=other.brand,
            model=other.model,
            relation=relation,
        )

    prereq_rows = db.execute(
        select(KnowledgeLink, Knowledge)
        .join(Knowledge, KnowledgeLink.to_knowledge_id == Knowledge.id)
        .where(
            KnowledgeLink.from_knowledge_id == k.id,
            KnowledgeLink.relation == "prerequisite",
        )
    ).all()
    reqby_rows = db.execute(
        select(KnowledgeLink, Knowledge)
        .join(Knowledge, KnowledgeLink.from_knowledge_id == Knowledge.id)
        .where(
            KnowledgeLink.to_knowledge_id == k.id,
            KnowledgeLink.relation == "prerequisite",
        )
    ).all()
    # "terkait" tampil dua arah
    rel_out = db.execute(
        select(KnowledgeLink, Knowledge)
        .join(Knowledge, KnowledgeLink.to_knowledge_id == Knowledge.id)
        .where(
            KnowledgeLink.from_knowledge_id == k.id,
            KnowledgeLink.relation == "related",
        )
    ).all()
    rel_in = db.execute(
        select(KnowledgeLink, Knowledge)
        .join(Knowledge, KnowledgeLink.from_knowledge_id == Knowledge.id)
        .where(
            KnowledgeLink.to_knowledge_id == k.id,
            KnowledgeLink.relation == "related",
        )
    ).all()
    seen: set[str] = set()
    related: list[LinkedArticle] = []
    for link, other in list(rel_out) + list(rel_in):
        if other.id in seen or other.id == k.id:
            continue
        seen.add(other.id)
        related.append(_linked(link.id, other, "related"))

    atts = db.scalars(
        select(KnowledgeAttachment)
        .where(KnowledgeAttachment.knowledge_id == k.id)
        .order_by(KnowledgeAttachment.created_at.asc())
    ).all()

    return KnowledgeDetail(
        **base.model_dump(),
        content_json=k.content_json or {},
        content_markdown=k.content_markdown,
        prerequisites=[_linked(l.id, o, "prerequisite") for l, o in prereq_rows],
        required_by=[_linked(l.id, o, "prerequisite") for l, o in reqby_rows],
        related=related,
        attachments=[
            AttachmentOut(
                id=a.id,
                original_name=a.original_name,
                size_bytes=a.size_bytes,
                mime_type=a.mime_type,
                description=a.description or "",
                created_at=a.created_at,
            )
            for a in atts
        ],
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
    return _to_detail(k, db)


@router.get("", response_model=KnowledgeListOut)
def list_knowledge(
    status_filter: str | None = None,
    category: str | None = None,
    q: str | None = None,
    # "review_queue" (belum direview dulu) | "newest" (terbaru dulu)
    order: str = "review_queue",
    page: int = 1,
    per_page: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    page = max(1, page)
    per_page = min(100, max(1, per_page))
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
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    if order == "newest":
        stmt = stmt.order_by(Knowledge.created_at.desc())
    else:
        stmt = stmt.order_by(STATUS_ORDER, Knowledge.created_at.asc())
    stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    items = db.scalars(stmt).all()
    return KnowledgeListOut(
        items=[_to_out(k) for k in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{knowledge_id}", response_model=KnowledgeDetail)
def get_knowledge(
    knowledge_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    k = db.get(Knowledge, knowledge_id)
    if k is None:
        raise HTTPException(status_code=404, detail="Knowledge tidak ditemukan")
    return _to_detail(k, db)


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
    return _to_detail(k, db)


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
    return _to_detail(k, db)


@router.post("/{knowledge_id}/unreview")
def unreview_knowledge(
    knowledge_id: str,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Batalkan status review — kembalikan ke belum_direview."""
    k = db.get(Knowledge, knowledge_id)
    if k is None:
        raise HTTPException(status_code=404, detail="Knowledge tidak ditemukan")
    k.status = "belum_direview"
    db.commit()
    db.refresh(k)
    return _to_detail(k, db)


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
    # tautan dua arah
    db.query(KnowledgeLink).filter(
        or_(
            KnowledgeLink.from_knowledge_id == k.id,
            KnowledgeLink.to_knowledge_id == k.id,
        )
    ).delete()
    # lampiran: hapus file fisiknya juga
    atts = (
        db.scalars(
            select(KnowledgeAttachment).where(
                KnowledgeAttachment.knowledge_id == k.id
            )
        ).all()
    )
    for a in atts:
        p = UPLOAD_DIR / a.stored_name
        if p.exists():
            p.unlink()
        db.delete(a)
    # laporan + balasan (hindari FK violation)
    rep_ids = (
        db.scalars(
            select(KnowledgeReport.id).where(
                KnowledgeReport.knowledge_id == k.id
            )
        ).all()
    )
    if rep_ids:
        db.query(ReportReply).filter(ReportReply.report_id.in_(rep_ids)).delete()
        db.query(KnowledgeReport).filter(
            KnowledgeReport.id.in_(rep_ids)
        ).delete()
    db.delete(k)
    db.commit()
    return None


# ---------- relasi antar artikel ----------


@router.post("/{knowledge_id}/links", status_code=201)
def create_link(
    knowledge_id: str,
    data: LinkIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Tautkan artikel ke artikel lain (prasyarat / terkait). Khusus admin."""
    if data.relation not in LINK_RELATIONS:
        raise HTTPException(
            status_code=400, detail="Relasi harus 'prerequisite' atau 'related'"
        )
    if db.get(Knowledge, knowledge_id) is None:
        raise HTTPException(status_code=404, detail="Knowledge tidak ditemukan")
    if db.get(Knowledge, data.to_knowledge_id) is None:
        raise HTTPException(status_code=404, detail="Artikel tujuan tidak ditemukan")
    if data.to_knowledge_id == knowledge_id:
        raise HTTPException(
            status_code=400, detail="Tidak bisa menautkan artikel ke dirinya sendiri"
        )
    exists = db.scalar(
        select(KnowledgeLink).where(
            KnowledgeLink.from_knowledge_id == knowledge_id,
            KnowledgeLink.to_knowledge_id == data.to_knowledge_id,
            KnowledgeLink.relation == data.relation,
        )
    )
    if exists:
        raise HTTPException(status_code=400, detail="Tautan sudah ada")
    link = KnowledgeLink(
        from_knowledge_id=knowledge_id,
        to_knowledge_id=data.to_knowledge_id,
        relation=data.relation,
        created_by=admin.id,
    )
    db.add(link)
    db.commit()
    return {"id": link.id}


@router.delete("/links/{link_id}", status_code=204)
def delete_link(
    link_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)
):
    link = db.get(KnowledgeLink, link_id)
    if link is None:
        raise HTTPException(status_code=404, detail="Tautan tidak ditemukan")
    db.delete(link)
    db.commit()
    return None


# ---------- lampiran file ----------


def _check_extension(filename: str) -> None:
    name = (filename or "").lower()
    if not any(name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail="Ekstensi file tidak diizinkan untuk lampiran",
        )


@router.post("/{knowledge_id}/attachments", status_code=201)
async def upload_attachment(
    knowledge_id: str,
    file: UploadFile = File(...),
    description: str = Form(""),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Upload file lampiran artikel (khusus admin)."""
    k = db.get(Knowledge, knowledge_id)
    if k is None:
        raise HTTPException(status_code=404, detail="Knowledge tidak ditemukan")
    _check_extension(file.filename or "")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "".join(Path(file.filename or "").suffixes)
    stored = f"{uuid.uuid4().hex}{suffix}"
    dest = UPLOAD_DIR / stored
    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    size = 0
    try:
        with dest.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File melebihi batas {MAX_UPLOAD_MB} MB",
                    )
                out.write(chunk)
    except Exception:
        if dest.exists():
            dest.unlink()
        raise
    att = KnowledgeAttachment(
        knowledge_id=k.id,
        stored_name=stored,
        original_name=file.filename or stored,
        mime_type=file.content_type,
        size_bytes=size,
        description=description.strip(),
        uploaded_by=admin.id,
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    return AttachmentOut(
        id=att.id,
        original_name=att.original_name,
        size_bytes=att.size_bytes,
        mime_type=att.mime_type,
        description=att.description or "",
        created_at=att.created_at,
    )


@router.get("/attachments/{attachment_id}/download")
def download_attachment(
    attachment_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unduh file lampiran (semua user yang login)."""
    att = db.get(KnowledgeAttachment, attachment_id)
    if att is None:
        raise HTTPException(status_code=404, detail="Lampiran tidak ditemukan")
    path = UPLOAD_DIR / att.stored_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="File tidak ditemukan di server")
    return FileResponse(
        path,
        media_type=att.mime_type or "application/octet-stream",
        filename=att.original_name,
    )


@router.delete("/attachments/{attachment_id}", status_code=204)
def delete_attachment(
    attachment_id: str,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Hapus lampiran (khusus admin) — baris DB + file fisik."""
    att = db.get(KnowledgeAttachment, attachment_id)
    if att is None:
        raise HTTPException(status_code=404, detail="Lampiran tidak ditemukan")
    path = UPLOAD_DIR / att.stored_name
    db.delete(att)
    db.commit()
    if path.exists():
        path.unlink()
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
