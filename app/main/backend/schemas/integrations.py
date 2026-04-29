from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class TelephonyWebhookPayload(BaseModel):
    provider: str = Field(..., description="Идентификатор провайдера, напр. 'generic' или 'mango'")
    external_id: str = Field(..., description="ID звонка в системе провайдера")
    event_type: Optional[str] = Field(None, description="call_ended / call_started / recording_ready …")

    direction: Optional[Literal["incoming", "outgoing"]] = None
    from_number: Optional[str] = None
    to_number: Optional[str] = None

    started_at: Optional[datetime] = None
    duration_sec: Optional[int] = None

    recording_url: Optional[str] = Field(
        None, description="Полный URL к MP3/WAV. Может быть подписанным и протухать."
    )
    recording_auth_header: Optional[str] = Field(
        None,
        description="Если провайдер требует Bearer/Basic для скачивания — кладём сюда",
    )


class WebhookAcceptedResponse(BaseModel):
    accepted: bool = True
    log_id: int
    call_id: Optional[int] = None
    status: str


class IntegrationStatusResponse(BaseModel):
    webhook_configured: bool = Field(
        ..., description="True если TELEPHONY_WEBHOOK_SECRET задан (HMAC включён)"
    )
    webhook_url: str = Field(..., description="URL для вставки в кабинет провайдера")
    max_audio_mb: int = Field(..., description="Лимит размера записи для скачивания")


class IntegrationLogResponse(BaseModel):
    id: int
    provider: str
    event_type: Optional[str] = None
    external_id: Optional[str] = None
    call_id: Optional[int] = None
    status: str
    message: Optional[str] = None
    payload: Optional[Any] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
