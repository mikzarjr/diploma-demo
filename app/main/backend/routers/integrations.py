from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from core.config import settings
from core.deps import require_admin
from fastapi import APIRouter, Depends, Form, Header, HTTPException, Query, Request
from schemas.integrations import (
    IntegrationLogResponse,
    IntegrationStatusResponse,
    TelephonyWebhookPayload,
    WebhookAcceptedResponse,
)
from services.telephony import build_webhook_url, resolve_manager, verify_hmac
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tasks.integrations import fetch_call_audio_task

from infra.storage.db.database import get_db
from infra.storage.db.models import Call, IntegrationLog, User

logger = logging.getLogger(__name__)

router = APIRouter()


_SENSITIVE_KEYS = {"recording_auth_header", "authorization", "auth_header", "password", "secret", "token"}


def _redact_payload(data):
    if isinstance(data, dict):
        return {
            k: ("***REDACTED***" if k.lower() in _SENSITIVE_KEYS and v else _redact_payload(v))
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_redact_payload(x) for x in data]
    return data


@router.post(
    "/telephony/webhook",
    response_model=WebhookAcceptedResponse,
    status_code=202,
)
async def telephony_webhook(
        request: Request,
        x_signature: Optional[str] = Header(None, alias="X-Signature"),
        db: AsyncSession = Depends(get_db),
) -> WebhookAcceptedResponse:
    body_bytes = await request.body()

    if not verify_hmac(body_bytes, x_signature, settings.TELEPHONY_WEBHOOK_SECRET):
        logger.warning("telephony webhook: invalid HMAC signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = TelephonyWebhookPayload.model_validate_json(body_bytes)
    except Exception as e:
        log = IntegrationLog(
            provider="unknown",
            event_type=None,
            external_id=None,
            status="error",
            message=f"invalid payload: {e}",
            payload=None,
        )
        db.add(log)
        await db.commit()
        raise HTTPException(status_code=422, detail=f"Invalid payload: {e}")

    log = IntegrationLog(
        provider=payload.provider,
        event_type=payload.event_type,
        external_id=payload.external_id,
        status="received",
        payload=_redact_payload(payload.model_dump(mode="json")),
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)

    existing = await db.execute(
        select(Call).where(
            Call.provider == payload.provider,
            Call.external_id == payload.external_id,
        )
    )
    existing_call = existing.scalar_one_or_none()
    if existing_call:
        log.status = "skipped"
        log.call_id = existing_call.id
        log.message = "duplicate external_id"
        await db.commit()
        logger.info(
            "telephony webhook: duplicate %s/%s → call_id=%s",
            payload.provider, payload.external_id, existing_call.id,
        )
        return WebhookAcceptedResponse(
            accepted=True,
            log_id=log.id,
            call_id=existing_call.id,
            status="skipped",
        )

    try:
        manager_id, client_number = await resolve_manager(
            payload.from_number, payload.to_number, payload.direction, db
        )

        call = Call(
            provider=payload.provider,
            external_id=payload.external_id,
            direction=payload.direction,
            from_number=payload.from_number,
            to_number=payload.to_number,
            manager_id=manager_id,
            client_id=client_number,
            start_time=payload.started_at,
            duration_sec=payload.duration_sec,
            status="new",
        )
        db.add(call)
        await db.commit()
        await db.refresh(call)

        log.call_id = call.id

        if payload.recording_url:
            fetch_call_audio_task.delay(
                call.id,
                payload.recording_url,
                payload.recording_auth_header,
                log.id,
            )
            call.status = "queued"
            log.status = "processed"
            log.message = "enqueued fetch_call_audio"
        else:
            log.status = "processed"
            log.message = "call created without recording_url (waiting)"

        await db.commit()

        logger.info(
            "telephony webhook: %s/%s → call_id=%s, manager_id=%s, recording=%s",
            payload.provider, payload.external_id, call.id, manager_id,
            bool(payload.recording_url),
        )
        return WebhookAcceptedResponse(
            accepted=True,
            log_id=log.id,
            call_id=call.id,
            status=log.status,
        )

    except Exception as e:
        logger.exception("telephony webhook: processing failed")
        log.status = "error"
        log.message = f"processing: {e}"
        await db.commit()
        return WebhookAcceptedResponse(
            accepted=True,
            log_id=log.id,
            call_id=None,
            status="error",
        )


def _parse_vats_datetime(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    try:
        if len(raw) == 16 and raw[8] == "T" and raw.endswith("Z"):
            normalized = f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}T{raw[9:11]}:{raw[11:13]}:{raw[13:15]}+00:00"
            return datetime.fromisoformat(normalized)
    except Exception:
        logger.warning("Failed to parse VATS datetime: %r", raw, exc_info=True)
    return None


@router.post(
    "/vats/webhook",
    response_model=WebhookAcceptedResponse,
    status_code=202,
)
async def vats_webhook(
        request: Request,
        cmd: Optional[str] = Form(None),
        crm_token: Optional[str] = Form(None),
        callid: Optional[str] = Form(None),
        type: Optional[str] = Form(None),
        status: Optional[str] = Form(None),
        phone: Optional[str] = Form(None),
        user: Optional[str] = Form(None),
        diversion: Optional[str] = Form(None),
        start: Optional[str] = Form(None),
        duration: Optional[int] = Form(None),
        link: Optional[str] = Form(None),
        ext: Optional[str] = Form(None),
        groupRealName: Optional[str] = Form(None),
        db: AsyncSession = Depends(get_db),
) -> WebhookAcceptedResponse:
    expected_token = settings.VATS_CRM_TOKEN
    if expected_token and crm_token != expected_token:
        logger.warning("vats webhook: invalid crm_token")
        raise HTTPException(status_code=401, detail="Invalid crm_token")

    if cmd != "history":
        logger.debug("vats webhook: cmd=%s, ignoring", cmd)
        log = IntegrationLog(
            provider="vats",
            event_type=cmd,
            external_id=callid,
            status="skipped",
            message=f"cmd={cmd} is not handled",
            payload={"cmd": cmd, "callid": callid},
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return WebhookAcceptedResponse(accepted=True, log_id=log.id, call_id=None, status="skipped")

    direction: Optional[str] = None
    from_number: Optional[str] = None
    to_number: Optional[str] = None
    if type == "in":
        direction = "incoming"
        from_number = phone
        to_number = diversion
    elif type == "out":
        direction = "outgoing"
        from_number = diversion
        to_number = phone

    payload = TelephonyWebhookPayload(
        provider="vats",
        external_id=callid or "",
        event_type="call_ended",
        direction=direction,
        from_number=from_number,
        to_number=to_number,
        started_at=_parse_vats_datetime(start),
        duration_sec=duration,
        recording_url=link,
        recording_auth_header=None,
    )

    log = IntegrationLog(
        provider="vats",
        event_type="call_ended",
        external_id=payload.external_id,
        status="received",
        payload=_redact_payload({
            "cmd": cmd, "callid": callid, "type": type, "status": status,
            "phone": phone, "user": user, "diversion": diversion,
            "start": start, "duration": duration, "link": link,
            "ext": ext, "groupRealName": groupRealName,
        }),
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)

    existing = await db.execute(
        select(Call).where(
            Call.provider == "vats",
            Call.external_id == payload.external_id,
        )
    )
    existing_call = existing.scalar_one_or_none()
    if existing_call:
        log.status = "skipped"
        log.call_id = existing_call.id
        log.message = "duplicate callid"
        await db.commit()
        return WebhookAcceptedResponse(accepted=True, log_id=log.id, call_id=existing_call.id, status="skipped")

    try:
        manager_id, client_number = await resolve_manager(
            payload.from_number, payload.to_number, payload.direction, db
        )

        call = Call(
            provider="vats",
            external_id=payload.external_id,
            direction=direction,
            from_number=payload.from_number,
            to_number=payload.to_number,
            manager_id=manager_id,
            client_id=client_number,
            start_time=payload.started_at,
            duration_sec=payload.duration_sec,
            status="new",
        )
        db.add(call)
        await db.commit()
        await db.refresh(call)
        log.call_id = call.id

        if payload.recording_url:
            fetch_call_audio_task.delay(call.id, payload.recording_url, None, log.id)
            call.status = "queued"
            log.status = "processed"
            log.message = "enqueued fetch_call_audio"
        else:
            log.status = "processed"
            log.message = "call created, no recording_url (recording may be disabled in ВАТС)"

        await db.commit()

        logger.info(
            "vats webhook: callid=%s → call_id=%s, manager_id=%s, recording=%s",
            callid, call.id, manager_id, bool(payload.recording_url),
        )
        return WebhookAcceptedResponse(accepted=True, log_id=log.id, call_id=call.id, status=log.status)

    except Exception as e:
        logger.exception("vats webhook: processing failed")
        log.status = "error"
        log.message = f"processing: {e}"
        await db.commit()
        return WebhookAcceptedResponse(accepted=True, log_id=log.id, call_id=None, status="error")


@router.get("/status", response_model=IntegrationStatusResponse)
async def integrations_status(
        _admin: User = Depends(require_admin),
) -> IntegrationStatusResponse:
    return IntegrationStatusResponse(
        webhook_configured=bool(settings.TELEPHONY_WEBHOOK_SECRET),
        webhook_url=build_webhook_url(settings.PUBLIC_BASE_URL),
        max_audio_mb=settings.TELEPHONY_MAX_AUDIO_MB,
    )


@router.get("/logs", response_model=list[IntegrationLogResponse])
async def integrations_logs(
        status: Optional[str] = Query(None, description="received / processed / skipped / error"),
        provider: Optional[str] = Query(None),
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
        db: AsyncSession = Depends(get_db),
        _admin: User = Depends(require_admin),
) -> list[IntegrationLog]:
    query = select(IntegrationLog).order_by(IntegrationLog.created_at.desc())
    if status:
        query = query.where(IntegrationLog.status == status)
    if provider:
        query = query.where(IntegrationLog.provider == provider)
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    return list(result.scalars().all())
