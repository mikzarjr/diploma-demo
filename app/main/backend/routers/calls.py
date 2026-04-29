import logging
import uuid
from datetime import datetime, timezone

from core.config import settings
from core.deps import get_current_user, get_current_user_from_query_or_header, require_head_or_admin
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from schemas.calls import (
    AnalyzeEnqueueResponse,
    CallDetailResponse,
    CallResponse,
    TranscribeRequest,
    TranscribeResponse,
    UploadResponse,
)
from services.transcription import transcribe_audio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from tasks.analysis import analyze_call_task

from infra.storage.db.database import get_db
from infra.storage.db.models import Call, User
from infra.storage.s3.config import get_s3_client

logger = logging.getLogger(__name__)

router = APIRouter()


def _can_see_all(user: User) -> bool:
    return user.role in ("admin", "head")


@router.get("/", response_model=list[CallResponse])
async def list_calls(
        status: str | None = Query(None),
        manager_id: int | None = Query(None),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
):
    query = (
        select(Call)
        .options(selectinload(Call.manager))
        .order_by(Call.created_at.desc())
    )
    if status:
        query = query.where(Call.status == status)

    if _can_see_all(user):
        if manager_id:
            query = query.where(Call.manager_id == manager_id)
    else:
        query = query.where(Call.manager_id == user.id)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    calls = result.scalars().all()
    for c in calls:
        c.manager_name = c.manager.name if c.manager else None
    return calls


@router.get("/{call_id}", response_model=CallDetailResponse)
async def get_call(
        call_id: int,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Call)
        .where(Call.id == call_id)
        .options(
            selectinload(Call.turns),
            selectinload(Call.results),
            selectinload(Call.manager),
        )
    )
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Звонок не найден")
    if not _can_see_all(user) and call.manager_id != user.id:
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    call.manager_name = call.manager.name if call.manager else None
    return call


@router.get("/audio/{audio_id}")
async def get_audio(
        audio_id: str,
        request: Request,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user_from_query_or_header),
):
    if not _can_see_all(user):
        result = await db.execute(select(Call).where(Call.audio_id == audio_id))
        call = result.scalar_one_or_none()
        if not call or call.manager_id != user.id:
            raise HTTPException(status_code=403, detail="Доступ запрещён")

    s3 = get_s3_client()

    try:
        head = s3.head_object(Bucket=settings.S3_BUCKET_NAME, Key=audio_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Аудиофайл не найден в хранилище")

    file_size = head["ContentLength"]

    ext = audio_id.rsplit(".", 1)[-1].lower() if "." in audio_id else ""
    content_types = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "ogg": "audio/ogg",
        "m4a": "audio/mp4",
        "webm": "audio/webm",
        "flac": "audio/flac",
    }
    content_type = content_types.get(ext, "audio/mpeg")

    range_header = request.headers.get("range")
    if range_header:
        range_spec = range_header.replace("bytes=", "")
        parts = range_spec.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
        end = min(end, file_size - 1)

        response = s3.get_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=audio_id,
            Range=f"bytes={start}-{end}",
        )

        return StreamingResponse(
            response["Body"],
            status_code=206,
            media_type=content_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(end - start + 1),
            },
        )

    response = s3.get_object(Bucket=settings.S3_BUCKET_NAME, Key=audio_id)

    return StreamingResponse(
        response["Body"],
        media_type=content_type,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
        },
    )


@router.delete("/{call_id}")
async def delete_call(
        call_id: int,
        db: AsyncSession = Depends(get_db),
        _user: User = Depends(require_head_or_admin),
):
    result = await db.execute(select(Call).where(Call.id == call_id))
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Звонок не найден")

    if call.audio_id:
        try:
            s3 = get_s3_client()
            s3.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=call.audio_id)
        except Exception:
            pass

    await db.delete(call)
    await db.commit()
    return {"detail": "Звонок удалён"}


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
        file: UploadFile = File(...),
        manager_id: int | None = Query(None),
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
):
    try:
        effective_manager_id = manager_id if _can_see_all(user) and manager_id else user.id

        file_id = str(uuid.uuid4())
        ext = file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else "wav"
        s3_key = f"{file_id}.{ext}"

        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Пустой файл")

        logger.info("Uploading %s (%d bytes) to bucket=%s", s3_key, len(file_bytes), settings.S3_BUCKET_NAME)

        s3 = get_s3_client()
        s3.put_object(Body=file_bytes, Bucket=settings.S3_BUCKET_NAME, Key=s3_key)

        head = s3.head_object(Bucket=settings.S3_BUCKET_NAME, Key=s3_key)
        saved_size = head["ContentLength"]
        logger.info("Verified: %s saved, size=%d", s3_key, saved_size)

        if saved_size != len(file_bytes):
            raise HTTPException(
                status_code=500,
                detail=f"Файл повреждён при загрузке: отправлено {len(file_bytes)}, сохранено {saved_size}",
            )

        new_call = Call(
            audio_id=s3_key,
            manager_id=effective_manager_id,
            status="new",
            start_time=datetime.now(timezone.utc),
            from_number="manual",
        )
        db.add(new_call)
        await db.commit()
        await db.refresh(new_call)

        return UploadResponse(call_id=new_call.id, s3_key=s3_key)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Upload failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки: {e}")


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(
        data: TranscribeRequest,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
):
    result = await db.execute(select(Call).where(Call.id == data.call_id))
    call_record = result.scalar_one_or_none()

    if not call_record:
        raise HTTPException(status_code=404, detail="Звонок не найден в БД")
    if not _can_see_all(user) and call_record.manager_id != user.id:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    s3 = get_s3_client()

    try:
        response = s3.get_object(Bucket=settings.S3_BUCKET_NAME, Key=call_record.audio_id)
        file_bytes = response["Body"].read()
    except Exception:
        raise HTTPException(status_code=404, detail="Файл не найден в S3")

    transcription = transcribe_audio(file_bytes)

    call_record.transcript = transcription
    call_record.status = "transcribed"
    await db.commit()

    return TranscribeResponse(call_id=call_record.id, text=transcription)


@router.post("/analyze", response_model=AnalyzeEnqueueResponse, status_code=202)
async def analyze(
        data: TranscribeRequest,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
):
    result = await db.execute(select(Call).where(Call.id == data.call_id))
    call_record = result.scalar_one_or_none()

    if not call_record:
        raise HTTPException(status_code=404, detail="Звонок не найден в БД")
    if not _can_see_all(user) and call_record.manager_id != user.id:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    if not call_record.audio_id:
        raise HTTPException(status_code=400, detail="У звонка нет audio_id")

    async_result = analyze_call_task.delay(call_record.id)

    call_record.status = "queued"
    call_record.task_id = async_result.id
    await db.commit()

    return AnalyzeEnqueueResponse(
        call_id=call_record.id,
        task_id=async_result.id,
        status="queued",
    )
