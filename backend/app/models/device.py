import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


class DetectionLog(Base):
    """Riwayat deteksi perangkat oleh user (untuk dilihat admin)."""

    __tablename__ = "detection_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    # "usb" (WebUSB VID/PID) | "manual" (input kode manual)
    method: Mapped[str] = mapped_column(String(16))
    vid: Mapped[str | None] = mapped_column(String(8), nullable=True)
    pid: Mapped[str | None] = mapped_column(String(8), nullable=True)
    # misal "Qualcomm EDL 9008" atau kode HP yang diinput manual
    label: Mapped[str] = mapped_column(String(255))
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class KnowledgeUsage(Base):
    """Riwayat pemakaian knowledge oleh user (untuk dilihat admin)."""

    __tablename__ = "knowledge_usages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    knowledge_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledges.id")
    )
    # "view" (buka detail) — aksi lain bisa ditambah nanti
    action: Mapped[str] = mapped_column(String(16), default="view")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
