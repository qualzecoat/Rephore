"""Parser BBCode toleran untuk knowledge tutorial/guide.

Format yang didukung (lihat PLANNING.md):

    [knowledge]
    [title]...[/title]
    [meta brand="..." model="..." codes="..." category="..." ...][/meta]
    [tools]
    - alat 1
    [/tools]
    [steps]
    [step n="1"]
    [instruksi]...[/instruksi]
    [command]adb ...[/command]
    [warning]...[/warning]
    [/step]
    [/steps]
    [troubleshooting]...[/troubleshooting]
    [/knowledge]

Parser ini toleran: tag yang tidak dikenal, tidak ditutup, atau penutup tanpa
pembuka tidak menggagalkan parsing — semuanya dicatat di `warnings` agar
admin bisa memperbaiki.
"""

import re

TAG_RE = re.compile(r"\[(/?)([a-z_]+)((?:\s+[a-z_]+=\"[^\"]*\")*)\s*\]")
ATTR_RE = re.compile(r'([a-z_]+)="([^"]*)"')

# Tag yang tidak punya isi/penutup (langsung dicatat, tidak masuk stack)
VOID_TAGS = {"meta"}

KNOWN_TAGS = {
    "knowledge",
    "title",
    "meta",
    "jawaban",
    "tools",
    "steps",
    "step",
    "instruksi",
    "command",
    "warning",
    "troubleshooting",
}


class _Node:
    def __init__(self, tag: str, attrs: dict):
        self.tag = tag
        self.attrs = attrs
        self.children: list = []  # str | _Node


def _inner_text(node: "_Node") -> str:
    parts: list[str] = []
    for c in node.children:
        parts.append(c if isinstance(c, str) else _inner_text(c))
    return "".join(parts)


def _find_all(node: "_Node", tag: str) -> list["_Node"]:
    found: list[_Node] = []
    for c in node.children:
        if isinstance(c, _Node):
            if c.tag == tag:
                found.append(c)
            found.extend(_find_all(c, tag))
    return found


def parse_bbcode(text: str) -> dict:
    """Parse teks BBCode menjadi dict terstruktur + daftar warnings."""
    warnings: list[str] = []
    root = _Node("root", {})
    stack: list[_Node] = [root]
    pos = 0

    for m in TAG_RE.finditer(text):
        chunk = text[pos : m.start()]
        if chunk:
            stack[-1].children.append(chunk)

        closing, tag, raw_attrs = m.group(1), m.group(2), m.group(3)
        attrs = dict(ATTR_RE.findall(raw_attrs or ""))

        if tag not in KNOWN_TAGS:
            warnings.append(
                f"Tag tidak dikenal [{tag}] — isinya tetap diproses sebagai teks"
            )
            stack[-1].children.append(m.group(0))
            pos = m.end()
            continue

        if closing:
            idx = None
            for i in range(len(stack) - 1, 0, -1):
                if stack[i].tag == tag:
                    idx = i
                    break
            if idx is None:
                warnings.append(f"Tag penutup [/{tag}] tanpa pembuka — diabaikan")
            else:
                while len(stack) - 1 > idx:
                    unclosed = stack.pop()
                    warnings.append(
                        f"Tag [{unclosed.tag}] tidak ditutup — ditutup otomatis"
                    )
                stack.pop()
        elif tag in VOID_TAGS:
            stack[-1].children.append(_Node(tag, attrs))
        else:
            node = _Node(tag, attrs)
            stack[-1].children.append(node)
            stack.append(node)

        pos = m.end()

    if pos < len(text):
        stack[-1].children.append(text[pos:])

    while len(stack) > 1:
        unclosed = stack.pop()
        warnings.append(f"Tag [{unclosed.tag}] tidak ditutup — ditutup otomatis")

    return _to_structured(root, warnings)


def _to_structured(root: "_Node", warnings: list[str]) -> dict:
    know_nodes = _find_all(root, "knowledge")
    scope = know_nodes[0] if know_nodes else root

    title_nodes = _find_all(scope, "title")
    title = _inner_text(title_nodes[0]).strip() if title_nodes else ""

    meta_nodes = _find_all(scope, "meta")
    meta = meta_nodes[0].attrs if meta_nodes else {}
    codes = [c.strip() for c in meta.get("codes", "").split(",") if c.strip()]

    tools: list[str] = []
    for t in _find_all(scope, "tools"):
        for line in _inner_text(t).strip().splitlines():
            line = line.strip()
            if line.startswith(("-", "*")):
                line = line[1:].strip()
            if line:
                tools.append(line)

    steps: list[dict] = []
    for s in _find_all(scope, "step"):
        try:
            n = int(s.attrs.get("n", ""))
        except (ValueError, TypeError):
            n = len(steps) + 1
        instr_nodes = _find_all(s, "instruksi")
        if instr_nodes:
            instruksi = "\n".join(_inner_text(x).strip() for x in instr_nodes)
        else:
            # fallback: teks langsung di dalam [step] (di luar sub-tag)
            instruksi = "".join(
                c for c in s.children if isinstance(c, str)
            ).strip()
        commands = [
            _inner_text(x).strip()
            for x in _find_all(s, "command")
            if _inner_text(x).strip()
        ]
        step_warnings = [
            _inner_text(x).strip()
            for x in _find_all(s, "warning")
            if _inner_text(x).strip()
        ]
        steps.append(
            {
                "n": n,
                "instruksi": instruksi,
                "commands": commands,
                "warnings": step_warnings,
            }
        )

    ts_nodes = _find_all(scope, "troubleshooting")
    troubleshooting = _inner_text(ts_nodes[0]).strip() if ts_nodes else ""

    jwb_nodes = _find_all(scope, "jawaban")
    jawaban = _inner_text(jwb_nodes[0]).strip() if jwb_nodes else ""

    if not title:
        warnings.append("Judul kosong — tag [title] tidak ditemukan atau kosong")
    if not steps:
        warnings.append("Belum ada langkah — tag [step] tidak ditemukan")

    return {
        "title": title,
        "meta": {
            "brand": meta.get("brand", ""),
            "model": meta.get("model", ""),
            "codes": codes,
            "category": meta.get("category", ""),
            "subcategory": meta.get("subcategory", ""),
            "difficulty": meta.get("difficulty", ""),
            "est_time": meta.get("est_time", ""),
        },
        "tools": tools,
        "steps": steps,
        "troubleshooting": troubleshooting,
        "jawaban": jawaban,
        "warnings": warnings,
    }
