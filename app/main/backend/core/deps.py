import jwt
from core.security import decode_token
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infra.storage.db.database import get_db
from infra.storage.db.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/main/api/auth/login", auto_error=False)


async def _resolve_user(token: str | None, db: AsyncSession) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Нет токена авторизации",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(token, expected_type="access")
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен истёк",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )
    return user


async def get_current_user(
        token: str | None = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db),
) -> User:
    return await _resolve_user(token, db)


async def get_current_user_from_query_or_header(
        token_query: str | None = Query(None, alias="token"),
        token_header: str | None = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db),
) -> User:
    return await _resolve_user(token_header or token_query, db)


def require_roles(*allowed_roles: str):
    async def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Доступ запрещён. Требуется роль: {', '.join(allowed_roles)}",
            )
        return user

    return _checker


require_admin = require_roles("admin")
require_head_or_admin = require_roles("admin", "head")
