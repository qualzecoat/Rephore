"""Rephore backend — FastAPI entrypoint."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from .api import auth, knowledge, users
from .core.config import settings
from .db.base import Base
from .db.session import engine
from .models import knowledge as _knowledge_model  # noqa: F401 — daftarkan model
from .models import user as _user_model  # noqa: F401 — daftarkan model


async def wait_for_db(retries: int = 30, delay: float = 2.0) -> None:
    """Tunggu database siap (Postgres butuh waktu saat pertama start)."""
    for _ in range(retries):
        try:
            with engine.begin() as conn:
                # butuh untuk kolom embedding pencarian semantik
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            Base.metadata.create_all(bind=engine)
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


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "rephore-backend"}
