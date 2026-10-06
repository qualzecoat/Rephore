import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


class AiProvider(Base):
    """Konfigurasi provider AI generik (OpenAI-compatible)."""

    __tablename__ = "ai_providers"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(128))
    base_url: Mapped[str] = mapped_column(String(512))
    # catatan: disimpan plain di v1 — enkripsi at-rest jadi PR berikutnya
    api_key: Mapped[str] = mapped_column(String(512))
    default_model: Mapped[str] = mapped_column(String(128), default="")
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4000)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AiJob(Base):
    """Satu permintaan generate knowledge (manual / terjadwal)."""

    __tablename__ = "ai_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # "manual" | "scheduled"
    type: Mapped[str] = mapped_column(String(16), default="manual")
    provider_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_providers.id"))
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String(64), nullable=True)
    topic: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "pending" | "running" | "done" | "failed"
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    result_knowledge_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("knowledges.id"), nullable=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class AiSchedule(Base):
    """Jadwal generate otomatis, misal 2-3 knowledge per hari."""

    __tablename__ = "ai_schedules"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(128))
    provider_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_providers.id"))
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # daftar topik dipisah koma, diputar tiap generate
    topics: Mapped[str] = mapped_column(Text, default="")
    knowledge_per_day: Mapped[int] = mapped_column(Integer, default=2)
    # jam (0-23) kapan jadwal mulai jalan hari itu
    run_hour: Mapped[int] = mapped_column(Integer, default=2)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
