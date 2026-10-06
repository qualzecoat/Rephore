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

## Auth — langkah pertama

```bash
# 1. Buat admin pertama (hanya bisa saat DB masih kosong)
curl -X POST http://localhost:8000/auth/seed-admin \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"ganti-ini"}'

# 2. Login lewat http://localhost:3000/login
# 3. Admin bisa kelola user di http://localhost:3000/admin/users
```

## Status

Fase 0 — inisialisasi monorepo. Lihat `PLANNING.md` untuk roadmap lengkap.
