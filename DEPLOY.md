# Deploy Rephore ke VPS (Production)

Panduan ini untuk VPS Ubuntu/Debian. Arsitektur production:

- **Caddy** di depan (port 80/443): HTTPS otomatis dari Let's Encrypt,
  meneruskan `/` ke frontend dan `/api/*` ke backend
- **postgres / redis / backend / frontend / worker**: hanya di jaringan
  internal Docker, tidak diekspos ke publik

## 1. Siapkan VPS & domain

1. VPS dengan Docker & Docker Compose terinstal
   (misal Ubuntu 22.04: `curl -fsSL https://get.docker.com | sh`)
2. Arahkan DNS domain ke IP VPS (record A), misal `rephore.contoh.com`
3. Buka port 80 dan 443 di firewall VPS

## 2. Clone repo

```bash
git clone https://github.com/qualzecoat/Rephore.git
cd Rephore
```

## 3. Isi environment production

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

Edit `backend/.env`:

```
DATABASE_URL=<redacted>
REDIS_URL=redis://redis:6379/0
JWT_SECRET=<redacted>
CORS_ORIGINS=https://rephore.contoh.com
```

> `JWT_SECRET` wajib diganti dengan string acak yang panjang. Jangan pakai
> nilai dari `.env.example`.
>
> **Master key enkripsi**: API key provider AI disimpan terenkripsi di database
> memakai master key (`REPHORE_MASTER_KEY`). Bila tidak diset, master key dibuat
> otomatis dan disimpan di Docker volume `rephore-secrets`. Untuk produksi,
> disarankan generate satu key sendiri dan set di `backend/.env`, lalu **backup
> nilainya di tempat aman** — bila master key hilang, semua API key tersimpan
> tidak bisa didekripsi dan harus dimasukkan ulang. Backup volume
> `rephore-secrets` bersama backup database.

## 4. Jalankan

```bash
DOMAIN=rephore.contoh.com docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

Caddy akan menerbitkan sertifikat HTTPS otomatis (butuh beberapa detik
sampai DNS & port 80/443 bisa diakses publik).

## 5. Buat admin pertama

```bash
curl -X POST https://rephore.contoh.com/api/auth/seed-admin \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"GANTI-DENGAN-PASSWORD-KUAT"}'
```

> Endpoint ini hanya bisa dipakai sekali (saat belum ada admin).

Buka `https://rephore.contoh.com`, login sebagai admin, lalu buat user
lewat menu Admin.

## 6. Backup database (disarankan)

Tambahkan cron di VPS untuk backup harian:

```bash
# tiap jam 3 pagi, simpan dump 7 hari terakhir di ~/rephore-backup/
0 3 * * * docker exec rephore-postgres-1 pg_dump -U rephore rephore | gzip > ~/rephore-backup/rephore-$(date +\%F).sql.gz && find ~/rephore-backup -mtime +7 -delete
```

## 7. Update ke versi baru

```bash
cd Rephore
git pull
DOMAIN=rephore.contoh.com docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

## Catatan keamanan

- API key provider AI disimpan terenkripsi (Fernet) di database; master key ada
  di env `REPHORE_MASTER_KEY` atau volume `rephore-secrets`. Backup keduanya
  bersama database.
- Jangan pernah commit file `.env` yang berisi secret ke git.
