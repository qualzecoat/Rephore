from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


# ---------- Provider ----------


class ProviderIn(BaseModel):
    name: str
    base_url: str
    api_key: str
    default_model: str = ""
    embedding_model: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4000
    is_active: bool = True


class ProviderUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    default_model: str | None = None
    embedding_model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    is_active: bool | None = None


class ProviderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    base_url: str
    # api_key sengaja tidak dikembalikan
    has_api_key: bool
    default_model: str
    embedding_model: str | None
    temperature: float
    max_tokens: int
    is_active: bool
    created_at: datetime


class PreviewModelsIn(BaseModel):
    base_url: str
    api_key: str


# ---------- Job ----------


class JobIn(BaseModel):
    provider_id: str
    model: str | None = None
    brand: str | None = None
    phone_model: str | None = None
    category: str | None = None
    subcategory: str | None = None
    topic: str | None = None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    provider_id: str
    model: str | None
    brand: str | None
    phone_model: str | None
    category: str | None
    subcategory: str | None
    topic: str | None
    status: str
    result_knowledge_id: str | None
    error: str | None
    created_at: datetime


# ---------- Schedule ----------


class ScheduleIn(BaseModel):
    name: str
    provider_id: str
    model: str | None = None
    brand: str | None = None
    phone_model: str | None = None
    category: str | None = None
    # satu topik per jadwal, misal "root"
    topic: str = ""
    run_hour: int = 2
    # anti-duplikat: lewati bila artikel mirip sudah ada dalam N hari terakhir
    dedup_days: int = 30
    is_active: bool = True


class ScheduleUpdate(BaseModel):
    name: str | None = None
    provider_id: str | None = None
    model: str | None = None
    brand: str | None = None
    phone_model: str | None = None
    category: str | None = None
    topic: str | None = None
    run_hour: int | None = None
    dedup_days: int | None = None
    is_active: bool | None = None


class ScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    provider_id: str
    model: str | None
    brand: str | None
    phone_model: str | None
    category: str | None
    topic: str | None
    run_hour: int
    dedup_days: int | None
    is_active: bool
    last_run_date: date | None
    created_at: datetime
