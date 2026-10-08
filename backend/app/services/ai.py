"""Client generik OpenAI-compatible untuk generate knowledge & embedding.

Mendukung provider apa pun yang mengikuti konvensi endpoint OpenAI:
Gemini (via endpoint OpenAI-compatible), OpenRouter, OpenAI, Ollama lokal, dll.
"""

import httpx
import json
import re

CHAT_TIMEOUT = 180.0
MODELS_TIMEOUT = 30.0
EMBED_TIMEOUT = 60.0

BBCODE_SPEC = """Format output WAJIB BBCode seperti contoh berikut. Jangan tambah
penjelasan di luar tag.

[knowledge]
[title]Judul tutorial yang jelas[/title]
[meta brand="Samsung" model="Galaxy A54" codes="SM-A546B, SM-A546E" category="hardware" subcategory="ganti LCD" difficulty="mudah|sedang|sulit" est_time="60 menit"]
[jawaban]Jawaban langsung atas permintaan user (1-3 kalimat).[/jawaban]
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
- Sertakan peringatan keselamatan yang relevan.
- [jawaban] WAJIB: jawab TEPAT permintaan user termasuk batasannya
  (mis. "tanpa akun Mi", "tanpa PC") dalam 1-3 kalimat. Bila yang diminta
  TIDAK BISA dilakukan secara resmi/aman, katakan dengan jelas + alasannya,
  lalu arahkan ke alternatif terdekat. JANGAN mengarang cara yang tidak ada
  dan JANGAN menulis panduan generik yang mengabaikan batasan."""


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


DEFAULT_KNOWLEDGE_SYSTEM = (
    "Kamu adalah penulis panduan servis smartphone profesional. "
    "Tulis tutorial yang akurat, aman, dan praktis dalam Bahasa Indonesia."
)

DEFAULT_KNOWLEDGE_USER = (
    "Buatkan tutorial servis untuk: {target}\n"
    "Fokus: {focus}\n\n"
    "WAJIB: baca kembali permintaan di atas dan jawab TEPAT apa yang diminta, "
    "termasuk setiap batasan (contoh: 'tanpa akun Mi Cloud', 'tanpa PC'). "
    "Tulis jawaban langsungnya di tag [jawaban]. Bila permintaan tidak mungkin "
    "dipenuhi, nyatakan itu dengan jelas beserta alasannya + alternatif "
    "realistis — jangan mengarang dan jangan mengabaikan batasannya.\n\n"
    "LANGKAH PERTAMA: cari tahu informasi lengkap HP ini \u2014 "
    "nama-nama pasar, SEMUA kode/varian (misal SM-A546B, SM-A546E), "
    "dan cantumkan semuanya di atribut codes pada tag [meta]. "
    "Jangan menulis tutorial sebelum info HP-nya lengkap.\n\n"
    "{bbcode_spec}\n\n"
    "Output HANYA BBCode di atas, tanpa teks pembuka/penutup."
)


DEFAULT_CONSTRAINT_CHECK = (
    "Kamu adalah penilai kepatuhan yang jujur dan konservatif untuk "
    "panduan servis smartphone.\n"
    "Tugasmu: menilai apakah sebuah tutorial BISA ditulis dengan mematuhi "
    "aturan keras di bawah, berdasarkan bahan riset yang tersedia. "
    "Jangan mengarang sumber atau metode di luar bahan riset.\n\n"
    "Target: {target}\n"
    "Fokus tutorial: {focus}\n\n"
    "ATURAN KERAS:\n{constraint}\n\n"
    "BAHAN RISET:\n{brief}\n\n"
    "Jawab HANYA dengan satu objek JSON, tanpa teks lain:\n"
    "{{\"satisfiable\": true/false, \"reason\": \"penjelasan singkat, maksimal 2 kalimat\"}}\n\n"
    "Aturan penilaian:\n"
    "- \"satisfiable\": true hanya bila bahan riset menunjukkan cara yang "
    "jelas mematuhi aturan keras TANPA mengakalinya.\n"
    "- \"satisfiable\": false bila bahan riset menunjukkan aturan keras "
    "membuat tutorial tidak mungkin ditulis dengan benar (misalnya metode "
    "standarnya memang mensyaratkan hal yang dilarang aturan).\n"
    "- Bila bahan riset tidak ada atau tidak meyakinkan, jawab "
    "{{\"satisfiable\": false}} dengan reason yang menjelaskannya — "
    "lebih baik menandai daripada menulis panduan yang melanggar aturan."
)


class ConstraintUnsatisfiable(Exception):
    """Aturan keras jadwal tidak bisa dipenuhi bahan riset.

    Bukan error teknis: worker menandai job sebagai "flagged" (bukan
    "failed") agar admin meninjau alasannya, bukan mengira ada crash.
    """


