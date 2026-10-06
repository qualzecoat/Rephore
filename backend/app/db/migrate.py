"""Migrasi ringan untuk database yang sudah ada.

`create_all` tidak menambah kolom baru ke tabel lama, jadi perubahan skema
ditangani di sini dengan DDL yang aman dijalankan berulang.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine


def run_migrations(engine: Engine) -> None:
    with engine.begin() as conn:
        # Fase 4 revisi: jadwal disederhanakan (1 jadwal = 1 topik)
        conn.execute(
            text("ALTER TABLE ai_schedules ADD COLUMN IF NOT EXISTS topic TEXT")
        )
        # Kolom legacy format lama: longgarkan NOT NULL agar insert baru lolos,
        # dan isi topic jadwal lama dari topik pertama daftar topics.
        conn.execute(
            text("ALTER TABLE ai_schedules ALTER COLUMN topics DROP NOT NULL")
        )
        conn.execute(
            text(
                "ALTER TABLE ai_schedules "
                "ALTER COLUMN knowledge_per_day DROP NOT NULL"
            )
        )
        conn.execute(
            text(
                "UPDATE ai_schedules "
                "SET topic = NULLIF(split_part(topics, ',', 1), '') "
                "WHERE topic IS NULL AND topics IS NOT NULL"
            )
        )
