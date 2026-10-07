"""Rephore AI worker — proses antrean job & jadwal generate otomatis.

Loop tiap POLL_SECONDS (default 60 detik):
1. Ambil job AI berstatus pending -> generate via provider -> simpan knowledge.
2. Cek jadwal aktif yang sudah waktunya -> buat job terjadwal baru.
"""

import os
import time
import traceback
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.models import ai as _ai_model  # noqa: F401 — daftarkan semua model
from app.models import device as _device_model  # noqa: F401 — agar FK ter-resolve
from app.models import knowledge as _knowledge_model  # noqa: F401
from app.models import settings as _settings_model  # noqa: F401
from app.models import user as _user_model  # noqa: F401 — agar FK ter-resolve
from app.models.ai import AiJob, AiProvider, AiSchedule
from app.models.knowledge import Knowledge
from app.models.logwatch import AiSuggestion, ErrorEvent, LogAnalysisRun
from app.services.ai import (
    build_knowledge_prompt,
    chat_complete,
    embed_text,
    embedding_text_for,
)
from app.services.crypto import decrypt_api_key
from app.services.logwatch import (
    build_log_analysis_prompt,
    exception_signature,
    parse_suggestions,
    record_error_event,
)
from app.services.knowledge import apply_parsed
from app.services.research import research_topic
from app.services.settings import get_setting
from app.services.parser import parse_bbcode

POLL_SECONDS = int(os.environ.get("WORKER_POLL_SECONDS", "60"))
# v1 log watcher: digest analisis tiap N jam (0 = hanya manual)
LOG_ANALYSIS_INTERVAL_HOURS = int(os.environ.get("LOG_ANALYSIS_INTERVAL_HOURS", "24"))
LOG_ANALYSIS_MAX_INCIDENTS = 10


def wait_for_db() -> None:
    for _ in range(30):
        try:
            engine = create_engine(settings.database_url, pool_pre_ping=True)
            Base.metadata.create_all(bind=engine)
            # samakan dengan backend: enkripsi api_key plaintext yang tersisa, dll.
            from app.db.migrate import run_migrations

            run_migrations(engine)
            return engine
        except OperationalError:
            time.sleep(2)
    raise RuntimeError("Database tidak bisa dijangkau")


