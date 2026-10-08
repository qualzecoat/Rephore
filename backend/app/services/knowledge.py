"""Helper bersama untuk knowledge (dipakai API & worker)."""

from ..models.knowledge import Knowledge


def apply_parsed(k: Knowledge, parsed: dict, bbcode: str) -> None:
    """Terapkan hasil parse BBCode ke model Knowledge."""
    meta = parsed["meta"]
    k.title = parsed["title"]
    k.brand = meta["brand"] or None
    k.model = meta["model"] or None
    k.codes = meta["codes"]
    k.category = meta["category"] or None
    k.subcategory = meta["subcategory"] or None
    k.difficulty = meta["difficulty"] or None
    k.est_time = meta["est_time"] or None
    k.tools = parsed["tools"]
    k.troubleshooting = parsed["troubleshooting"] or None
    k.content_json = {
        "title": parsed["title"],
        "meta": meta,
        "jawaban": parsed.get("jawaban") or "",
        "tools": parsed["tools"],
        "steps": parsed["steps"],
        "troubleshooting": parsed["troubleshooting"],
    }
    k.content_markdown = bbcode
