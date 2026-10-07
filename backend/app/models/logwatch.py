"""Log watcher v1: insiden error, saran perbaikan AI, dan riwayat analisis."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


class ErrorEvent(Base):
    """Satu jenis error yang terdeteksi (didup per signature).

    service: "backend" | "worker" | "frontend"
    """

    __tablename__ = "error_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    service: Mapped[str] = mapped_column(String(16))
    signature: Mapped[str] = mapped_column(String(255), unique=True)
    message: Mapped[str] = mapped_column(Text, default="")
    traceback: Mapped[str | None] = mapped_column(Text, nullable=True)
    count: Mapped[int] = mapped_column(Integer, default=1)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AiSuggestion(Base):
    """Saran perbaikan dari AI untuk satu signature error."""

    __tablename__ = "ai_suggestions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    signature: Mapped[str] = mapped_column(String(255))
    service: Mapped[str] = mapped_column(String(16))
    # "low" | "medium" | "high"
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    probable_cause: Mapped[str] = mapped_column(Text, default="")
    suggested_fix: Mapped[str] = mapped_column(Text, default="")
    # "open" | "resolved" | "dismissed"
    status: Mapped[str] = mapped_column(String(16), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LogAnalysisRun(Base):
    """Riwayat eksekusi analisis log (terjadwal / manual)."""

    __tablename__ = "log_analysis_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # "scheduled" | "manual"
    trigger: Mapped[str] = mapped_column(String(16))
    # "pending" | "running" | "done" | "error"
    status: Mapped[str] = mapped_column(String(16), default="pending")
    incidents_found: Mapped[int] = mapped_column(Integer, default=0)
    suggestions_created: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
