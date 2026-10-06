"""Migrasi ringan untuk database yang sudah ada.

`create_all` tidak menambah kolom baru ke tabel lama, jadi perubahan skema
ditangani di sini dengan DDL `IF NOT EXISTS` yang aman dijalankan berulang.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine


def run_migrations(engine: Engine) -> None:
    with engine.begin() as conn:
        # Fase 4 revisi: jadwal disederhanakan (1 jadwal = 1 topik)
        conn.execute(text("ALTER TABLE ai_schedules ADD COLUMN IF NOT EXISTS topic TEXT"))
