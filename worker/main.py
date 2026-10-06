"""Rephore AI worker — proses antrean job & jadwal generate otomatis.

Loop tiap POLL_SECONDS (default 60 detik):
1. Ambil job AI berstatus pending -> generate via provider -> simpan knowledge.
2. Cek jadwal aktif yang sudah waktunya -> buat job terjadwal baru.
"""

import os
import time
import traceback
from datetime import date, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.models import ai as _ai_model  # noqa: F401 — daftarkan semua model
from app.models import device as _device_model  # noqa: F401 — agar FK ter-resolve
from app.models import knowledge as _knowledge_model  # noqa: F401
from app.models import user as _user_model  # noqa: F401 — agar FK ter-resolve
from app.models.ai import AiJob, AiProvider, AiSchedule
from app.models.knowledge import Knowledge
from app.services.ai import (
    build_knowledge_prompt,
    chat_complete,
    embed_text,
    embedding_text_for,
)
from app.services.knowledge import apply_parsed
from app.services.parser import parse_bbcode

POLL_SECONDS = int(os.environ.get("WORKER_POLL_SECONDS", "60"))


def wait_for_db() -> None:
    for _ in range(30):
        try:
            engine = create_engine(settings.database_url, pool_pre_ping=True)
            Base.metadata.create_all(bind=engine)
            return engine
        except OperationalError:
            time.sleep(2)
    raise RuntimeError("Database tidak bisa dijangkau")


def run_job(db, job: AiJob) -> None:
    provider = db.get(AiProvider, job.provider_id)
    if provider is None or not provider.is_active:
        raise RuntimeError("Provider tidak ditemukan / tidak aktif")
    model = job.model or provider.default_model
    if not model:
        raise RuntimeError("Model belum dipilih untuk job ini")

    messages = build_knowledge_prompt(
        job.brand, job.phone_model, job.category, job.subcategory, job.topic
    )
    content = chat_complete(
        provider.base_url,
        provider.api_key,
        model,
        messages,
        provider.temperature,
        provider.max_tokens,
    )
    parsed = parse_bbcode(content)
    if not parsed["title"]:
        raise RuntimeError(
            "AI tidak menghasilkan judul yang valid: "
            + "; ".join(parsed["warnings"][:3])
        )

    k = Knowledge(source="ai", status="belum_direview", created_by=job.created_by)
    apply_parsed(k, parsed, content)
    db.add(k)
    db.flush()  # dapatkan id sebelum embedding

    # isi embedding bila provider punya embedding_model (non-fatal bila gagal)
    if provider.embedding_model:
        try:
            text = embedding_text_for(
                k.title, k.brand, k.model, k.codes,
                k.category, k.subcategory, k.troubleshooting,
            )
            vec = embed_text(
                provider.base_url, provider.api_key, provider.embedding_model, text
            )
            if len(vec) == 1536:
                k.embedding = vec
            else:
                print(
                    f"[worker] dimensi embedding {len(vec)} != 1536, dilewati",
                    flush=True,
                )
        except Exception as e:
            print(f"[worker] embedding gagal: {e}", flush=True)

    job.result_knowledge_id = k.id


def process_pending(db) -> int:
    jobs = (
        db.scalars(
            select(AiJob)
            .where(AiJob.status == "pending")
            .order_by(AiJob.created_at)
            .limit(5)
        ).all()
    )
    for job in jobs:
        print(f"[worker] proses job {job.id} ({job.type})", flush=True)
        job.status = "running"
        db.commit()
        try:
            run_job(db, job)
            job.status = "done"
            print(
                f"[worker] job {job.id} selesai -> knowledge {job.result_knowledge_id}",
                flush=True,
            )
        except Exception as e:
            job.status = "failed"
            job.error = str(e)[:2000]
            print(f"[worker] job {job.id} gagal: {e}", flush=True)
            traceback.print_exc()
        job.updated_at = datetime.utcnow()
        db.commit()
    return len(jobs)


def check_schedules(db) -> int:
    """Satu jadwal yang sudah waktunya -> tepat satu job untuk hari ini."""
    now = datetime.now()
    today = date.today()
    made = 0
    schedules = db.scalars(
        select(AiSchedule).where(AiSchedule.is_active == True)
    ).all()
    for s in schedules:
        if s.last_run_date == today:
            continue
        if now.hour < s.run_hour:
            continue
        db.add(
            AiJob(
                type="scheduled",
                provider_id=s.provider_id,
                model=s.model,
                brand=s.brand,
                phone_model=s.phone_model,
                category=s.category,
                subcategory=s.topic or None,
                topic=s.topic or None,
                status="pending",
                created_by=s.created_by,
            )
        )
        s.last_run_date = today
        db.commit()
        made += 1
        print(
            f"[worker] jadwal '{s.name}': 1 job dibuat untuk hari ini",
            flush=True,
        )
    return made


def main() -> None:
    engine = wait_for_db()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    print("[worker] siap, polling tiap", POLL_SECONDS, "detik", flush=True)
    while True:
        try:
            db = SessionLocal()
            try:
                n_jobs = process_pending(db)
                n_sched = check_schedules(db)
                if n_jobs or n_sched:
                    print(
                        f"[worker] siklus selesai: {n_jobs} job, {n_sched} job terjadwal",
                        flush=True,
                    )
            finally:
                db.close()
        except Exception as e:
            print(f"[worker] error siklus: {e}", flush=True)
            traceback.print_exc()
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
