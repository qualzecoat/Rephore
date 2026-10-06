"""Rephore backend — FastAPI entrypoint."""

from fastapi import FastAPI

from .api import auth, users
from .db.base import Base
from .db.session import engine
from .models import user as _user_model  # noqa: F401 — daftarkan model

# Fase 1: buat tabel otomatis. Fase berikutnya: migrasi Alembic.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Rephore API", version="0.2.0")

app.include_router(auth.router)
app.include_router(users.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "rephore-backend"}
