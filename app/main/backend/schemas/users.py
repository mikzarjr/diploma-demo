from datetime import datetime

from pydantic import BaseModel


class UserCreate(BaseModel):
    name: str
    phone_number: str | None = None
    role: str = "manager"
    password: str | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    phone_number: str | None = None
    role: str | None = None
    password: str | None = None


class UserResponse(BaseModel):
    id: int
    name: str
    phone_number: str | None
    role: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
