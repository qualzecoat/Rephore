"""Rephore backend — FastAPI entrypoint."""

import asyncio
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from .api import ai, auth, history, knowledge, logwatch, reports, search, users
from .core.config import settings
from .db.base import Base
from .db.migrate import run_migrations
from .db.session import SessionLocal, engine
from .models import ai as _ai_model  # noqa: F401 — daftarkan model
from .models import device as _device_model  # noqa: F401 — daftarkan model
from .models import knowledge as _knowledge_model  # noqa: F401 — daftarkan model
from .models import logwatch as _logwatch_model  # noqa: F401 — daftarkan model
from .models import user as _user_model  # noqa: F401 — daftarkan model
from .services.logwatch import exception_signature, normalize_path, record_error_event


async def wait_for_db(retries: int = 30, delay: float = 2.0) -> None:
    """Tunggu database siap (Postgres butuh waktu saat pertama start)."""
    for _ in range(retries):
        try:
            with engine.begin() as conn:
                # butuh untuk kolom embedding pencarian semantik
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            Base.metadata.create_all(bind=engine)
            run_migrations(engine)
            return
        except OperationalError:
            await asyncio.sleep(delay)
    raise RuntimeError("Database tidak bisa dijangkau setelah menunggu")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await wait_for_db()
    yield


# Fase 1: buat tabel otomatis. Fase berikutnya: migrasi Alembic.
app = FastAPI(title="Rephore API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(knowledge.router)
app.include_router(search.router)
app.include_router(history.router)
app.include_router(ai.router)
app.include_router(reports.router)
app.include_router(logwatch.router)


@app.middleware("http")
async def _record_server_errors(request: Request, call_next):
    """Catat exception tak tertangani & respons 5xx ke error_events (v1 log watcher)."""
    try:
        response = await call_next(request)
    except Exception as exc:
        # jangan ganggu request — catat lalu lempar lagi
        try:
            db = SessionLocal()
            try:
                record_error_event(
                    db,
                    service="backend",
                    signature=exception_signature(exc),
                    message=str(exc),
                    tb=traceback.format_exc(),
                )
            finally:
                db.close()
        except Exception:
            pass
        raise
    if response.status_code >= 500:
        try:
            db = SessionLocal()
            try:
                record_error_event(
                    db,
                    service="backend",
                    signature=(
                        f"HTTP{response.status_code} "
                        f"{request.method} {normalize_path(request.url.path)}"
                    ),
                    message=f"{request.method} {request.url.path}",
                )
            finally:
                db.close()
        except Exception:
            pass
    return response


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "rephore-backend"}
