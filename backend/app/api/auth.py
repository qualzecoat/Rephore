from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.security import create_access_token, hash_password, verify_password
from ..db.session import get_db
from ..models.user import User
from ..schemas.user import LoginIn, TokenOut, UserCreate, UserOut
from .deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/seed-admin", response_model=UserOut, status_code=201)
def seed_admin(data: UserCreate, db: Session = Depends(get_db)):
    """Buat admin pertama. Hanya bisa dipakai saat belum ada user sama sekali."""
    count = db.scalar(select(func.count()).select_from(User))
    if count and count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin sudah ada. Akun baru hanya bisa dibuat oleh admin.",
        )
    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == data.username))
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau password salah",
        )
    return TokenOut(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
