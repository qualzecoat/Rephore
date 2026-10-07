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


class KnowledgeDetail(KnowledgeOut):
    content_json: dict
    # BBCode sumber
    content_markdown: str


class ParseOut(BaseModel):
    data: dict
    warnings: list[str]


class FeedbackIn(BaseModel):
    # "like" | "success"
    type: str
