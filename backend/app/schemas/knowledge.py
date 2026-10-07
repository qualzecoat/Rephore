from datetime import datetime

from pydantic import BaseModel, ConfigDict


class KnowledgeCreate(BaseModel):
    bbcode: str
    # "manual" | "ai"
    source: str = "manual"


class KnowledgeUpdate(BaseModel):
    # kalau diisi, seluruh konten di-parse ulang dari BBCode ini
    bbcode: str | None = None
    # "belum_direview" | "sudah_direview"
    status: str | None = None


class KnowledgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    brand: str | None
    model: str | None
    codes: list[str]
    category: str | None
    subcategory: str | None
    difficulty: str | None
    est_time: str | None
    tools: list[str]
    troubleshooting: str | None
    source: str
    status: str
    # tag tampilan, bisa lebih dari satu, misal ["belum direview", "ada testimoni"]
    tags: list[str]
    like_count: int
    success_count: int
    created_at: datetime
    updated_at: datetime


class LinkIn(BaseModel):
    to_knowledge_id: str
    # "prerequisite" | "related"
    relation: str


class LinkedArticle(BaseModel):
    """Artikel yang ditautkan — untuk kotak prasyarat/terkait."""

    id: str  # id tautan (untuk hapus)
    knowledge_id: str
    title: str
    brand: str | None = None
    model: str | None = None
    relation: str


class AttachmentOut(BaseModel):
    id: str
    original_name: str
    size_bytes: int
    mime_type: str | None = None
    description: str = ""
    created_at: datetime


class KnowledgeDetail(KnowledgeOut):
    content_json: dict
    # BBCode sumber
    content_markdown: str
    prerequisites: list[LinkedArticle] = []
    required_by: list[LinkedArticle] = []
    related: list[LinkedArticle] = []
    attachments: list[AttachmentOut] = []


class KnowledgeListOut(BaseModel):
    items: list[KnowledgeOut]
    total: int
    page: int
    per_page: int


class ParseOut(BaseModel):
    data: dict
    warnings: list[str]


class FeedbackIn(BaseModel):
    # "like" | "success"
    type: str


class ReportIn(BaseModel):
    # "report" (laporkan masalah) | "suggestion" (saran perbaikan)
    kind: str
    message: str


class ReportOut(BaseModel):
    id: str
    knowledge_id: str
    knowledge_title: str
    username: str
    kind: str
    message: str
    status: str
    replies_closed: bool = False
    replies_count: int = 0
    created_at: datetime


class ReportUpdate(BaseModel):
    # "open" | "resolved"
    status: str | None = None
    replies_closed: bool | None = None


class ReplyIn(BaseModel):
    message: str


class ReplyOut(BaseModel):
    id: str
    username: str
    role: str
    message: str
    created_at: datetime