def run_job(db, job: AiJob) -> None:
    provider = db.get(AiProvider, job.provider_id)
    if provider is None or not provider.is_active:
        raise RuntimeError("Provider tidak ditemukan / tidak aktif")
    try:
        api_key = decrypt_api_key(provider.api_key)
    except ValueError as e:
        raise RuntimeError(str(e))
    model = job.model or provider.default_model
    if not model:
        raise RuntimeError("Model belum dipilih untuk job ini")

    # Tahap riset: kumpulkan bahan dari forum (konfigurasi via Pengaturan AI).
    # Non-fatal: bila gagal/tidak ada key, lanjut dengan pengetahuan model.
    prompts = {
        "system": get_setting(db, "prompt.knowledge_system"),
        "user": get_setting(db, "prompt.knowledge_user"),
        "bbcode_spec": get_setting(db, "prompt.bbcode_spec"),
    }
    brief = None
    try:
        brief = research_topic(
            job.brand,
            job.phone_model,
            job.topic or job.subcategory,
            config={
                "enabled": get_setting(db, "search.enabled") == "1",
                "brave_api_key": get_setting(db, "search.brave_api_key"),
                "max_pages": get_setting(db, "search.max_pages"),
                "max_chars_per_page": get_setting(db, "search.max_chars_per_page"),
                "rules": get_setting(db, "prompt.research_rules"),
            },
        )
    except Exception as e:
        print(f"[worker] riset error (non-fatal): {e}", flush=True)

    messages = build_knowledge_prompt(
        job.brand,
        job.phone_model,
        job.category,
        job.subcategory,
        job.topic,
        research_brief=brief,
        prompts=prompts,
    )
    content = chat_complete(
        provider.base_url,
        api_key,
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
                provider.base_url, api_key, provider.embedding_model, text
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


def _similar_knowledge_exists(db, brand, phone_model, topic, days: int) -> bool:
    """Cek apakah sudah ada artikel mirip dalam N hari terakhir.

    Brand & model dicocokkan persis (case-insensitive); topik dicocokkan
    sebagai kata kunci pada judul karena isi subkategori tulisan AI
    bisa bervariasi ("root" vs "Root HP").
    """
    cutoff = datetime.now() - timedelta(days=max(1, days))
    q = select(Knowledge.id).where(Knowledge.created_at >= cutoff)
    if brand:
        q = q.where(func.lower(Knowledge.brand) == brand.lower())
    if phone_model:
        q = q.where(func.lower(Knowledge.model) == phone_model.lower())
    if topic:
        for word in topic.split():
            q = q.where(Knowledge.title.ilike(f"%{word}%"))
    return db.scalar(q.limit(1)) is not None


def _similar_job_pending(db, brand, phone_model, topic) -> bool:
    """Cek apakah sudah ada job (pending/processing) untuk target yang sama."""
    q = select(AiJob.id).where(AiJob.status.in_(["pending", "processing"]))
    if brand:
        q = q.where(func.lower(AiJob.brand) == brand.lower())
    if phone_model:
        q = q.where(func.lower(AiJob.phone_model) == phone_model.lower())
    if topic:
        q = q.where(func.lower(AiJob.subcategory) == topic.lower())
    return db.scalar(q.limit(1)) is not None


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
        dedup_days = s.dedup_days or 30
        if _similar_job_pending(db, s.brand, s.phone_model, s.topic):
            print(
                f"[worker] jadwal '{s.name}': dilewati — job serupa masih antre/diproses",
                flush=True,
            )
            s.last_run_date = today
            db.commit()
            continue
        if _similar_knowledge_exists(
            db, s.brand, s.phone_model, s.topic, dedup_days
        ):
            print(
                f"[worker] jadwal '{s.name}': dilewati — artikel mirip "
                f"sudah ada dalam {dedup_days} hari terakhir",
                flush=True,
            )
            s.last_run_date = today
            db.commit()
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


def run_log_analysis(db, run) -> None:
    """Jalankan satu analisis log: kumpulkan insiden -> minta saran ke AI."""
    run.status = "running"
    db.commit()
    now = datetime.now()
    try:
        provider = db.scalar(
            select(AiProvider)
            .where(AiProvider.is_active == True)
            .order_by(AiProvider.created_at)
            .limit(1)
        )
        if provider is None or not provider.default_model:
            raise RuntimeError("tidak ada AI provider aktif dengan default model")
        try:
            log_api_key = decrypt_api_key(provider.api_key)
        except ValueError as e:
            raise RuntimeError(str(e))
        last_done = db.scalar(
            select(LogAnalysisRun)
            .where(LogAnalysisRun.status == "done")
            .order_by(LogAnalysisRun.finished_at.desc())
            .limit(1)
        )
        since = (
            last_done.finished_at
            if last_done and last_done.finished_at
            else now - timedelta(days=7)
        )
        incidents = db.scalars(
            select(ErrorEvent)
            .where(ErrorEvent.last_seen >= since)
            .order_by(ErrorEvent.count.desc())
            .limit(LOG_ANALYSIS_MAX_INCIDENTS)
        ).all()
        run.incidents_found = len(incidents)
        if not incidents:
            run.status = "done"
            run.finished_at = now
            db.commit()
            print("[worker] analisis log: tidak ada insiden baru", flush=True)
            return
        messages = build_log_analysis_prompt(
            [
                {
                    "service": e.service,
                    "signature": e.signature,
                    "count": e.count,
                    "first_seen": e.first_seen.isoformat(),
                    "last_seen": e.last_seen.isoformat(),
                    "message": e.message or "-",
                    "traceback": (e.traceback or "-")[:2000],
                }
                for e in incidents
            ]
        )
        raw = chat_complete(
            provider.base_url,
            log_api_key,
            provider.default_model,
            messages,
            temperature=0.3,
            max_tokens=4000,
        )
        suggestions = parse_suggestions(raw)
        made = 0
        for s in suggestions:
            exists = db.scalar(
                select(AiSuggestion).where(
                    AiSuggestion.signature == s["signature"],
                    AiSuggestion.status == "open",
                )
            )
            if exists:
                continue
            ev = next(
                (e for e in incidents if e.signature == s["signature"]), incidents[0]
            )
            db.add(
                AiSuggestion(
                    signature=s["signature"],
                    service=ev.service,
                    severity=s["severity"],
                    probable_cause=s["probable_cause"],
                    suggested_fix=s["suggested_fix"],
                    status="open",
                )
            )
            made += 1
        if not suggestions:
            # output AI tidak terparse — simpan mentah agar tidak hilang
            db.add(
                AiSuggestion(
                    signature=f"digest-raw@{run.id[:8]}",
                    service="worker",
                    severity="medium",
                    probable_cause="Output AI tidak dalam format JSON yang diharapkan.",
                    suggested_fix=raw[:4000],
                    status="open",
                )
            )
            made += 1
        run.suggestions_created = made
        run.status = "done"
        run.finished_at = now
        db.commit()
        print(
            f"[worker] analisis log selesai: {len(incidents)} insiden, "
            f"{made} saran baru",
            flush=True,
        )
    except Exception as e:
        db.rollback()
        run.status = "error"
        run.error = str(e)[:1000]
        run.finished_at = datetime.now()
        db.commit()
        print(f"[worker] analisis log gagal: {e}", flush=True)


def maybe_log_analysis(db) -> None:
    """Proses run manual yang pending, atau buat digest terjadwal bila waktunya."""
    run = db.scalar(
        select(LogAnalysisRun)
        .where(LogAnalysisRun.status == "pending")
        .order_by(LogAnalysisRun.created_at)
        .limit(1)
    )
    if run is None and LOG_ANALYSIS_INTERVAL_HOURS > 0:
        last_done = db.scalar(
            select(LogAnalysisRun)
            .where(LogAnalysisRun.status == "done")
            .order_by(LogAnalysisRun.finished_at.desc())
            .limit(1)
        )
        due = True
        if last_done and last_done.finished_at:
            due = datetime.now() - last_done.finished_at >= timedelta(
                hours=LOG_ANALYSIS_INTERVAL_HOURS
            )
        if due:
            run = LogAnalysisRun(trigger="scheduled", status="pending")
            db.add(run)
            db.commit()
    if run is not None:
        run_log_analysis(db, run)


def _record_worker_error(SessionLocal, exc: BaseException) -> None:
    try:
        db = SessionLocal()
        try:
            record_error_event(
                db,
                service="worker",
                signature=exception_signature(exc),
                message=str(exc),
                tb=traceback.format_exc(),
            )
        finally:
            db.close()
    except Exception:
        pass


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
                maybe_log_analysis(db)
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
            _record_worker_error(SessionLocal, e)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
