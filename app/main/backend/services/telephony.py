from __future__ import annotations

import hashlib
import hmac
import logging
import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infra.storage.db.models import User

logger = logging.getLogger(__name__)


def verify_hmac(body_bytes: bytes, signature_header: Optional[str], secret: str) -> bool:
    if not secret:
        return True
    if not signature_header:
        return False

    sig = signature_header.strip()
    if sig.lower().startswith("sha256="):
        sig = sig[len("sha256="):]

    expected = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig.lower())


_DIGITS_RE = re.compile(r"\D")


def normalize_phone(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    digits = _DIGITS_RE.sub("", raw)
    if not digits:
        return None
    # 9991234567 -> +79991234567
    if len(digits) == 10:
        digits = "7" + digits
    # 89991234567 -> +79991234567
    elif len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    if len(digits) < 10:
        return None
    return "+" + digits


async def resolve_manager(
        from_number: Optional[str],
        to_number: Optional[str],
        direction: Optional[str],
        db: AsyncSession,
) -> tuple[Optional[int], Optional[str]]:
    from_n = normalize_phone(from_number)
    to_n = normalize_phone(to_number)

    manager_candidates: list[Optional[str]] = []
    client_number: Optional[str] = None

    if direction == "incoming":
        manager_candidates = [to_n]
        client_number = from_n
    elif direction == "outgoing":
        manager_candidates = [from_n]
        client_number = to_n
    else:
        manager_candidates = [to_n, from_n]

    for candidate in manager_candidates:
        if not candidate:
            continue
        result = await db.execute(
            select(User).where(User.phone_number == candidate, User.role == "manager")
        )
        manager = result.scalar_one_or_none()
        if manager:
            if client_number is None:
                client_number = from_n if candidate == to_n else to_n
            return manager.id, client_number

    if client_number is None:
        client_number = from_n or to_n
    return None, client_number


def build_webhook_url(public_base_url: str) -> str:
    base = public_base_url.rstrip("/")
    return f"{base}/api/integrations/telephony/webhook"
