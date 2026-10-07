# Rephore — Planning (living doc)

> Dokumen ini adalah sumber kebenaran planning proyek. Update file ini setiap ada
> keputusan baru, jangan bikin dokumen terpisah.

## 1. Visi

Knowledge base fullstack yang **AI-agent friendly** untuk servis hardware dan
software smartphone. Knowledge bisa dimasukkan manual lewat parser, diminta ke
AI agent, atau dibuat otomatis terjadwal oleh AI agent.

## 2. Keputusan yang sudah dikunci

| Topik | Keputusan |
|---|---|
| Stack | Next.js (frontend) + FastAPI (backend), worker Python terpisah |
| Database | PostgreSQL + pgvector (pencarian semantik) |
| Queue | Redis |
| Deploy | Docker Compose di VPS |
| Format parser | BBCode-style, misal `[title]...[/title]` — gampang dikembangkan dengan tag baru |
| AI provider | Konfigurasi **generik OpenAI-compatible**: nama, API key, base URL, tombol fetch model dari base URL (`GET /models`), default model, temperature, max tokens. Mendukung Gemini, OpenRouter, OpenAI/ChatGPT, bahkan server lokal seperti Ollama |
| Deteksi HP mati | Cukup sampai level **chipset** dulu (Qualcomm EDL 9008, MediaTek preloader) via VID/PID USB |
| Role | 2 login: admin dan user. User hanya bisa dibuat oleh admin |
| Format dokumen | Semua dokumen teknis dalam bentuk Markdown (.md), bukan PDF |

## 3. Arsitektur

Monorepo, 5 service via `docker-compose.yml`:

- `frontend` — Next.js, halaman pencarian, login, dashboard admin
- `backend` — FastAPI, API + auth + parser + manajemen knowledge
- `worker` — scheduler + pemanggil AI provider untuk generate knowledge harian
- `postgres` — PostgreSQL + pgvector
- `redis` — queue & cache

## 4. Model data knowledge

Setiap knowledge disimpan ganda: **Markdown** (dibaca manusia) + **JSON terstruktur**
(dibaca AI agent) + **embedding** (pencarian semantik).

Field utama: judul, brand, model, daftar kode HP (misal `SM-A546B`), kategori
(hardware/software), subkategori (ganti LCD, flash firmware, bypass FRP, ...),
tingkat kesulitan, estimasi waktu, daftar alat, steps (tiap step: instruksi,
perintah adb/fastboot bila ada, peringatan, troubleshooting), sumber,
status review, jumlah like/success.

Tag status: `belum direview` → `sudah direview` → `ada testimoni`.
Knowledge hasil AI langsung tampil dengan tag `belum direview`.

## 5. Format parser (BBCode-style)

Tag baku v1:

```
[knowledge]
[title]...[/title]
[meta brand="..." model="..." codes="..." category="..." difficulty="..."][/meta]
[tools]...[/tools]
[steps]
[step n="1"]
[instruksi]...[/instruksi]
[command]adb ...[/command]
[warning]...[/warning]
[/step]
[/steps]
[troubleshooting]...[/troubleshooting]
[/knowledge]
```

Aturan: isi dalam tag boleh Markdown. Parser **toleran** — tag yang lupa
ditutup tidak menggagalkan parsing, tapi memunculkan warning ke admin.
Prompt untuk AI agent mewajibkan output memakai tag lengkap (mode strict).

## 6. AI provider generik

Admin mendaftarkan provider dengan field: nama, base URL, API key, lalu tombol
"fetch models" untuk mengambil daftar model dari `{base_url}/models`.
Per job (request manual / scheduler otomatis) bisa dipilih provider + model
yang berbeda, plus fallback bila provider utama gagal.

Setting detail per job: sumber daftar HP, template prompt per kategori, bahasa
output, jadwal (1 jadwal = 1 topik per hari), aturan anti-duplikat, retry policy.

## 7. Deteksi perangkat (frontend, WebUSB)

