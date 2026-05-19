from core.deps import get_current_user, require_head_or_admin
from fastapi import APIRouter, HTTPException, Depends, Query
from schemas.checks import CheckCreate, CheckUpdate, CheckResponse
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from infra.storage.db.database import get_db
from infra.storage.db.models import Check, CheckResult, User

router = APIRouter()


def _enforce_rule_based_output_type(payload: dict) -> dict:
    if payload.get("type") == "rule_based":
        payload["output_type"] = "boolean"
    return payload


@router.post("/", response_model=CheckResponse)
async def create_check(
        data: CheckCreate,
        db: AsyncSession = Depends(get_db),
        _admin: User = Depends(require_head_or_admin),
):
    payload = _enforce_rule_based_output_type(data.model_dump())
    check = Check(**payload)
    db.add(check)
    await db.commit()
    await db.refresh(check)
    return check


@router.get("/", response_model=list[CheckResponse])
async def list_checks(
        scope: str | None = Query(None, description="call / segment"),
        type: str | None = Query(None, description="rule_based / llm_based"),
        active: bool | None = Query(None),
        db: AsyncSession = Depends(get_db),
        _user: User = Depends(get_current_user),
):
    query = select(Check).order_by(Check.id)
    if scope:
        query = query.where(Check.scope == scope)
    if type:
        query = query.where(Check.type == type)
    if active is not None:
        query = query.where(Check.active == active)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{check_id}", response_model=CheckResponse)
async def get_check(
        check_id: int,
        db: AsyncSession = Depends(get_db),
        _user: User = Depends(get_current_user),
):
    result = await db.execute(select(Check).where(Check.id == check_id))
    check = result.scalar_one_or_none()
    if not check:
        raise HTTPException(status_code=404, detail="Проверка не найдена")
    return check


@router.put("/{check_id}", response_model=CheckResponse)
async def update_check(
        check_id: int,
        data: CheckUpdate,
        db: AsyncSession = Depends(get_db),
        _admin: User = Depends(require_head_or_admin),
):
    result = await db.execute(select(Check).where(Check.id == check_id))
    check = result.scalar_one_or_none()
    if not check:
        raise HTTPException(status_code=404, detail="Проверка не найдена")

    updates = data.model_dump(exclude_unset=True)
    target_type = updates.get("type", check.type)
    if target_type == "rule_based":
        updates["output_type"] = "boolean"

    for field, value in updates.items():
        setattr(check, field, value)

    await db.commit()
    await db.refresh(check)
    return check


@router.delete("/{check_id}")
async def delete_check(
        check_id: int,
        db: AsyncSession = Depends(get_db),
        _admin: User = Depends(require_head_or_admin),
):
    result = await db.execute(select(Check).where(Check.id == check_id))
    check = result.scalar_one_or_none()
    if not check:
        raise HTTPException(status_code=404, detail="Проверка не найдена")

    await db.execute(delete(CheckResult).where(CheckResult.check_id == check_id))
    await db.delete(check)
    await db.commit()
    return {"detail": "Проверка удалена"}
