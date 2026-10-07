"""Pengaturan aplikasi generik — khusus admin.

GET  /settings       -> daftar setting + metadata + nilai efektif
PUT  /settings/{key} -> simpan override (body: {"value": "..."})
DELETE /settings/{key} -> hapus override (kembali ke default)
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..models.user import User
from ..services import settings as svc
from .deps import require_admin

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingValue(BaseModel):
    value: str = ""


@router.get("")
def list_settings(
    _: User = Depends(require_admin), db: Session = Depends(get_db)
):
    return svc.describe_settings(db)


@router.put("/{key}")
def update_setting(
    key: str,
    data: SettingValue,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    d = svc._DEFS.get(key)
    if d is None:
        raise HTTPException(status_code=404, detail="Setting tidak dikenal")
    # password kosong = biarkan nilai yang ada (jangan timpa)
    if d["type"] == "password" and not (data.value or "").strip():
        return {"ok": True, "unchanged": True}
    try:
        svc.set_setting(db, key, data.value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@router.delete("/{key}")
def reset_setting(
    key: str, _: User = Depends(require_admin), db: Session = Depends(get_db)
):
    if key not in svc._DEFS:
        raise HTTPException(status_code=404, detail="Setting tidak dikenal")
    svc.reset_setting(db, key)
    return {"ok": True}
