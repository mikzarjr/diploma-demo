from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from celery_app import celery_app
from core.config import settings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from tasks.analysis import analyze_call_task

from infra.storage.db.config import settings as db_settings
from infra.storage.db.models import Call, IntegrationLog
from infra.storage.s3.config import get_s3_client

logger = logging.getLogger(__name__)

MAX_AUDIO_BYTES = settings.TELEPHONY_MAX_AUDIO_MB * 1024 * 1024


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


def _ext_from_url_or_content_type(url: str, content_type: Optional[str]) -> str:
    if content_type:
        ct = content_type.lower().split(";")[0].strip()
        mapping = {
            "audio/mpeg": "mp3",
            "audio/mp3": "mp3",
            "audio/wav": "wav",
            "audio/x-wav": "wav",
            "audio/ogg": "ogg",
            "audio/mp4": "m4a",
            "audio/webm": "webm",
            "audio/flac": "flac",
        }
        if ct in mapping:
            return mapping[ct]
    path = url.split("?", 1)[0]
    if "." in path:
        candidate = path.rsplit(".", 1)[-1].lower()
        if candidate in ("mp3", "wav", "ogg", "m4a", "webm", "flac"):
            return candidate
    return "mp3"


def _download(url: str, auth_header: Optional[str]) -> tuple[bytes, Optional[str]]:
    headers = {}
    if auth_header:
        headers["Authorization"] = auth_header

    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        with client.stream("GET", url, headers=headers) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type")
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > MAX_AUDIO_BYTES:
                    raise RuntimeError(
                        f"recording too large: >{settings.TELEPHONY_MAX_AUDIO_MB}MB"
                    )
                chunks.append(chunk)
    return b"".join(chunks), content_type


@celery_app.task(
    bind=True,
    name="tasks.fetch_call_audio",
    max_retries=3,
    default_retry_delay=30,
)
def fetch_call_audio_task(
        self,
        call_id: int,
        recording_url: str,
        auth_header: Optional[str] = None,
        log_id: Optional[int] = None,
) -> dict:
    logger.info("fetch_call_audio start: call_id=%s url=%s", call_id, recording_url)

    try:
        audio_bytes, content_type = _download(recording_url, auth_header)
    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response else None
        msg = f"provider returned HTTP {status}"
        logger.error("%s for call_id=%s", msg, call_id)
        asyncio.run(_mark_failed(call_id, log_id, msg))
        return {"call_id": call_id, "status": "error", "error": msg}
    except (httpx.TransportError, httpx.TimeoutException) as e:
        logger.warning("transient download error (call_id=%s): %s", call_id, e)
        raise self.retry(exc=e)
    except Exception as e:
        logger.exception("fetch_call_audio failed: call_id=%s", call_id)
        asyncio.run(_mark_failed(call_id, log_id, str(e)))
        return {"call_id": call_id, "status": "error", "error": str(e)}

    ext = _ext_from_url_or_content_type(recording_url, content_type)
    s3_key = f"{uuid.uuid4()}.{ext}"

    try:
        s3 = get_s3_client()
        s3.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=s3_key,
            Body=audio_bytes,
            ContentType=content_type or "audio/mpeg",
        )
        s3.head_object(Bucket=settings.S3_BUCKET_NAME, Key=s3_key)
    except Exception as e:
        logger.exception("S3 upload failed: call_id=%s", call_id)
        asyncio.run(_mark_failed(call_id, log_id, f"s3 upload: {e}"))
        raise self.retry(exc=e)

    asyncio.run(_finalize_fetch(call_id, s3_key, log_id, len(audio_bytes)))

    analyze = analyze_call_task.delay(call_id)
    logger.info(
        "fetch_call_audio done: call_id=%s s3_key=%s analyze_task=%s",
        call_id, s3_key, analyze.id,
    )

    asyncio.run(_attach_analyze_task(call_id, analyze.id))

    return {"call_id": call_id, "status": "queued", "task_id": analyze.id}


async def _finalize_fetch(
        call_id: int, s3_key: str, log_id: Optional[int], size_bytes: int
) -> None:
    async with _task_session() as db:
        call = (await db.execute(select(Call).where(Call.id == call_id))).scalar_one_or_none()
        if not call:
            logger.warning("call_id=%s vanished before finalize", call_id)
            return
        call.audio_id = s3_key
        await db.commit()

        if log_id:
            log = (await db.execute(
                select(IntegrationLog).where(IntegrationLog.id == log_id)
            )).scalar_one_or_none()
            if log:
                log.status = "processed"
                log.message = f"downloaded {size_bytes} bytes → {s3_key}"
                await db.commit()


async def _attach_analyze_task(call_id: int, analyze_task_id: str) -> None:
    async with _task_session() as db:
        call = (await db.execute(select(Call).where(Call.id == call_id))).scalar_one_or_none()
        if not call:
            return
        call.task_id = analyze_task_id
        call.status = "queued"
        await db.commit()


async def _mark_failed(call_id: int, log_id: Optional[int], message: str) -> None:
    async with _task_session() as db:
        call = (await db.execute(select(Call).where(Call.id == call_id))).scalar_one_or_none()
        if call:
            call.status = "error"
            await db.commit()
        if log_id:
            log = (await db.execute(
                select(IntegrationLog).where(IntegrationLog.id == log_id)
            )).scalar_one_or_none()
            if log:
                log.status = "error"
                log.message = message
                await db.commit()
