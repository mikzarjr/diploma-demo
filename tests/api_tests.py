from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from typing import Any

import requests

BASE = os.getenv("BASE_URL", "http://localhost/main").rstrip("/")
PHONE = os.getenv("PHONE", "+11111111111")
PASSWORD = os.getenv("PASSWORD", "123")
TIMEOUT = 15


@dataclass
class TestResult:
    name: str
    ok: bool
    status: int | None
    detail: str = ""
    elapsed_ms: float = 0.0


results: list[TestResult] = []


def case(name: str, fn):
    t0 = time.perf_counter()
    try:
        status, detail = fn()
        ok = True
    except AssertionError as e:
        status, detail = None, f"FAIL: {e}"
        ok = False
    except requests.RequestException as e:
        status, detail = None, f"NETWORK: {e}"
        ok = False
    elapsed = (time.perf_counter() - t0) * 1000
    results.append(TestResult(name, ok, status, detail, elapsed))


def expect(condition: bool, msg: str):
    if not condition:
        raise AssertionError(msg)


def auth_login_ok() -> tuple[int, str]:
    r = requests.post(
        f"{BASE}/api/auth/login",
        json={"phone_number": PHONE, "password": PASSWORD},
        timeout=TIMEOUT,
    )
    expect(r.status_code == 200, f"expected 200, got {r.status_code}")
    body = r.json()
    expect("access_token" in body, "no access_token in response")
    expect("refresh_token" in body, "no refresh_token in response")
    expect(body.get("user", {}).get("role") in ("head", "admin", "manager"),
           "user.role missing or invalid")
    session["access"] = body["access_token"]
    session["refresh"] = body["refresh_token"]
    session["user"] = body["user"]
    return r.status_code, f"user={body['user']['name']} role={body['user']['role']}"


def auth_login_wrong_password() -> tuple[int, str]:
    r = requests.post(
        f"{BASE}/api/auth/login",
        json={"phone_number": PHONE, "password": "wrong_password_zzz"},
        timeout=TIMEOUT,
    )
    expect(r.status_code == 401, f"expected 401, got {r.status_code}")
    return r.status_code, "rejected as expected"


def auth_me_with_token() -> tuple[int, str]:
    r = requests.get(
        f"{BASE}/api/auth/me",
        headers={"Authorization": f"Bearer {session['access']}"},
        timeout=TIMEOUT,
    )
    expect(r.status_code == 200, f"expected 200, got {r.status_code}")
    body = r.json()
    expect(body.get("phone_number") == PHONE, "phone mismatch")
    return r.status_code, f"id={body['id']}"


def auth_me_without_token() -> tuple[int, str]:
    r = requests.get(f"{BASE}/api/auth/me", timeout=TIMEOUT)
    expect(r.status_code == 401, f"expected 401, got {r.status_code}")
    return r.status_code, "rejected"


def auth_refresh() -> tuple[int, str]:
    r = requests.post(
        f"{BASE}/api/auth/refresh",
        json={"refresh_token": session["refresh"]},
        timeout=TIMEOUT,
    )
    expect(r.status_code == 200, f"expected 200, got {r.status_code}")
    body = r.json()
    expect("access_token" in body, "no access_token")
    return r.status_code, "new token issued"


def calls_list() -> tuple[int, str]:
    r = requests.get(
        f"{BASE}/api/calls/",
        headers={"Authorization": f"Bearer {session['access']}"},
        timeout=TIMEOUT,
    )
    expect(r.status_code == 200, f"expected 200, got {r.status_code}")
    body = r.json()
    expect(isinstance(body, list), "expected list")
    if body:
        item = body[0]
        for f in ("id", "status", "created_at"):
            expect(f in item, f"missing field '{f}' in call item")
        session["sample_call_id"] = item["id"]
        session["sample_audio_id"] = item.get("audio_id")
    return r.status_code, f"{len(body)} calls"


def calls_list_no_token() -> tuple[int, str]:
    r = requests.get(f"{BASE}/api/calls/", timeout=TIMEOUT)
    expect(r.status_code == 401, f"expected 401, got {r.status_code}")
    return r.status_code, "rejected"


def calls_get_one() -> tuple[int, str]:
    cid = session.get("sample_call_id")
    if not cid:
        return 0, "SKIP: no calls in DB"
    r = requests.get(
        f"{BASE}/api/calls/{cid}",
        headers={"Authorization": f"Bearer {session['access']}"},
        timeout=TIMEOUT,
    )
    expect(r.status_code == 200, f"expected 200, got {r.status_code}")
    body = r.json()
    expect(body["id"] == cid, "id mismatch")
    expect("turns" in body or "results" in body, "missing detail fields")
    return r.status_code, f"call {cid} detail loaded"


def calls_get_not_found() -> tuple[int, str]:
    r = requests.get(
        f"{BASE}/api/calls/999999",
        headers={"Authorization": f"Bearer {session['access']}"},
        timeout=TIMEOUT,
    )
    expect(r.status_code == 404, f"expected 404, got {r.status_code}")
    return r.status_code, "404 as expected"


def calls_audio_stream() -> tuple[int, str]:
    aid = session.get("sample_audio_id")
    if not aid:
        return 0, "SKIP: no audio_id"
    r = requests.get(
        f"{BASE}/api/calls/audio/{aid}",
        headers={"Authorization": f"Bearer {session['access']}"},
        timeout=TIMEOUT,
        stream=True,
    )
    expect(r.status_code in (200, 206), f"expected 200/206, got {r.status_code}")
    ct = r.headers.get("Content-Type", "")
    expect(ct.startswith("audio/"), f"non-audio content-type: {ct}")
    return r.status_code, f"content-type={ct}"


