from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


class AppSetting(Base):
    """Pengaturan aplikasi generik (key -> value).

    Nilai untuk key sensitif (berakhiran _api_key/_secret/_token) disimpan
    terenkripsi (Fernet). Bila tidak ada baris untuk sebuah key, dipakai
    nilai default yang didefinisikan di kode (lihat services/settings.py).
    """

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
