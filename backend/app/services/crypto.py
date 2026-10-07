"""Enkripsi API key provider saat disimpan di database (at-rest).

Memakai Fernet (AES-128-CBC + HMAC). Master key diambil dengan prioritas:
1. env REPHORE_MASTER_KEY (string Fernet key, 44 char base64)
2. file di REPHORE_MASTER_KEY_FILE (atau /app/secrets/master.key)
3. bila tidak ada: generate acak, simpan ke file (mode 0600) + warning keras

Catatan threat model: ini melindungi dari kebocoran database saja
(dump SQL, backup, akses baca DB). Bila seluruh filesystem/VPS jebol,
penyerang tetap bisa membaca master key — itu batas wajar enkripsi at-rest.
"""

import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

ENV_VAR = "REPHORE_MASTER_KEY"
FILE_ENV_VAR = "REPHORE_MASTER_KEY_FILE"
DEFAULT_KEY_FILE = Path("/app/secrets/master.key")

_cached: Fernet | None = None


def _load_or_create_key() -> bytes:
    raw = os.environ.get(ENV_VAR, "").strip()
    if raw:
        return raw.encode()
    key_file = Path(os.environ.get(FILE_ENV_VAR, "") or DEFAULT_KEY_FILE)
    if key_file.exists():
        return key_file.read_bytes().strip()
    key = Fernet.generate_key()
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_bytes(key)
    os.chmod(key_file, 0o600)
    print(
        "[crypto] PERINGATAN: REPHORE_MASTER_KEY belum diset — "
        f"master key baru dibuat di {key_file}. "
        "Untuk produksi, set REPHORE_MASTER_KEY di env dan backup nilainya; "
        "bila key hilang, API key tersimpan tidak bisa didekripsi lagi.",
        flush=True,
    )
    return key


def get_fernet() -> Fernet:
    global _cached
    if _cached is None:
        _cached = Fernet(_load_or_create_key())
    return _cached


def is_encrypted(value: str | None) -> bool:
    """Token Fernet selalu diawali 'gAAAAA' (byte versi 0x80 dalam base64)."""
    return bool(value) and value.startswith("gAAAAA")


def encrypt_api_key(plain: str | None) -> str:
    if not plain:
        return plain or ""
    if is_encrypted(plain):
        return plain  # sudah terenkripsi — jangan double-encrypt
    return get_fernet().encrypt(plain.encode()).decode()


def decrypt_api_key(token: str | None) -> str:
    if not token:
        return ""
    if not is_encrypted(token):
        # nilai lama yang belum termigrasi — pakai apa adanya
        return token
    try:
        return get_fernet().decrypt(token.encode()).decode()
    except InvalidToken as e:
        raise ValueError(
            "Gagal mendekripsi API key — master key tidak cocok. "
            "Periksa REPHORE_MASTER_KEY."
        ) from e