def users_list() -> tuple[int, str]:
    r = requests.get(
        f"{BASE}/api/users/",
        headers={"Authorization": f"Bearer {session['access']}"},
        timeout=TIMEOUT,
    )
    expect(r.status_code == 200, f"expected 200, got {r.status_code}")
    body = r.json()
    expect(isinstance(body, list), "expected list")
    expect(len(body) > 0, "no users returned")
    return r.status_code, f"{len(body)} users"


def checks_list() -> tuple[int, str]:
    r = requests.get(
        f"{BASE}/api/checks/",
        headers={"Authorization": f"Bearer {session['access']}"},
        timeout=TIMEOUT,
    )
    expect(r.status_code == 200, f"expected 200, got {r.status_code}")
    body = r.json()
    expect(isinstance(body, list), "expected list")
    if body:
        session["sample_check_id"] = body[0]["id"]
    return r.status_code, f"{len(body)} checks"


def checks_get_one() -> tuple[int, str]:
    chk = session.get("sample_check_id")
    if not chk:
        return 0, "SKIP: no checks"
    r = requests.get(
        f"{BASE}/api/checks/{chk}",
        headers={"Authorization": f"Bearer {session['access']}"},
        timeout=TIMEOUT,
    )
    expect(r.status_code == 200, f"expected 200, got {r.status_code}")
    body = r.json()
    expect(body["id"] == chk, "id mismatch")
    return r.status_code, f"check {chk} loaded"


def analytics_manager_stats() -> tuple[int, str]:
    r = requests.get(
        f"{BASE}/api/analytics/manager-stats",
        headers={"Authorization": f"Bearer {session['access']}"},
        timeout=TIMEOUT,
    )
    expect(r.status_code == 200, f"expected 200, got {r.status_code}")
    return r.status_code, "ok"


def analytics_check_stats() -> tuple[int, str]:
    r = requests.get(
        f"{BASE}/api/analytics/check-stats",
        headers={"Authorization": f"Bearer {session['access']}"},
        timeout=TIMEOUT,
    )
    expect(r.status_code == 200, f"expected 200, got {r.status_code}")
    return r.status_code, "ok"


def integrations_status_rbac() -> tuple[int, str]:
    role = session["user"]["role"]
    r = requests.get(
        f"{BASE}/api/integrations/status",
        headers={"Authorization": f"Bearer {session['access']}"},
        timeout=TIMEOUT,
    )
    if role == "admin":
        expect(r.status_code == 200, f"admin expected 200, got {r.status_code}")
        return r.status_code, "admin allowed"
    expect(r.status_code == 403,
           f"non-admin expected 403, got {r.status_code}")
    return r.status_code, f"role={role} correctly rejected"


def integrations_logs_rbac() -> tuple[int, str]:
    role = session["user"]["role"]
    r = requests.get(
        f"{BASE}/api/integrations/logs",
        headers={"Authorization": f"Bearer {session['access']}"},
        timeout=TIMEOUT,
    )
    if role == "admin":
        expect(r.status_code == 200, f"admin expected 200, got {r.status_code}")
        return r.status_code, "admin allowed"
    expect(r.status_code == 403,
           f"non-admin expected 403, got {r.status_code}")
    return r.status_code, f"role={role} correctly rejected"


def webhook_unsigned_rejected() -> tuple[int, str]:
    r = requests.post(
        f"{BASE}/api/integrations/telephony/webhook",
        json={"event": "test"},
        timeout=TIMEOUT,
    )
    expect(r.status_code in (401, 403, 422),
           f"expected 401/403/422 for unsigned webhook, got {r.status_code}")
    return r.status_code, "unsigned rejected"


session: dict[str, Any] = {}

TESTS = [
    ("auth.login (correct creds)", auth_login_ok),
    ("auth.login (wrong password)", auth_login_wrong_password),
    ("auth.me (with token)", auth_me_with_token),
    ("auth.me (no token)", auth_me_without_token),
    ("auth.refresh", auth_refresh),
    ("calls.list", calls_list),
    ("calls.list (no token)", calls_list_no_token),
    ("calls.get (existing)", calls_get_one),
    ("calls.get (not found)", calls_get_not_found),
    ("calls.audio (stream)", calls_audio_stream),
    ("users.list", users_list),
    ("checks.list", checks_list),
    ("checks.get", checks_get_one),
    ("analytics.manager-stats", analytics_manager_stats),
    ("analytics.check-stats", analytics_check_stats),
    ("integrations.status (RBAC)", integrations_status_rbac),
    ("integrations.logs (RBAC)", integrations_logs_rbac),
    ("webhook (unsigned rejected)", webhook_unsigned_rejected),
]


def main():
    print(f"\n  BASE_URL = {BASE}")
    print(f"  USER     = {PHONE}\n")
    print(f"  {'TEST':<38} {'STATUS':>6}  {'TIME':>8}  DETAIL")
    print(f"  {'-' * 38} {'-' * 6}  {'-' * 8}  {'-' * 40}")

    for name, fn in TESTS:
        case(name, fn)
        r = results[-1]
        mark = "OK " if r.ok else "FAIL"
        st = str(r.status) if r.status is not None else "-"
        print(f"  {name:<38} {st:>6}  {r.elapsed_ms:>6.0f}ms  [{mark}] {r.detail}")

    passed = sum(1 for r in results if r.ok)
    failed = len(results) - passed
    print()
    print(f"  {'=' * 38}")
    print(f"  PASSED:  {passed}/{len(results)}")
    print(f"  FAILED:  {failed}/{len(results)}")
    print(f"  {'=' * 38}\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
