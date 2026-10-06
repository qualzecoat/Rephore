"""Pencarian knowledge — keyword + ranking.

Fase 3: pencocokan keyword (judul, brand, model, subkategori, kode HP).
Fase berikutnya: digabung dengan pencarian semantik via kolom embedding.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..models.knowledge import Knowledge
from ..models.user import User
from ..schemas.knowledge import KnowledgeOut
from .deps import get_current_user
from .knowledge import _to_out

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[KnowledgeOut])
def search(
    q: str,
    category: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = q.strip()
    if not query:
        return []

    like = f"%{query}%"
    stmt = select(Knowledge).where(
        or_(
            Knowledge.title.ilike(like),
            Knowledge.brand.ilike(like),
            Knowledge.model.ilike(like),
            Knowledge.subcategory.ilike(like),
            # codes tersimpan sebagai JSON, cocokkan sebagai teks
            func.lower(cast(Knowledge.codes, String)).like(f"%{query.lower()}%"),
        )
    )
    if category:
        stmt = stmt.where(Knowledge.category == category)

    results = list(db.scalars(stmt.limit(100)).all())

    def score(k: Knowledge) -> int:
        ql = query.lower()
        # kode HP cocok persis = prioritas tertinggi
        if any((c or "").lower() == ql for c in (k.codes or [])):
            return 3
        if ql in (k.title or "").lower():
            return 2
        return 1

    results.sort(key=lambda k: (score(k), k.created_at), reverse=True)
    return [_to_out(k) for k in results]
