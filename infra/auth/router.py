import logging
import re
from urllib.parse import parse_qs, quote, urlparse

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
COOKIE_PATH = "/main"


def _set_auth_cookies(
        resp: Response,
        access: str,
        refresh: str | None = None,
        *,
        access_max_age: int = 60 * 60,
        refresh_max_age: int = 60 * 60 * 24 * 30,
) -> None:
    resp.set_cookie(
        ACCESS_COOKIE,
        access,
        max_age=access_max_age,
        httponly=True,
        samesite="lax",
        path=COOKIE_PATH,
    )
    if refresh is not None:
        resp.set_cookie(
            REFRESH_COOKIE,
            refresh,
            max_age=refresh_max_age,
            httponly=True,
            samesite="lax",
            path=COOKIE_PATH,
        )


from deps import get_current_user_from_bearer
from infra.storage.db.database import get_db
from infra.storage.db.models import User
from schemas import (
    AccessToken,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    UserResponse,
)
from security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_DIGITS_RE = re.compile(r"\D")


def _normalize_phone(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = _DIGITS_RE.sub("", raw)
    if not digits:
        return None
    if len(digits) == 10:
        digits = "7" + digits
    elif len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    if len(digits) < 10:
        return None
    return "+" + digits


PUBLIC_PREFIXES = (
    "/main/api/auth/login",
    "/main/api/auth/refresh",
    "/main/api/auth/logout",
    "/main/api/auth/validate",
    "/main/api/integrations/telephony",
    "/main/api/integrations/vats",
    "/main/login",
    "/main/_next",
    "/main/favicon.ico",
)


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    raw = (data.phone_number or "").strip()
    normalized = _normalize_phone(raw)
    candidates = {raw}
    if normalized:
        candidates.add(normalized)

    result = await db.execute(select(User).where(User.phone_number.in_(candidates)))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный телефон или пароль",
        )
    access = create_access_token(user.id, user.role)
    refresh_tok = create_refresh_token(user.id)
    body = LoginResponse(
        access_token=access,
        refresh_token=refresh_tok,
        user=UserResponse.model_validate(user),
    )
    resp = JSONResponse(content=body.model_dump(mode="json"))
    _set_auth_cookies(resp, access, refresh_tok)
    return resp


@router.post("/refresh", response_model=AccessToken)
async def refresh(
        request: Request,
        data: RefreshRequest | None = None,
        db: AsyncSession = Depends(get_db),
):
    refresh_tok = (
                      data.refresh_token if data and data.refresh_token else None
                  ) or request.cookies.get(REFRESH_COOKIE)
    if not refresh_tok:
        raise HTTPException(status_code=401, detail="Нет refresh токена")
    try:
        payload = decode_token(refresh_tok, expected_type="refresh")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh токен истёк")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Невалидный refresh токен")

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    access = create_access_token(user.id, user.role)
    body = AccessToken(access_token=access)
    resp = JSONResponse(content=body.model_dump(mode="json"))
    _set_auth_cookies(resp, access)
    return resp


@router.post("/logout")
async def logout():
    resp = JSONResponse(content={"detail": "ok"})
    resp.delete_cookie(ACCESS_COOKIE, path=COOKIE_PATH)
    resp.delete_cookie(REFRESH_COOKIE, path=COOKIE_PATH)
    return resp


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user_from_bearer)):
    return user


@router.get("/validate")
async def validate(request: Request):
    fwd_uri = request.headers.get("x-forwarded-uri", "")
    fwd_method = request.headers.get("x-forwarded-method", "GET").upper()
    path = fwd_uri.split("?", 1)[0]

    if fwd_method == "OPTIONS":
        return Response(status_code=200)

    if any(path.startswith(p) for p in PUBLIC_PREFIXES):
        return Response(status_code=200)

    auth_h = request.headers.get("authorization", "")
    token: str | None = None
    if auth_h.lower().startswith("bearer "):
        token = auth_h[7:].strip()

    if not token:
        token = request.cookies.get(ACCESS_COOKIE)

    if not token and "?" in fwd_uri:
        qs = parse_qs(urlparse(fwd_uri).query)
        token = (qs.get("token") or [None])[0]

    is_api = path.startswith("/main/api/")

    def _deny():
        if is_api:
            raise HTTPException(status_code=401, detail="no token")
        next_enc = quote(fwd_uri or "/", safe="")
        proto = request.headers.get("x-forwarded-proto", "http")
        host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
        location = f"{proto}://{host}/main/login?next={next_enc}" if host else f"/main/login?next={next_enc}"
        return Response(
            status_code=302,
            headers={"Location": location},
        )

    if not token:
        return _deny()

    try:
        payload = decode_token(token, expected_type="access")
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return _deny()

    return Response(
        status_code=200,
        headers={
            "X-User-Id": str(payload["sub"]),
            "X-User-Role": payload.get("role") or "manager",
        },
    )
