import os
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")

RECOGNIZE_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"


def transcribe_yandex(audio_path: str) -> str:
    if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
        raise ValueError("YANDEX_API_KEY или YANDEX_FOLDER_ID не заданы в .env")

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    resp = requests.post(
        RECOGNIZE_URL,
        params={"folderId": YANDEX_FOLDER_ID, "lang": "ru-RU", "format": "lpcm", "sampleRateHertz": 16000},
        headers={"Authorization": f"Api-Key {YANDEX_API_KEY}"},
        data=audio_bytes,
        timeout=30,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Yandex STT {resp.status_code}: {resp.text}")

    return resp.json().get("result", "")
