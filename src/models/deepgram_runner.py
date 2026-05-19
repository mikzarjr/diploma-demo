import os
import requests
from dotenv import load_dotenv

load_dotenv()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")


def transcribe_deepgram(audio_path: str) -> str:
    if not DEEPGRAM_API_KEY:
        raise ValueError("DEEPGRAM_API_KEY не задан в .env")

    url = "https://api.deepgram.com/v1/listen?model=nova-3&language=ru"
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "audio/wav",
    }

    with open(audio_path, "rb") as f:
        resp = requests.post(url, headers=headers, data=f, timeout=300)

    resp.raise_for_status()
    data = resp.json()
    return data["results"]["channels"][0]["alternatives"][0]["transcript"]
