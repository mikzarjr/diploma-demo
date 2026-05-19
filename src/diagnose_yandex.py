import os
import sys
import base64
import json
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "")
YANDEX_CLOUD_ID = os.getenv("YANDEX_CLOUD_ID", "")

AUDIO_PATH = "data/raw/openstt/asr_calls_2_val/0/00/2f29b7d43246.wav"
RECOGNIZE_URL = "https://stt.api.cloud.yandex.net/stt/v3/recognizeFileAsync"


def fail(msg: str) -> None:
    print(f"\n❌ {msg}")
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"✅ {msg}")


def step(n: int, title: str) -> None:
    print(f"\n--- Шаг {n}: {title} ---")


step(1, "Проверка .env")

if not YANDEX_API_KEY:
    fail("YANDEX_API_KEY не задан в .env")
if not YANDEX_FOLDER_ID:
    fail("YANDEX_FOLDER_ID не задан в .env")

ok(f"YANDEX_API_KEY длиной {len(YANDEX_API_KEY)} символов, начинается с {YANDEX_API_KEY[:8]}...")
ok(f"YANDEX_FOLDER_ID = {YANDEX_FOLDER_ID}")
if YANDEX_CLOUD_ID:
    ok(f"YANDEX_CLOUD_ID = {YANDEX_CLOUD_ID}")
else:
    print("ℹ️  YANDEX_CLOUD_ID не задан (необязательно, но удобно для отладки)")

step(2, "Проверка формата ключа")

if not YANDEX_API_KEY.startswith("AQVN"):
    print("⚠️  API-ключ обычно начинается с 'AQVN'. У вас другое начало —")
    print("    возможно, вы скопировали не тот тип ключа (IAM-токен / OAuth / JSON-ключ).")
else:
    ok("Префикс 'AQVN' — похоже на API-ключ.")

if len(YANDEX_API_KEY) < 30:
    fail("Ключ слишком короткий — скорее всего скопирован не полностью.")

if not YANDEX_FOLDER_ID.startswith("b1"):
    print("⚠️  Folder ID обычно начинается с 'b1'. Проверьте, что это именно folderId,")
    print("    а не cloudId или имя фолдера.")

step(3, "Проверка тестового аудио")
if not os.path.exists(AUDIO_PATH):
    fail(f"Не найден файл {AUDIO_PATH}")
ok(f"Файл найден: {AUDIO_PATH} ({os.path.getsize(AUDIO_PATH)} байт)")

step(4, "Минимальный запрос к recognizeFileAsync")

with open(AUDIO_PATH, "rb") as f:
    audio_b64 = base64.b64encode(f.read()).decode("utf-8")

headers = {
    "Authorization": f"Api-Key {YANDEX_API_KEY}",
    "x-folder-id": YANDEX_FOLDER_ID,
    "Content-Type": "application/json",
}
payload = {
    "content": audio_b64,
    "recognitionModel": {
        "model": "general",
        "audioFormat": {"containerAudio": {"containerAudioType": "WAV"}},
        "languageRestriction": {
            "restrictionType": "WHITELIST",
            "languageCode": ["ru-RU"],
        },
        "audioProcessingType": "FULL_DATA",
    },
}

try:
    resp = requests.post(RECOGNIZE_URL, headers=headers, json=payload, timeout=60)
except requests.RequestException as e:
    fail(f"Сетевая ошибка: {e}")

print(f"HTTP {resp.status_code}")
print("Тело ответа:")
print(resp.text[:1000])

step(5, "Что это значит")

if resp.status_code == 200:
    ok("Ключ работает, фолдер доступен. Можно запускать benchmark.")
    op_id = resp.json().get("id")
    print(f"Operation ID: {op_id}")
    sys.exit(0)

try:
    body = resp.json()
except json.JSONDecodeError:
    fail("Ответ не JSON — возможно, попали не на тот endpoint.")

err_msg = body.get("message", "") or body.get("error", "")

if resp.status_code == 401 or "Unknown api key" in err_msg:
    print("→ Ключ не опознан. Возможные причины:")
    print("  • Ключ выпущен в другом облаке (RU vs KZ).")
    print("  • Ключ удалён или просрочен.")
    print("  • В .env скопирован не сам ключ, а его ID.")
    print("Решение: создайте НОВЫЙ API-ключ у нужного SA и положите в .env.")

elif resp.status_code == 403 or "denied" in err_msg.lower():
    print("→ Ключ опознан, но у его сервисного аккаунта нет прав на этот фолдер.")
    print("  Проверьте по очереди:")
    print("  1. SA, которому принадлежит ЭТОТ ключ, имеет роль 'ai.speechkit-stt.user'")
    print(f"     именно на фолдер {YANDEX_FOLDER_ID}.")
    print("     ВНИМАНИЕ: имя фолдера ('default') ≠ его ID. Сравнивайте ID.")
    print("  2. Биллинг облака активен (TRIAL_ACTIVE / ACTIVE).")
    print("     Если PAYMENT_REQUIRED или SUSPENDED — будет 403 даже при верных ролях.")
    print("  3. Ключ из .env действительно выпущен у того SA, которому вы дали роли.")
    print("     Откройте SA в консоли → раздел 'API-ключи' → там должен быть ID этого ключа.")

elif resp.status_code == 400:
    print("→ Запрос некорректный (формат аудио, payload). Проверьте, что файл — настоящий WAV.")

else:
    print("→ Неожиданный код. Скопируйте вывод выше и проверьте в документации Yandex Cloud.")

sys.exit(1)
