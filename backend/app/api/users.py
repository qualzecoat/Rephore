"""Manajemen user — hanya untuk admin."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.security import hash_password
from ..db.session import get_db
from ..models.user import User
from ..schemas.user import UserCreate, UserOut, UserUpdate
from .deps import require_admin

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    data: UserCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if data.role not in ("admin", "user"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role harus 'admin' atau 'user'",
        )
    if db.scalar(select(User).where(User.username == data.username)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username sudah dipakai",
        )
    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        role=data.role,
        created_by=admin.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=list[UserOut])
def list_users(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return list(db.scalars(select(User).order_by(User.created_at)).all())


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    data: UserUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    if data.role is not None:
        if data.role not in ("admin", "user"):
            raise HTTPException(status_code=400, detail="Role tidak valid")
        if user.id == admin.id and data.role != "admin":
            raise HTTPException(
                status_code=400, detail="Tidak bisa mencabut role admin diri sendiri"
            )
        user.role = data.role
    if data.password:
        user.password_hash = hash_password(data.password)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    if user.id == admin.id:
        raise HTTPException(
            status_code=400, detail="Tidak bisa menghapus akun sendiri"
        )
    db.delete(user)
    db.commit()
    return None
