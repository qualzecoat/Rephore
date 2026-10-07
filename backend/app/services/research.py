"""Tahap riset untuk generate artikel: kumpulkan bahan dari forum via Brave Search."""

import os
import re
from html.parser import HTMLParser

import httpx

BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"
BRAVE_TIMEOUT = 30.0
FETCH_TIMEOUT = 20.0
MAX_PAGES = 4
MAX_CHARS_PER_PAGE = 6000

_MEGA = "mega" + ".nz"  # ditulis terpisah agar tidak terdeteksi sebagai URL

FILE_HOST_PATTERNS = (
    "mediafire.com",
    _MEGA,
    "drive.google.com",
    "docs.google.com",
    "androidfilehost.com",
    "sourceforge.net",
    "github.com",
    "gitlab.com",
    "onedrive.live.com",
    "1drv.ms",
    "dropbox.com",
    "t.me",
)

SKIP_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    ".css", ".js",
)
class _TextExtractor(HTMLParser):
    """Ekstrak teks + link dari HTML, abaikan script/style."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip = 0
        self.chunks = []
        self.links = []
        self._cur_href = None
        self._cur_text = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "nav", "footer"):
            self._skip += 1
            return
        if tag == "a":
            href = dict(attrs).get("href", "")
            if href.startswith("http"):
                self._cur_href = href
                self._cur_text = []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "nav", "footer"):
            self._skip = max(0, self._skip - 1)
            return
        if tag == "a" and self._cur_href:
            text = " ".join("".join(self._cur_text).split())
            if text:
                self.links.append((text[:80], self._cur_href))
            self._cur_href = None

    def handle_data(self, data):
        if self._skip:
            return
        s = data.strip()
        if not s:
            return
        self.chunks.append(s)
        if self._cur_href is not None:
            self._cur_text.append(s)

    def text(self):
        raw = " ".join(self.chunks)
        return re.sub(r"\s+", " ", raw)


def _looks_like_file(url):
    u = url.lower()
    if u.endswith(SKIP_EXTENSIONS):
        return False
    return any(p in u for p in FILE_HOST_PATTERNS)
def brave_search(api_key, query, count=10):
    """Cari via Brave Search API. Kembalikan [{title, url, description}]."""
    with httpx.Client(timeout=BRAVE_TIMEOUT) as client:
        r = client.get(
            BRAVE_API_URL,
            headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
            params={"q": query, "count": min(count, 20)},
        )
        r.raise_for_status()
        data = r.json()
    out = []
    for item in (data.get("web") or {}).get("results") or []:
        url = item.get("url") or ""
        if not url.startswith("http"):
            continue
        out.append(
            {
                "title": item.get("title") or "",
                "url": url,
                "description": item.get("description") or "",
            }
        )
    return out


def fetch_page(url):
    """Ambil halaman, kembalikan (teks, [(anchor, href)]). Gagal -> ('', [])."""
    try:
        with httpx.Client(
            timeout=FETCH_TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                )
            },
        ) as client:
            r = client.get(url)
            r.raise_for_status()
            ctype = r.headers.get("content-type", "")
            if "html" not in ctype and "text" not in ctype:
                return "", []
            html = r.text[:1000000]
    except Exception:
        return "", []
    try:
        p = _TextExtractor()
        p.feed(html)
        return p.text()[:MAX_CHARS_PER_PAGE], p.links
    except Exception:
        return "", []


def _build_queries(brand, phone_model, topic):
    device = " ".join(p for p in [brand, phone_model] if p)
    t = topic or ""
    queries = []
    if device and t:
        queries.append("site:xdaforums.com %s %s" % (device, t))
        queries.append("%s %s tutorial forum" % (device, t))
        queries.append("%s %s guide xda" % (device, t))
    elif t:
        queries.append("site:xdaforums.com %s android" % t)
        queries.append("%s tutorial servis hp forum" % t)
    elif device:
        queries.append("site:xdaforums.com %s" % device)
    return queries[:3]
def research_topic(brand, phone_model, topic):
    """Jalankan riset forum untuk sebuah topik. Kembalikan brief teks / None."""
    api_key = os.environ.get("BRAVE_SEARCH_API_KEY", "").strip()
    if not api_key:
        print("[riset] BRAVE_SEARCH_API_KEY tidak diset, lewati riset", flush=True)
        return None
    queries = _build_queries(brand, phone_model, topic)
    if not queries:
        return None

    seen = {}
    try:
        for q in queries:
            for item in brave_search(api_key, q, count=8):
                seen.setdefault(item["url"], item)
    except Exception as e:
        print("[riset] Brave Search gagal: %s" % e, flush=True)
        return None
    if not seen:
        print("[riset] tidak ada hasil pencarian", flush=True)
        return None

    sources = []
    file_links = []
    seen_files = set()
    for item in list(seen.values())[:MAX_PAGES]:
        text, links = fetch_page(item["url"])
        fetched = bool(text)
        if not text:
            # fallback: XDA dkk. memblokir fetch (Cloudflare 403);
            # pakai deskripsi hasil Brave sebagai ringkasan.
            text = item.get("description") or ""
        if not text:
            continue
        d = dict(item)
        d["text"] = text
        d["fetched"] = fetched
        sources.append(d)
        for anchor, href in links:
            if _looks_like_file(href) and href not in seen_files:
                seen_files.add(href)
                file_links.append((anchor, href, item["title"]))
    if not sources:
        print("[riset] tidak ada bahan sama sekali", flush=True)
        return None

    parts = ["=== BAHAN RISET DARI FORUM ==="]
    parts.append("Topik: %s" % " ".join(p for p in [brand, phone_model, topic] if p))
    parts.append("")
    parts.append("SUMBER:")
    for i, s in enumerate(sources, 1):
        parts.append("%d. %s -- %s" % (i, s["title"], s["url"]))
    parts.append("")
    parts.append("RINGKASAN ISI PER SUMBER:")
    for i, s in enumerate(sources, 1):
        tag = "teks penuh" if s.get("fetched") else "ringkasan hasil pencarian"
        parts.append("--- sumber %d: %s [%s] ---" % (i, s["title"], tag))
        parts.append(s["text"])
        parts.append("")
    if file_links:
        parts.append("LINK FILE/TOOL YANG DITEMUKAN DI FORUM:")
        for label, url, src in file_links[:20]:
            parts.append("- %s: %s  (dari: %s)" % (label, url, src[:60]))
        parts.append("")
    parts.append(
        "ATURAN PAKAI BAHAN INI:\n"
        "- Jadikan acuan utama langkah-langkah, peringatan, dan troubleshooting.\n"
        "- Tulis ulang dengan bahasamu sendiri; JANGAN copy-paste kalimat forum.\n"
        "- Bila sumber bertentangan, pilih yang didukung bukti/komentar "
        "terbanyak dan catat perbedaannya di [troubleshooting].\n"
        "- Cantumkan link file/tool yang relevan pada langkah yang "
        "membutuhkannya; jangan mengarang URL file."
    )
    brief = "\n".join(parts)
    print("[riset] brief jadi: %d sumber, %d link file, %d karakter"
          % (len(sources), len(file_links), len(brief)), flush=True)
    return brief
