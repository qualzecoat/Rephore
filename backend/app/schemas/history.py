from datetime import datetime

from pydantic import BaseModel


class DetectionLogIn(BaseModel):
    # "usb" | "manual"
    method: str
    vid: str | None = None
    pid: str | None = None
    label: str
    raw: dict = {}


class DetectionLogOut(BaseModel):
    id: str
    username: str
    method: str
    vid: str | None
    pid: str | None
    label: str
    created_at: datetime


class UsageOut(BaseModel):
    id: str
    username: str
    knowledge_id: str
    knowledge_title: str
    action: str
    created_at: datetime


# --- Riwayat milik user yang sedang login (tanpa username) ---


class MyDetectionOut(BaseModel):
    id: str
    method: str
    vid: str | None
    pid: str | None
    label: str
    created_at: datetime


class MyUsageOut(BaseModel):
    id: str
    knowledge_id: str
    knowledge_title: str
    action: str
    created_at: datetime


class MyFeedbackOut(BaseModel):
    id: str
    knowledge_id: str
    knowledge_title: str
    kind: str  # "like" | "success"
    created_at: datetime
