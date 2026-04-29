import asyncio
import logging
from contextlib import asynccontextmanager

from celery_app import celery_app
from core.config import settings
from services.analysis import analyze_call
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from infra.storage.db.config import settings as db_settings
from infra.storage.db.models import Call
from infra.storage.s3.config import get_s3_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _task_session():
    engine = create_async_engine(db_settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    try:
        async with session_factory() as session:
            yield session
    finally:
        await engine.dispose()


@celery_app.task(
    bind=True,
    name="tasks.analyze_call",
    autoretry_for=(),
    retry_backoff=False,
    max_retries=0,
)
def analyze_call_task(self, call_id: int) -> dict:
    logger.info("analyze_call_task start: call_id=%s task_id=%s", call_id, self.request.id)

    def report(step: str, percent: int) -> None:
        self.update_state(
            state="PROGRESS",
            meta={"step": step, "percent": percent, "call_id": call_id},
        )

    try:
        report("queued", 0)
        result = asyncio.run(_run_analysis(call_id, report))
        logger.info("analyze_call_task done: call_id=%s", call_id)
        return result
    except Exception as e:
        logger.exception("analyze_call_task failed: call_id=%s", call_id)
        asyncio.run(_mark_error(call_id))
        raise e


async def _run_analysis(call_id: int, report) -> dict:
    async with _task_session() as db:
        call = (await db.execute(select(Call).where(Call.id == call_id))).scalar_one_or_none()
        if not call:
            raise RuntimeError(f"Call {call_id} not found")

        report("downloading", 5)
        s3 = get_s3_client()
        try:
            response = s3.get_object(Bucket=settings.S3_BUCKET_NAME, Key=call.audio_id)
            audio_bytes = response["Body"].read()
        except Exception as e:
            raise RuntimeError(f"S3 download failed for {call.audio_id}: {e}") from e

        metrics = await analyze_call(call, audio_bytes, db, on_progress=report)

        return {
            "call_id": call.id,
            "status": call.status,
            "manager_talk_ratio": metrics.manager_talk_ratio,
            "client_talk_ratio": metrics.client_talk_ratio,
            "interruptions": metrics.interruptions,
            "total_duration_sec": metrics.total_duration_sec,
        }


async def _mark_error(call_id: int) -> None:
    try:
        async with _task_session() as db:
            call = (await db.execute(select(Call).where(Call.id == call_id))).scalar_one_or_none()
            if call:
                call.status = "error"
                await db.commit()
    except Exception:
        logger.exception("failed to mark call as error (call_id=%s)", call_id)
