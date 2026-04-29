import logging

from celery.result import AsyncResult
from celery_app import celery_app
from core.deps import get_current_user
from fastapi import APIRouter, Depends, HTTPException
from schemas.tasks import TaskStatusResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infra.storage.db.database import get_db
from infra.storage.db.models import Call, User

logger = logging.getLogger(__name__)

router = APIRouter()


def _can_see_all(user: User) -> bool:
    return user.role in ("admin", "head")


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def task_status(
        task_id: str,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
):
    call_result = await db.execute(select(Call).where(Call.task_id == task_id))
    call = call_result.scalar_one_or_none()

    if call and not _can_see_all(user) and call.manager_id != user.id:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    async_result: AsyncResult = AsyncResult(task_id, app=celery_app)
    state = async_result.state
    info = async_result.info

    response = TaskStatusResponse(
        task_id=task_id,
        state=state,
        call_id=call.id if call else None,
        call_status=call.status if call else None,
    )

    if state == "PROGRESS" and isinstance(info, dict):
        response.step = info.get("step")
        response.percent = info.get("percent")
        if not response.call_id:
            response.call_id = info.get("call_id")

    elif state == "SUCCESS":
        response.percent = 100
        response.step = "done"
        if isinstance(info, dict):
            response.result = info

    elif state == "FAILURE":
        response.error = str(info) if info else "Task failed"

    return response
