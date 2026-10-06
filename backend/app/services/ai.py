"""Client generik OpenAI-compatible untuk generate knowledge & embedding.

Mendukung provider apa pun yang mengikuti konvensi endpoint OpenAI:
Gemini (via endpoint OpenAI-compatible), OpenRouter, OpenAI, Ollama lokal, dll.
"""

import httpx

CHAT_TIMEOUT = 180.0
MODELS_TIMEOUT = 30.0
EMBED_TIMEOUT = 60.0

BBCODE_SPEC = """Format output WAJIB BBCode seperti contoh berikut. Jangan tambah
penjelasan di luar tag.

[knowledge]
[title]Judul tutorial yang jelas[/title]
[meta brand="Samsung" model="Galaxy A54" codes="SM-A546B, SM-A546E" category="hardware" subcategory="ganti LCD" difficulty="mudah|sedang|sulit" est_time="60 menit"]
[tools]
- Alat 1
- Alat 2
[/tools]
[steps]
[step n="1"]
[instruksi]Langkah detail di sini.[/instruksi]
[command]perintah adb/fastboot bila ada[/command]
[warning]Hal yang wajib diwaspadai.[/warning]
[/step]
[/steps]
[troubleshooting]Solusi bila gagal.[/troubleshooting]
[/knowledge]

Aturan:
- category hanya "hardware" atau "software".
- codes: daftar kode HP dipisah koma, kosongkan bila tidak tahu.
- Tulis instruksi yang konkret dan berurutan, minimal 3 langkah.
- Sertakan peringatan keselamatan yang relevan."""


def _headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"}


def fetch_models(base_url: str, api_key: str) -> list[str]:
    """Ambil daftar model dari {base_url}/models."""
    url = base_url.rstrip("/") + "/models"
    with httpx.Client(timeout=MODELS_TIMEOUT) as client:
        r = client.get(url, headers=_headers(api_key))
        r.raise_for_status()
        data = r.json()
    models = data.get("data", [])
    return sorted(m.get("id") for m in models if m.get("id"))


def chat_complete(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 4000,
) -> str:
    """Panggil {base_url}/chat/completions, kembalikan isi pesan."""
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    with httpx.Client(timeout=CHAT_TIMEOUT) as client:
        r = client.post(url, json=payload, headers=_headers(api_key))
        r.raise_for_status()
        data = r.json()
    return data["choices"][0]["message"]["content"]


def embed_text(base_url: str, api_key: str, model: str, text: str) -> list[float]:
    """Panggil {base_url}/embeddings, kembalikan vektor."""
    url = base_url.rstrip("/") + "/embeddings"
    with httpx.Client(timeout=EMBED_TIMEOUT) as client:
        r = client.post(
            url, json={"model": model, "input": text}, headers=_headers(api_key)
        )
        r.raise_for_status()
        data = r.json()
    return data["data"][0]["embedding"]


def build_knowledge_prompt(
    brand: str | None,
    phone_model: str | None,
    category: str | None,
    subcategory: str | None,
    topic: str | None,
) -> list[dict]:
    """Susun messages untuk generate satu knowledge servis HP."""
    target = " ".join(p for p in [brand, phone_model] if p) or "smartphone umum"
    focus = " ".join(p for p in [category, subcategory, topic] if p) or "servis umum"
    return [
        {
            "role": "system",
            "content": (
                "Kamu adalah penulis panduan servis smartphone profesional. "
                "Tulis tutorial yang akurat, aman, dan praktis dalam Bahasa Indonesia."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Buatkan tutorial servis untuk: {target}\n"
                f"Fokus: {focus}\n\n"
                "LANGKAH PERTAMA: cari tahu informasi lengkap HP ini — "
                "nama-nama pasar, SEMUA kode/varian (misal SM-A546B, SM-A546E), "
                "dan cantumkan semuanya di atribut codes pada tag [meta]. "
                "Jangan menulis tutorial sebelum info HP-nya lengkap.\n\n"
                f"{BBCODE_SPEC}\n\n"
                "Output HANYA BBCode di atas, tanpa teks pembuka/penutup."
            ),
        },
    ]


def embedding_text_for(
    title: str,
    brand: str | None,
    model: str | None,
    codes: list,
    category: str | None,
    subcategory: str | None,
    troubleshooting: str | None,
) -> str:
    parts = [
        title,
        " ".join(p for p in [brand, model] if p),
        " ".join(codes or []),
        " ".join(p for p in [category, subcategory] if p),
        troubleshooting or "",
    ]
    return "\n".join(p for p in parts if p)[:4000]