| Kondisi | Cara | Hasil |
|---|---|---|
| HP hidup, USB debugging on | ADB via WebUSB | Model + build number (pasti) |
| Mode fastboot | fastboot via WebUSB | Product/variant (pasti) |
| HP mati | VID/PID USB | Chipset saja (EDL 9008 / MTK preloader) |

Hasil deteksi disimpan sebagai data perangkat di histori user dan dipakai
untuk auto-suggest knowledge yang cocok (level model bila pasti, level
chipset bila hanya chipset).

## 8. Alur

**User:** login → pencarian (keyword / kode HP / hasil deteksi) → daftar
knowledge terkait → buka guide/tutorial → tombol like / berhasil sebagai
testimoni.

**Admin:** review & edit knowledge (antrian dari belum direview paling lama) →
buat akun user → kirim request generate ke AI / atur jadwal otomatis →
lihat histori pemakaian knowledge + data perangkat user → kelola AI provider.

## 9. Roadmap

- **Fase 0** — inisialisasi monorepo + commit pertama ✅
- **Fase 1** — auth (admin/user), manajemen user oleh admin ✅ (selesai 2026-10-06)
- **Fase 2** — CRUD knowledge + parser BBCode + tag review ✅ (selesai 2026-10-06)
  - Revisi 2026-10-07: satu artikel bisa menampilkan beberapa tag sekaligus
    (misal "belum direview" + "ada testimoni"); hapus knowledge ikut menghapus
    testimoni & histori pemakaiannya, dengan peringatan dulu bila sudah ada
    testimoni
- **Fase 3** — pencarian (keyword + ranking) + deteksi perangkat WebUSB + histori ✅ (selesai 2026-10-06)
  - Catatan: pencarian semantik pgvector sudah disiapkan kolomnya, tapi embedding
    baru diisi di Fase 4 (butuh AI provider untuk generate embedding)
- **Fase 4** — AI provider generik + request manual + scheduler otomatis ✅ (selesai 2026-10-06, revisi konsep jadwal 2026-10-06)
  - Provider OpenAI-compatible: nama, base URL, API key, tombol ambil daftar model
    dari base URL, default model, model embedding opsional, temperature, max tokens
  - Request manual: admin pilih provider + target HP, worker proses ±1 menit,
    hasil langsung masuk knowledge dengan tag belum direview
  - Scheduler: **1 jadwal = 1 topik per hari** di jam yang ditentukan. Alur tiap
    jadwal: AI riset info HP dulu (lengkap dengan kode-kode) → buat artikel
    via parser → rilis sebagai knowledge baru. Mau 2–3 artikel/hari = buat
    2–3 jadwal
  - Worker mengisi embedding bila provider punya embedding_model; pencarian
    memakai hybrid keyword + semantik (fallback keyword bila gagal)
  - Testimoni "berhasil" dibatasi 1x per user (ditegakkan di backend)
- **Fase 5** — testimoni like/berhasil + histori user + hardening deploy VPS ✅ (selesai 2026-10-06)
  - Testimoni like/berhasil: sudah ada sejak Fase 4 (tombol di halaman knowledge,
    "berhasil" dibatasi 1x per user di backend)
  - Histori user: halaman `/history` ("Riwayat saya") — deteksi perangkat,
    knowledge yang dibuka, dan testimoni yang diberikan; endpoint
    `GET /history/me/detections|usages|feedbacks`
  - Hapus jadwal: tombol Hapus muncul setelah jadwal dinonaktifkan
    (backend `DELETE /ai/schedules/{id}` sudah ada)
  - Hardening deploy: `docker-compose.prod.yml` + Caddy (HTTPS otomatis,
    `/api/*` → backend), DB/redis/backend tidak diekspos publik,
    panduan `DEPLOY.md`

## 10. Keputusan terbuka

- Reverse proxy untuk HTTPS di VPS (usulan v1: Caddy)
- Upload gambar per langkah: manual dulu di v1
- User belum bisa mengusulkan koreksi di v1 (cukup like/berhasil)
- Steps disimpan sebagai JSONB di tabel `knowledges` (usulan v1)
- API key provider AI disimpan plain di database v1 — enkripsi at-rest jadi PR berikutnya
