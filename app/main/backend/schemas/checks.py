from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CheckCreate(BaseModel):
    name: str
    description: str | None = None
    scope: str = "call"
    type: str = "rule_based"
    output_type: str = "boolean"
    weight: float = 1.0
    active: bool = True
    rule_config: dict[str, Any] | None = None
    prompt: str | None = None
    expected_format: str | None = None


class CheckUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    scope: str | None = None
    type: str | None = None
    output_type: str | None = None
    weight: float | None = None
    active: bool | None = None
    rule_config: dict[str, Any] | None = None
    prompt: str | None = None
    expected_format: str | None = None


class CheckResponse(BaseModel):
    id: int
    name: str
    description: str | None
    scope: str | None
    type: str | None
    output_type: str | None
    weight: float | None
    active: bool | None
    rule_config: dict[str, Any] | None
    prompt: str | None
    expected_format: str | None
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}
