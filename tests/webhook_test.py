from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests

BASE = os.getenv("BASE_URL", "http://localhost/main").rstrip("/")
PHONE = os.getenv("PHONE", "+11111111111")
PASSWORD = os.getenv("PASSWORD", "123")
SECRET = os.getenv(
    "TELEPHONY_WEBHOOK_SECRET",
    "300423935e2a4122d6b7c77cecacd70f9866a5ee7c82b1c154b1a35b1b84bdc4",
)
ROOT = Path(__file__).resolve().parent.parent.parent
STEREO_FILE = ROOT / "data" / "test_audio" / "stereo" / "stereo_1min.wav"
SERVER_PORT = int(os.getenv("FILE_SERVER_PORT", "8765"))
HOST_FOR_WORKER = os.getenv("HOST_FOR_WORKER", "host.docker.internal")
POLL_INTERVAL = 2.0
POLL_TIMEOUT = 600.0
TERMINAL = {"analyzed", "error"}


def serve_file_in_thread(path: Path, port: int) -> ThreadingHTTPServer:
    serve_dir = path.parent

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(serve_dir), **kwargs)

        def log_message(self, *a, **kw):
            print(f"    [http] {self.address_string()} {a[0] % a[1:]}")

    httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


def sign(body: bytes) -> str:
    mac = hmac.new(SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={mac}"


def login() -> str:
    r = requests.post(
        f"{BASE}/api/auth/login",
        json={"phone_number": PHONE, "password": PASSWORD},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def send_webhook(recording_url: str) -> dict:
    external_id = f"perf-test-{uuid.uuid4()}"
    payload = {
        "provider": "generic",
        "external_id": external_id,
        "event_type": "call_ended",
        "direction": "incoming",
        "from_number": "+79991234567",
        "to_number": "+11111111111",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "duration_sec": 76,
        "recording_url": recording_url,
        "recording_auth_header": None,
    }
    body = json.dumps(payload).encode("utf-8")
    sig = sign(body)

    print(f"    payload external_id={external_id}")
    print(f"    signature={sig[:20]}...")
    print(f"    recording_url={recording_url}")

    r = requests.post(
        f"{BASE}/api/integrations/telephony/webhook",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature": sig,
        },
        timeout=30,
    )
    print(f"    response {r.status_code}: {r.text[:200]}")
    r.raise_for_status()
    return r.json()


def poll(token: str, call_id: int) -> tuple[str, dict, float]:
    t0 = time.perf_counter()
    last = None
    while True:
        r = requests.get(
            f"{BASE}/api/calls/{call_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        body = r.json()
        st = body.get("status")
        if st != last:
            print(f"    [poll] call_id={call_id} status={st}")
            last = st
        if st in TERMINAL:
            return st, body, time.perf_counter() - t0
        if time.perf_counter() - t0 > POLL_TIMEOUT:
            return "timeout", body, time.perf_counter() - t0
        time.sleep(POLL_INTERVAL)


def verify(detail: dict) -> list[tuple[str, bool, str]]:
    checks = []

    turns = detail.get("turns") or []
    checks.append(("turns count > 0", len(turns) > 0, f"{len(turns)} turns"))

    speakers = {t.get("speaker") for t in turns if t.get("speaker")}
    checks.append((
        "exactly 2 speakers detected",
        len(speakers) == 2,
        f"speakers = {sorted(speakers)}",
    ))

    transcript = detail.get("transcript") or ""
    checks.append((
        "transcript non-empty",
        len(transcript) > 20,
        f"{len(transcript)} chars",
    ))

    results = detail.get("results") or []
    checks.append((
        "check_results created",
        len(results) >= 1,
        f"{len(results)} results",
    ))

    return checks


def main():
    print(f"  BASE_URL    = {BASE}")
    print(f"  FILE        = {STEREO_FILE}")
    print(f"  HOST_FOR_WK = {HOST_FOR_WORKER}")
    print(f"  PORT        = {SERVER_PORT}\n")

    if not STEREO_FILE.exists():
        print(f"  ERROR: {STEREO_FILE} not found")
        sys.exit(2)

    print("  [1/5] starting file server")
    httpd = serve_file_in_thread(STEREO_FILE, SERVER_PORT)
    time.sleep(0.5)

    recording_url = f"http://{HOST_FOR_WORKER}:{SERVER_PORT}/{STEREO_FILE.name}"
    print(f"        url: {recording_url}")

    try:
        print("\n  [2/5] login")
        token = login()
        print("        token OK")

        print("\n  [3/5] sending webhook")
        resp = send_webhook(recording_url)
        call_id = resp.get("call_id")
        log_id = resp.get("log_id")
        print(f"        webhook accepted: call_id={call_id} log_id={log_id}")
        if not call_id:
            print("        ERROR: no call_id in response")
            sys.exit(3)

        print("\n  [4/5] polling call status")
        status, detail, elapsed = poll(token, call_id)
        print(f"        terminal status={status} after {elapsed:.1f}s")

        print("\n  [5/5] verification")
        results = verify(detail)
        all_ok = True
        for name, ok, msg in results:
            mark = "OK " if ok else "FAIL"
            print(f"        [{mark}] {name:<32} — {msg}")
            if not ok:
                all_ok = False

        print()
        print("  " + "=" * 60)
        print(f"  RESULT: {'PASS' if all_ok else 'FAIL'} (call_id={call_id})")
        print("  " + "=" * 60)
        print()
        sys.exit(0 if all_ok else 1)

    finally:
        httpd.shutdown()


if __name__ == "__main__":
    main()