def build_constraint_check_prompt(
    target: str,
    focus: str,
    constraint: str,
    brief: str | None,
    template: str | None = None,
) -> list[dict]:
    """Susun messages untuk penilai aturan keras.

    template: override dari pengaturan (prompt.constraint_check); bila
    placeholder-nya rusak, pakai default.
    """
    tpl = template or DEFAULT_CONSTRAINT_CHECK
    brief_text = brief.strip() if brief and brief.strip() else (
        "(tidak ada bahan riset — nilai secara konservatif dari topik "
        "dan pengetahuan umum saja)"
    )
    try:
        content = tpl.format(
            target=target,
            focus=focus,
            constraint=constraint.strip(),
            brief=brief_text,
        )
    except (KeyError, IndexError, ValueError):
        content = DEFAULT_CONSTRAINT_CHECK.format(
            target=target,
            focus=focus,
            constraint=constraint.strip(),
            brief=brief_text,
        )
    return [
        {
            "role": "system",
            "content": (
                "Kamu adalah penilai kepatuhan yang jujur dan konservatif. "
                "Jawab hanya dengan JSON yang diminta."
            ),
        },
        {"role": "user", "content": content},
    ]


def parse_constraint_verdict(raw: str) -> dict | None:
    """Parse output penilai -> {"satisfiable": bool, "reason": str}.

    Kembalikan None bila tidak terparse (pemanggil memutuskan fail-open
    atau fail-closed).
    """
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("satisfiable"), bool):
        return None
    return {
        "satisfiable": data["satisfiable"],
        "reason": str(data.get("reason") or "-")[:500],
    }


def evaluate_constraint(
    brief: str | None,
    constraint: str,
    target: str,
    focus: str,
    judge_template: str | None,
    chat_fn,
) -> dict:
    """Nilai apakah artikel bisa mematuhi aturan keras.

    chat_fn: callable(messages) -> str (mis. functools.partial dari
    chat_complete) — dipisah agar logika ini bisa diuji tanpa network.

    Bila output penilai tidak terparse -> anggap satisfiable (fail-open):
    penulis tetap menerima aturan keras di prompt-nya, dan semua artikel
    AI masuk antrean review admin sebelum tayang. Kegagalan parse dicetak
    ke log agar terlihat.
    """
    messages = build_constraint_check_prompt(
        target, focus, constraint, brief, template=judge_template
    )
    raw = chat_fn(messages)
    verdict = parse_constraint_verdict(raw)
    if verdict is None:
        print(
            "[worker] output penilai aturan tidak terparse, lanjut "
            "dengan aturan disuntik ke penulis: " + raw[:200],
            flush=True,
        )
        return {
            "satisfiable": True,
            "reason": "penilaian tidak terparse; aturan tetap disuntik ke penulis",
        }
    return verdict


def build_knowledge_prompt(
    brand: str | None,
    phone_model: str | None,
    category: str | None,
    subcategory: str | None,
    topic: str | None,
    research_brief: str | None = None,
    prompts: dict | None = None,
    constraint: str | None = None,
) -> list[dict]:
    """Susun messages untuk generate satu knowledge servis HP.

    research_brief: hasil tahap riset forum (boleh None -> perilaku lama).
    prompts: override template {"system", "user", "bbcode_spec"}; bila
        template user rusak (placeholder tidak dikenal), pakai default.
    constraint: aturan keras jadwal (mis. "tanpa akun Mi Cloud") — bila
        diisi, disuntik sebagai instruksi wajib di akhir prompt penulis.
    """
    target = " ".join(p for p in [brand, phone_model] if p) or "smartphone umum"
    focus = " ".join(p for p in [category, subcategory, topic] if p) or "servis umum"
    prompts = prompts or {}
    system = prompts.get("system") or DEFAULT_KNOWLEDGE_SYSTEM
    user_tpl = prompts.get("user") or DEFAULT_KNOWLEDGE_USER
    bbcode = prompts.get("bbcode_spec") or BBCODE_SPEC
    try:
        user_content = user_tpl.format(
            target=target, focus=focus, bbcode_spec=bbcode
        )
    except (KeyError, IndexError, ValueError):
        user_content = DEFAULT_KNOWLEDGE_USER.format(
            target=target, focus=focus, bbcode_spec=BBCODE_SPEC
        )
    if research_brief:
        user_content += (
            "\n\n=== BAHAN RISET DARI FORUM (WAJIB JADI ACUAN UTAMA) ===\n"
            + research_brief
        )
    if constraint and constraint.strip():
        # ditaruh paling akhir agar salience-nya tertinggi bagi penulis
        user_content += (
            "\n\n=== ATURAN KERAS (WAJIB DIPATUHI, TIDAK BOLEH DILANGGAR) ===\n"
            + constraint.strip()
            + "\nSetiap langkah tutorial WAJIB mematuhi aturan di atas. "
            "Jangan sertakan langkah apa pun yang melanggarnya, "
            "dan jangan menyarankan jalan pintas yang melanggarnya."
        )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
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
