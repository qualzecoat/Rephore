"""Kolektor & analisis log v1: saring, kelompokkan, kirim ringkas ke AI."""

import json
import re
import traceback
from datetime import datetime

from sqlalchemy import select

from ..models.logwatch import ErrorEvent

# samarkan segmen id/uuid/angka di path agar signature stabil
_ID_SEGMENT = re.compile(r"[0-9a-fA-F-]{8,}|\d+")


def normalize_path(path: str) -> str:
    return _ID_SEGMENT.sub("{id}", path)


def exception_signature(exc: BaseException) -> str:
    """Signature stabil: jenis exception + lokasi frame terakhir."""
    frames = traceback.extract_tb(exc.__traceback__)
    loc = "?"
    if frames:
        f = frames[-1]
        filename = (f.filename or "?").split("/")[-1]
        loc = f"{filename}:{f.lineno}"
    return f"{type(exc).__name__}@{loc}"


def record_error_event(
    db,
    service: str,
    signature: str,
    message: str = "",
    tb: str | None = None,
) -> None:
    """Simpan insiden (upsert per signature). Tidak boleh melempar error."""
    try:
        now = datetime.utcnow()
        ev = db.scalar(select(ErrorEvent).where(ErrorEvent.signature == signature))
        if ev is None:
            db.add(
                ErrorEvent(
                    service=service,
                    signature=signature,
                    message=message[:1000],
                    traceback=(tb or "")[:4000] or None,
                    count=1,
                    first_seen=now,
                    last_seen=now,
                )
            )
        else:
            ev.count += 1
            ev.last_seen = now
            if message and not ev.message:
                ev.message = message[:1000]
        db.commit()
    except Exception:
        db.rollback()


def build_log_analysis_prompt(incidents: list[dict]) -> list[dict]:
    """Susun prompt analisis untuk sekumpulan insiden error."""
    lines = []
    for i, inc in enumerate(incidents, 1):
        lines.append(
            f"{i}. [{inc['service']}] {inc['signature']}\n"
            f"   Terjadi {inc['count']}x, pertama {inc['first_seen']}, terakhir {inc['last_seen']}\n"
            f"   Pesan: {inc['message']}\n"
            f"   Traceback (potongan):\n{inc['traceback']}"
        )
    body = "\n\n".join(lines)
    return [
        {
            "role": "system",
            "content": (
                "Kamu adalah asisten DevOps untuk aplikasi Rephore "
                "(FastAPI + Next.js + PostgreSQL + worker Python, deploy Docker). "
                "Analisis insiden error berikut dan beri saran perbaikan yang konkret "
                "dalam Bahasa Indonesia."
            ),
        },
        {
            "role": "user",
            "content": (
                "Insiden error dari aplikasi:\n\n"
                f"{body}\n\n"
                "Untuk SETIAP insiden, berikan:\n"
                "- severity: low / medium / high\n"
                "- probable_cause: tebakan penyebab paling mungkin (1-2 kalimat)\n"
                "- suggested_fix: saran perbaikan konkret (2-4 kalimat, sebutkan "
                "nama file/fungsi bila jelas dari traceback)\n\n"
                "Output HANYA berupa JSON array dengan format:\n"
                '[{"signature": "...", "severity": "medium", '
                '"probable_cause": "...", "suggested_fix": "..."}, ...]\n'
                "Tanpa teks pembuka/penutup, tanpa markdown fence."
            ),
        },
    ]


def parse_suggestions(raw: str) -> list[dict]:
    """Parse output AI menjadi list saran. Kembalikan [] bila gagal."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    out = []
    for item in data:
        if not isinstance(item, dict) or not item.get("signature"):
            continue
        sev = str(item.get("severity", "medium")).lower()
        if sev not in ("low", "medium", "high"):
            sev = "medium"
        out.append(
            {
                "signature": str(item["signature"])[:255],
                "severity": sev,
                "probable_cause": str(item.get("probable_cause", ""))[:2000],
                "suggested_fix": str(item.get("suggested_fix", ""))[:4000],
            }
        )
    return out
