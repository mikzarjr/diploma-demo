from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

BASE = os.getenv("BASE_URL", "http://localhost/main").rstrip("/")
PHONE = os.getenv("PHONE", "+11111111111")
PASSWORD = os.getenv("PASSWORD", "123")
ROOT = Path(__file__).resolve().parent.parent.parent
AUDIO_DIR = ROOT / "data" / "test_audio" / "mono"
POLL_INTERVAL = 2.0
POLL_TIMEOUT = 600.0
TERMINAL_STATES = {"analyzed", "error"}

FILES = [
    "1min.mp3",
    "3min.mp3",
    "7min.mp3",
]


def ffprobe_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())


def login() -> str:
    r = requests.post(
        f"{BASE}/api/auth/login",
        json={"phone_number": PHONE, "password": PASSWORD},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def upload(token: str, path: Path) -> tuple[int, float]:
    t0 = time.perf_counter()
    with path.open("rb") as f:
        r = requests.post(
            f"{BASE}/api/calls/upload",
            files={"file": (path.name, f, "audio/mpeg")},
            headers={"Authorization": f"Bearer {token}"},
            timeout=120,
        )
    elapsed = time.perf_counter() - t0
    r.raise_for_status()
    return r.json()["call_id"], elapsed


def analyze(token: str, call_id: int) -> None:
    r = requests.post(
        f"{BASE}/api/calls/analyze",
        json={"call_id": call_id},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    r.raise_for_status()


def poll(token: str, call_id: int) -> tuple[str, dict, float]:
    t0 = time.perf_counter()
    last_status = None
    while True:
        r = requests.get(
            f"{BASE}/api/calls/{call_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        body = r.json()
        st = body.get("status")
        if st != last_status:
            print(f"    [poll] call_id={call_id} status={st}")
            last_status = st
        if st in TERMINAL_STATES:
            return st, body, time.perf_counter() - t0
        if time.perf_counter() - t0 > POLL_TIMEOUT:
            return "timeout", body, time.perf_counter() - t0
        time.sleep(POLL_INTERVAL)


def run_one(token: str, file_path: Path) -> dict:
    print(f"\n  → {file_path.name}")
    duration = ffprobe_duration(file_path)
    print(f"    audio duration = {duration:.2f}s")

    call_id, t_upload = upload(token, file_path)
    print(f"    upload OK call_id={call_id} ({t_upload * 1000:.0f}ms)")

    analyze(token, call_id)
    print(f"    enqueued for analysis")

    status, detail, t_process = poll(token, call_id)
    rtf = t_process / duration if duration > 0 else 0.0

    turns = len(detail.get("turns") or [])
    results = len(detail.get("results") or [])
    transcript_len = len(detail.get("transcript") or "")

    print(f"    DONE status={status} time={t_process:.1f}s RTF={rtf:.2f} turns={turns} checks={results}")

    return {
        "file": file_path.name,
        "audio_sec": round(duration, 2),
        "upload_ms": round(t_upload * 1000, 0),
        "processing_sec": round(t_process, 2),
        "rtf": round(rtf, 2),
        "status": status,
        "turns": turns,
        "checks": results,
        "transcript_chars": transcript_len,
        "call_id": call_id,
    }


def main():
    print(f"  BASE_URL = {BASE}")
    print(f"  USER     = {PHONE}")
    print(f"  AUDIO    = {AUDIO_DIR}")

    if not AUDIO_DIR.exists():
        print(f"\n  ERROR: {AUDIO_DIR} not found")
        sys.exit(2)

    paths = [AUDIO_DIR / f for f in FILES]
    missing = [p for p in paths if not p.exists()]
    if missing:
        print(f"\n  ERROR: missing files: {[p.name for p in missing]}")
        sys.exit(2)

    token = login()
    print(f"  login OK")

    rows = []
    t_total = time.perf_counter()
    for p in paths:
        try:
            rows.append(run_one(token, p))
        except Exception as e:
            print(f"    FAIL: {e}")
            rows.append({"file": p.name, "status": "fail", "error": str(e)})
    total_elapsed = time.perf_counter() - t_total

    print("\n  " + "=" * 100)
    print(f"  {'FILE':<14} {'AUDIO':>8} {'UPLOAD':>8} {'PROC':>8} {'RTF':>6} {'TURNS':>6} {'CHECKS':>7} {'STATUS':>10}")
    print(f"  {'-' * 14} {'-' * 8} {'-' * 8} {'-' * 8} {'-' * 6} {'-' * 6} {'-' * 7} {'-' * 10}")
    for r in rows:
        if r.get("status") == "fail":
            print(f"  {r['file']:<14} {'--':>8} {'--':>8} {'--':>8} {'--':>6} {'--':>6} {'--':>7} {'FAIL':>10}")
            continue
        print(f"  {r['file']:<14} {r['audio_sec']:>6.1f}s "
              f"{int(r['upload_ms']):>6}ms {r['processing_sec']:>6.1f}s "
              f"{r['rtf']:>6.2f} {r['turns']:>6} {r['checks']:>7} {r['status']:>10}")
    print(f"  {'-' * 100}")
    print(f"  TOTAL elapsed: {total_elapsed:.1f}s\n")

    out_path = Path(__file__).resolve().parent / "perf_results.json"
    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    print(f"  results → {out_path}\n")


if __name__ == "__main__":
    main()
