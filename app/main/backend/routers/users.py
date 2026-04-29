from core.deps import get_current_user, require_head_or_admin
from core.security import hash_password
from fastapi import APIRouter, Depends, HTTPException, Query
from schemas.users import UserCreate, UserResponse, UserUpdate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infra.storage.db.database import get_db
from infra.storage.db.models import User

router = APIRouter()


@router.post("/", response_model=UserResponse)
async def create_user(
        data: UserCreate,
        db: AsyncSession = Depends(get_db),
        _admin: User = Depends(require_head_or_admin),
):
    user = User(
        name=data.name,
        phone_number=data.phone_number,
        role=data.role,
        password_hash=hash_password(data.password) if data.password else None,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/", response_model=list[UserResponse])
async def list_users(
        role: str | None = Query(None, description="Фильтр по роли: admin / manager / head"),
        db: AsyncSession = Depends(get_db),
        _user: User = Depends(get_current_user),
):
    query = select(User).order_by(User.id)
    if role:
        query = query.where(User.role == role)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        _user: User = Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
        user_id: int,
        data: UserUpdate,
        db: AsyncSession = Depends(get_db),
        _admin: User = Depends(require_head_or_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    payload = data.model_dump(exclude_unset=True)
    if "password" in payload:
        password = payload.pop("password")
        if password:
            user.password_hash = hash_password(password)

    for field, value in payload.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}")
async def delete_user(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        _admin: User = Depends(require_head_or_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    await db.delete(user)
    await db.commit()
    return {"detail": "Пользователь удалён"}
