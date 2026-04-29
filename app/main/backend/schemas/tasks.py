from pydantic import BaseModel


class TaskStatusResponse(BaseModel):
    task_id: str
    state: str
    step: str | None = None
    percent: int | None = None
    call_id: int | None = None
    call_status: str | None = None
    result: dict | None = None
    error: str | None = None
