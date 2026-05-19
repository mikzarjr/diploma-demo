from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    phone_number: str
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    name: str
    phone_number: str | None
    role: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginResponse(TokenPair):
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
