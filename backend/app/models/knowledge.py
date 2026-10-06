import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


class Knowledge(Base):
    __tablename__ = "knowledges"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255), index=True)
    brand: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # daftar kode HP, misal ["SM-A546B", "V2219"]
    codes: Mapped[list] = mapped_column(JSON, default=list)
    # "hardware" | "software"
    category: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    subcategory: Mapped[str | None] = mapped_column(String(64), nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(32), nullable=True)
    est_time: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tools: Mapped[list] = mapped_column(JSON, default=list)
    # BBCode sumber (format manusia), dan hasil parse terstruktur (format AI)
    content_markdown: Mapped[str] = mapped_column(Text)
    content_json: Mapped[dict] = mapped_column(JSON, default=dict)
    troubleshooting: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "manual" | "ai"
    source: Mapped[str] = mapped_column(String(16), default="manual")
    # "belum_direview" | "sudah_direview"
    status: Mapped[str] = mapped_column(
        String(32), default="belum_direview", index=True
    )
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    # embedding untuk pencarian semantik (diisi Fase 3+)
    embedding: Mapped[list | None] = mapped_column(Vector(1536), nullable=True)
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class KnowledgeFeedback(Base):
    """Catatan siapa memberi testimoni apa — 'berhasil' dibatasi 1x per user."""

    __tablename__ = "knowledge_feedbacks"
    __table_args__ = (
        Index(
            "uq_feedback_success_once",
            "user_id",
            "knowledge_id",
            unique=True,
            postgresql_where=text("kind = 'success'"),
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    knowledge_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledges.id")
    )
    # "like" | "success"
    kind: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
