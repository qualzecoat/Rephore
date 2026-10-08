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
        # Blok legacy hanya untuk DB lama yang masih punya kolom 'topics'.
        # Di install baru kolom itu tidak ada -> lewati agar tidak error.
        def _has_column(table: str, column: str) -> bool:
            return (
                conn.execute(
                    text(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_name = :t AND column_name = :c"
                    ),
                    {"t": table, "c": column},
                ).first()
                is not None
            )

        if _has_column("ai_schedules", "topics"):
            # Kolom legacy format lama: longgarkan NOT NULL agar insert baru
            # lolos, dan isi topic jadwal lama dari topik pertama daftar topics.
            conn.execute(
                text("ALTER TABLE ai_schedules ALTER COLUMN topics DROP NOT NULL")
            )
            if _has_column("ai_schedules", "knowledge_per_day"):
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
        # Anti-duplikat scheduler (2026-10-07)
        conn.execute(
            text("ALTER TABLE ai_schedules ADD COLUMN IF NOT EXISTS dedup_days INTEGER")
        )
        conn.execute(
            text("UPDATE ai_schedules SET dedup_days = 30 WHERE dedup_days IS NULL")
        )
        # Batas like 1x per user (2026-10-07) — index parsial seperti success
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_feedback_like_once "
                "ON knowledge_feedbacks (user_id, knowledge_id) "
                "WHERE kind = 'like'"
            )
        )
        # Thread balasan laporan (2026-10-07)
        conn.execute(
            text(
                "ALTER TABLE knowledge_reports "
                "ADD COLUMN IF NOT EXISTS replies_closed BOOLEAN"
            )
        )
        conn.execute(
            text(
                "UPDATE knowledge_reports SET replies_closed = false "
                "WHERE replies_closed IS NULL"
            )
        )
        # Aturan keras jadwal (no-Mi-Cloud dkk): kolom di jadwal + snapshot di job.
        # Nama kolom di-quote karena CONSTRAINT adalah reserved word di Postgres.
        conn.execute(
            text('ALTER TABLE ai_schedules ADD COLUMN IF NOT EXISTS "constraint" TEXT')
        )
        conn.execute(
            text('ALTER TABLE ai_jobs ADD COLUMN IF NOT EXISTS "constraint" TEXT')
        )
        # Enkripsi API key provider at-rest (2026-10-07): enkripsi nilai
        # plaintext yang masih tersisa. Import di dalam fungsi agar migrate.py
        # tetap ringan dan tidak ada import cycle.
        from ..services.crypto import encrypt_api_key, is_encrypted

        rows = conn.execute(text("SELECT id, api_key FROM ai_providers")).all()
        for pid, api_key in rows:
            if api_key and not is_encrypted(api_key):
                conn.execute(
                    text("UPDATE ai_providers SET api_key = :k WHERE id = :id"),
                    {"k": encrypt_api_key(api_key), "id": pid},
                )
