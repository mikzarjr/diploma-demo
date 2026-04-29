import logging

import jwt
from core.deps import get_current_user
from core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from fastapi import APIRouter, Depends, HTTPException, status
from schemas.auth import AccessToken, LoginRequest, LoginResponse, RefreshRequest
from schemas.users import UserResponse
from services.telephony import normalize_phone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infra.storage.db.database import get_db
from infra.storage.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    raw = (data.phone_number or "").strip()
    normalized = normalize_phone(raw)
    candidates = {raw}
    if normalized:
        candidates.add(normalized)

    result = await db.execute(select(User).where(User.phone_number.in_(candidates)))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный телефон или пароль",
        )
    return LoginResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=AccessToken)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(data.refresh_token, expected_type="refresh")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh токен истёк")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Невалидный refresh токен")

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    return AccessToken(access_token=create_access_token(user.id, user.role))


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user
