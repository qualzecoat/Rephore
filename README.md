# Rephore

Knowledge base fullstack yang AI-agent friendly untuk servis hardware dan software smartphone.

## Stack

- **Frontend:** Next.js (React + TypeScript)
- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL + pgvector (pencarian semantik)
- **Queue:** Redis
- **Deploy:** Docker Compose di VPS

## Struktur repo

```
rephore/
├── frontend/          # Next.js — UI user & admin
├── backend/           # FastAPI — API, auth, parser, knowledge
├── worker/            # Worker AI — generate knowledge terjadwal
├── docker-compose.yml
└── PLANNING.md         # Dokumen planning (living doc)
```

## Cara jalan (development)

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

## Status

Fase 0 — inisialisasi monorepo. Lihat `PLANNING.md` untuk roadmap lengkap.
