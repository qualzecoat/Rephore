"""Pencarian knowledge — keyword + ranking + semantik (bila tersedia).

Semantik: bila ada provider aktif dengan embedding_model, query di-embedding
lalu digabung dengan hasil keyword. Gagal = fallback ke keyword saja.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..models.ai import AiProvider
from ..models.knowledge import Knowledge
from ..models.user import User
from ..schemas.knowledge import KnowledgeOut
from ..services.ai import embed_text
from .deps import get_current_user
from .knowledge import _to_out

router = APIRouter(prefix="/search", tags=["search"])


def _keyword_results(db: Session, query: str, category: str | None) -> list[Knowledge]:
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
    return list(db.scalars(stmt.limit(100)).all())


def _semantic_results(db: Session, query: str) -> list[Knowledge]:
    """Cari via embedding; kembalikan [] bila tidak tersedia/gagal."""
    provider = db.scalar(
        select(AiProvider).where(
            AiProvider.is_active == True,
            AiProvider.embedding_model.is_not(None),
        )
    )
    if provider is None or not provider.embedding_model:
        return []
    try:
        vec = embed_text(
            provider.base_url, provider.api_key, provider.embedding_model, query
        )
        if len(vec) != 1536:
            return []
        return list(
            db.scalars(
                select(Knowledge)
                .where(Knowledge.embedding.is_not(None))
                .order_by(Knowledge.embedding.cosine_distance(vec))
                .limit(20)
            ).all()
        )
    except Exception:
        return []


@router.get("", response_model=list[KnowledgeOut])
def search(
    q: str,
    category: str | None = None,
    semantic: bool = True,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = q.strip()
    if not query:
        return []

    keyword = _keyword_results(db, query, category)

    def score(k: Knowledge) -> int:
        ql = query.lower()
        # kode HP cocok persis = prioritas tertinggi
        if any((c or "").lower() == ql for c in (k.codes or [])):
            return 3
        if ql in (k.title or "").lower():
            return 2
        return 1

    keyword.sort(key=lambda k: (score(k), k.created_at), reverse=True)

    if not semantic:
        return [_to_out(k) for k in keyword]

    seen = {k.id for k in keyword}
    merged = list(keyword)
    for k in _semantic_results(db, query):
        if k.id not in seen:
            if category and k.category != category:
                continue
            merged.append(k)
            seen.add(k.id)
    return [_to_out(k) for k in merged]
