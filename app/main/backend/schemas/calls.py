from datetime import datetime

from pydantic import BaseModel


class TranscribeRequest(BaseModel):
    call_id: int


class UploadResponse(BaseModel):
    call_id: int
    s3_key: str


class TranscribeResponse(BaseModel):
    call_id: int
    text: str


class SpeakerTurnResponse(BaseModel):
    id: int
    speaker: str | None
    text: str | None
    t_start: float | None
    t_end: float | None

    model_config = {"from_attributes": True}


class CheckResultResponse(BaseModel):
    id: int
    check_id: int
    speaker_turn_id: int | None
    value_boolean: bool | None
    value_score: float | None
    value_category: str | None
    raw_response: str | None

    model_config = {"from_attributes": True}


class CallResponse(BaseModel):
    id: int
    audio_id: str | None
    manager_id: int | None
    manager_name: str | None = None
    client_id: str | None
    transcript: str | None
    summary: str | None
    start_time: datetime | None
    duration_sec: int | None
    status: str | None
    task_id: str | None = None
    created_at: datetime | None
    provider: str | None = None
    external_id: str | None = None
    direction: str | None = None
    from_number: str | None = None
    to_number: str | None = None

    model_config = {"from_attributes": True}


class CallDetailResponse(CallResponse):
    turns: list[SpeakerTurnResponse] = []
    results: list[CheckResultResponse] = []


class AnalyzeEnqueueResponse(BaseModel):
    call_id: int
    task_id: str
    status: str
