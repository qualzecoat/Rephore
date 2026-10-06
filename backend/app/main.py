"""Rephore backend — FastAPI entrypoint (Fase 0 scaffold)."""

from fastapi import FastAPI

app = FastAPI(title="Rephore API", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "rephore-backend"}


# Fase berikutnya: routers untuk auth, knowledge, parser, devices, ai-providers
