"""Pengaturan aplikasi generik (key -> value) dengan default di kode.

Pola pakai:
    get_setting(db, "search.enabled")        # nilai efektif: DB > env > default
    set_setting(db, "search.max_pages", "6") # validasi + enkripsi bila sensitif
    reset_setting(db, "search.max_pages")    # hapus override -> kembali default

Key yang berakhiran _api_key/_secret/_token disimpan terenkripsi (Fernet).
"""

import os

from sqlalchemy.orm import Session

from ..models.settings import AppSetting
from .ai import (
    BBCODE_SPEC,
    DEFAULT_CONSTRAINT_CHECK,
    DEFAULT_KNOWLEDGE_SYSTEM,
    DEFAULT_KNOWLEDGE_USER,
)
from .crypto import decrypt_api_key, encrypt_api_key, is_encrypted
from .research import DEFAULT_RESEARCH_RULES

SENSITIVE_SUFFIXES = ("_api_key", "_secret", "_token")


def _is_sensitive(key: str) -> bool:
    return key.endswith(SENSITIVE_SUFFIXES)


SETTING_DEFS: list[dict] = [
    {
        "key": "search.enabled",
        "section": "Riset Forum",
        "label": "Riset forum aktif",
        "desc": "Bila dimatikan, worker langsung generate tanpa riset (perilaku lama).",
        "type": "boolean",
        "default": "1",
    },
    {
        "key": "search.brave_api_key",
        "section": "Riset Forum",
        "label": "Brave Search API key",
        "desc": "Kunci API Brave Search untuk tahap riset. Bila kosong, riset dilewati.",
        "type": "password",
        "default": "",
        "env_var": "BRAVE_SEARCH_API_KEY",
    },
    {
        "key": "search.max_pages",
        "section": "Riset Forum",
        "label": "Maks. halaman di-fetch per topik",
        "desc": "Jumlah thread forum yang diambil isi penuhnya (sisanya hanya ringkasan).",
        "type": "number",
        "default": "4",
    },
    {
        "key": "search.max_chars_per_page",
        "section": "Riset Forum",
        "label": "Maks. karakter per halaman",
        "desc": "Batas teks yang diambil dari tiap halaman thread.",
        "type": "number",
        "default": "6000",
    },
    {
        "key": "prompt.knowledge_system",
        "section": "Prompt Artikel",
        "label": "System prompt penulis",
        "desc": "Peran yang diberikan ke AI penulis artikel.",
        "type": "textarea",
        "default": DEFAULT_KNOWLEDGE_SYSTEM,
        "placeholders": [],
    },
    {
        "key": "prompt.knowledge_user",
        "section": "Prompt Artikel",
        "label": "Template prompt user",
        "desc": "Variabel yang tersedia: {target}, {focus}, {bbcode_spec}. "
                "Kurung kurawal lain akan dianggap rusak dan template default dipakai.",
        "type": "textarea",
        "default": DEFAULT_KNOWLEDGE_USER,
        "placeholders": ["target", "focus", "bbcode_spec"],
    },
    {
        "key": "prompt.bbcode_spec",
        "section": "Prompt Artikel",
        "label": "Spesifikasi format BBCode",
        "desc": "Dimasukkan ke prompt via variabel {bbcode_spec}.",
        "type": "textarea",
        "default": BBCODE_SPEC,
        "placeholders": [],
    },
    {
        "key": "prompt.research_rules",
        "section": "Prompt Artikel",
        "label": "Aturan pakai bahan riset",
        "desc": "Instruksi untuk AI tentang cara memakai hasil riset forum.",
        "type": "textarea",
        "default": DEFAULT_RESEARCH_RULES,
        "placeholders": [],
    },
    {
        "key": "prompt.constraint_check",
        "section": "Prompt Artikel",
        "label": "Template prompt penilai aturan keras",
        "desc": "Dipakai worker untuk menilai — SEBELUM penulis berjalan — "
                "apakah bahan riset bisa memenuhi aturan keras jadwal. "
                "Variabel yang tersedia: {target}, {focus}, {constraint}, {brief}. "
                "Kurung kurawal lain akan dianggap rusak dan template default dipakai.",
        "type": "textarea",
        "default": DEFAULT_CONSTRAINT_CHECK,
        "placeholders": ["target", "focus", "constraint", "brief"],
    },
]

_DEFS = {d["key"]: d for d in SETTING_DEFS}


def _decrypt(key: str, value: str) -> str:
    if _is_sensitive(key) and value and is_encrypted(value):
        try:
            return decrypt_api_key(value)
        except Exception:
            pass
    return value


def get_setting(db: Session, key: str) -> str | None:
    """Nilai efektif sebuah setting: DB (terdekripsi) > env var > default kode."""
    row = db.get(AppSetting, key)
    if row is not None:
        return _decrypt(key, row.value or "")
    d = _DEFS.get(key)
    if d and d.get("env_var"):
        v = os.environ.get(d["env_var"], "").strip()
        if v:
            return v
    return d["default"] if d else None


def set_setting(db: Session, key: str, value: str) -> None:
    """Simpan override setting (validasi tipe + enkripsi bila sensitif)."""
    d = _DEFS.get(key)
    if d is None:
        raise KeyError(f"Setting tidak dikenal: {key}")
    value = (value or "").strip()
    t = d["type"]
    if t == "boolean":
        if value not in ("1", "0", "true", "false", "True", "False"):
            raise ValueError("Nilai boolean harus 1/0")
        value = "1" if value in ("1", "true", "True") else "0"
    elif t == "number":
        try:
            value = str(int(value))
        except (TypeError, ValueError):
            raise ValueError("Nilai harus berupa angka bulat")
    if _is_sensitive(key) and value:
        value = encrypt_api_key(value)
    row = db.get(AppSetting, key)
    if row is None:
        db.add(AppSetting(key=key, value=value))
    else:
        row.value = value
    db.commit()


def reset_setting(db: Session, key: str) -> None:
    """Hapus override -> kembali ke default kode (atau env var)."""
    if key not in _DEFS:
        raise KeyError(f"Setting tidak dikenal: {key}")
    row = db.get(AppSetting, key)
    if row is not None:
        db.delete(row)
        db.commit()


def describe_settings(db: Session) -> list[dict]:
    """Daftar setting untuk admin UI: metadata + nilai efektif + sumbernya."""
    out = []
    for d in SETTING_DEFS:
        key = d["key"]
        row = db.get(AppSetting, key)
        if row is not None:
            source = "db"
            is_set = True
            value = "" if d["type"] == "password" else _decrypt(key, row.value or "")
        elif d.get("env_var") and os.environ.get(d["env_var"], "").strip():
            source = "env"
            is_set = True
            value = "" if d["type"] == "password" else os.environ[d["env_var"]].strip()
        else:
            source = "default"
            is_set = False
            value = "" if d["type"] == "password" else d["default"]
        out.append(
            {
                "key": key,
                "section": d["section"],
                "label": d["label"],
                "desc": d.get("desc", ""),
                "type": d["type"],
                "placeholders": d.get("placeholders", []),
                "default": d["default"],
                "value": value,
                "is_set": is_set,
                "source": source,
            }
        )
    return out
