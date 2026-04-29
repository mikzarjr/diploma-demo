import logging
import re

import httpx
from core.config import settings
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

YANDEX_GPT_URL = settings.YANDEX_GPT_URL


class LLMRetryableError(Exception):
    """HTTP 5xx / 429 / таймаут — повторяемо."""


class LLMFatalError(Exception):
    """HTTP 4xx (кроме 429) / конфиг — повторять бесполезно."""


@retry(
    retry=retry_if_exception_type(LLMRetryableError),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def call_yandex_gpt(
        prompt: str,
        system_prompt: str = "Ты — ИИ-ассистент для анализа телефонных звонков.",
        temperature: float = 0.3,
        max_tokens: int = 1000,
) -> str:
    if not settings.YANDEX_GPT_API_KEY or not settings.YANDEX_GPT_FOLDER_ID:
        raise LLMFatalError(
            "YANDEX_GPT_API_KEY or YANDEX_GPT_FOLDER_ID not found"
        )

    model_uri = f"gpt://{settings.YANDEX_GPT_FOLDER_ID}/{settings.YANDEX_GPT_MODEL}"

    headers = {
        "Authorization": f"Api-Key {settings.YANDEX_GPT_API_KEY}",
        "Content-Type": "application/json",
    }

    body = {
        "modelUri": model_uri,
        "completionOptions": {
            "stream": False,
            "temperature": temperature,
            "maxTokens": str(max_tokens),
        },
        "messages": [
            {"role": "system", "text": system_prompt},
            {"role": "user", "text": prompt},
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(YANDEX_GPT_URL, headers=headers, json=body)
    except (httpx.TimeoutException, httpx.TransportError) as e:
        raise LLMRetryableError(f"transport/timeout: {e}") from e

    if response.status_code == 429 or response.status_code >= 500:
        raise LLMRetryableError(
            f"retryable HTTP {response.status_code}: {response.text[:200]}"
        )
    if response.status_code >= 400:
        raise LLMFatalError(
            f"fatal HTTP {response.status_code}: {response.text[:200]}"
        )

    data = response.json()

    alternatives = data.get("result", {}).get("alternatives", [])
    if alternatives:
        return alternatives[0].get("message", {}).get("text", "")

    return ""


async def identify_manager_speaker(speaker_texts: dict[str, str]) -> str | None:
    """
    Given two-or-more speaker tracks (label → concatenated text), ask LLM
    which one is the sales/support manager (employee of the company),
    and which is the customer/client.

    Returns the label of the manager track, or None if LLM can't decide.
    The diarization itself (who said what) is NOT touched here — we only
    label tracks already split by pyannote/channel VAD.
    """
    if len(speaker_texts) < 2:
        # Only one speaker — pick that one as manager by default.
        return next(iter(speaker_texts), None)

    if not settings.YANDEX_GPT_API_KEY or not settings.YANDEX_GPT_FOLDER_ID:
        logger.warning("YandexGPT not configured — skipping manager identification")
        return None

    label_lines = []
    for label, text in speaker_texts.items():
        snippet = text[:1500].strip()
        label_lines.append(f"=== {label} ===\n{snippet}")
    tracks_block = "\n\n".join(label_lines)

    labels_csv = ", ".join(speaker_texts.keys())
    prompt = (
        f"Перед тобой расшифровка телефонного звонка, разделённая по дорожкам "
        f"диаризации. Определи, какая дорожка принадлежит МЕНЕДЖЕРУ компании "
        f"(сотруднику, который консультирует/продаёт), а какие — КЛИЕНТУ "
        f"(тот, кто звонит за услугой/товаром).\n\n"
        f"Признаки менеджера: представляется от имени компании, задаёт уточняющие "
        f"вопросы по продукту, рассказывает условия, использует деловую речь.\n"
        f"Признаки клиента: задаёт вопросы как покупатель, описывает свою "
        f"проблему/потребность, может торговаться.\n\n"
        f"Дорожки:\n{tracks_block}\n\n"
        f"Ответь СТРОГО одной строкой — точным идентификатором дорожки менеджера. "
        f"Допустимые значения: {labels_csv}. Никакого пояснения."
    )

    try:
        raw = await call_yandex_gpt(
            prompt,
            system_prompt="Ты определяешь роли участников телефонного звонка.",
            temperature=0.0,
            max_tokens=20,
        )
    except (LLMRetryableError, LLMFatalError):
        logger.exception("LLM manager identification failed")
        return None

    answer = (raw or "").strip().upper()
    for label in speaker_texts:
        if label.upper() in answer:
            return label
    logger.warning(
        "LLM returned unrecognized manager label: %r (expected one of %s)",
        raw, list(speaker_texts.keys()),
    )
    return None


async def generate_summary(transcript: str, turns_text: str = "") -> str:
    dialog = turns_text[:4000] if turns_text else transcript[:4000]

    prompt = f"""
    Составь краткое резюме телефонного звонка (3-5 предложений).
    Выдели: тему разговора, ключевые договорённости, итог.
    Диалог: {dialog}
    """

    return await call_yandex_gpt(prompt)


async def run_llm_check(
        prompt_template: str,
        transcript: str,
        turns_text: str,
        output_type: str,
) -> dict:
    user_instruction = prompt_template
    user_instruction = user_instruction.replace("{{transcript}}", transcript[:4000])
    user_instruction = user_instruction.replace("{{turns}}", turns_text[:4000])
    user_instruction = user_instruction.replace("{transcript}", transcript[:4000])
    user_instruction = user_instruction.replace("{turns}", turns_text[:4000])

    dialog = turns_text[:4000] if turns_text else transcript[:4000]

    if output_type == "boolean":
        format_instruction = (
            "Ответь строго в формате:\n"
            "Первая строка: только «Да» или «Нет» (вердикт).\n"
            "Вторая строка: краткое пояснение (1-2 предложения).\n"
            "Пример:\nДа\nМенеджер поздоровался в начале разговора."
        )
    elif output_type == "score":
        format_instruction = (
            "Ответь строго в формате:\n"
            "Первая строка: только число от 0 до 10 (оценка).\n"
            "Вторая строка: краткое пояснение (1-2 предложения).\n"
            "Пример:\n7\nМенеджер хорошо провёл звонок, но не предложил дополнительные услуги."
        )
    elif output_type == "category":
        format_instruction = (
            "Ответь строго в формате:\n"
            "Первая строка: только одно слово — категория.\n"
            "Вторая строка: краткое пояснение (1-2 предложения).\n"
            "Пример:\nПозитивный\nКлиент остался доволен и договорился о следующей встрече."
        )
    else:
        format_instruction = "Дай краткий ответ."

    prompt = f"""
    Задание: {user_instruction}
    Диалог для анализа:{dialog}
    
    {format_instruction}
    """

    logger.info("LLM check prompt (%s): %d chars", output_type, len(prompt))

    raw_response = await call_yandex_gpt(prompt, temperature=0.1)

    logger.info("LLM response: %s", raw_response[:200])

    result = {
        "value_boolean": None,
        "value_score": None,
        "value_category": None,
        "raw_response": raw_response.strip(),
    }

    lines = [l.strip() for l in raw_response.strip().split("\n") if l.strip()]
    verdict = lines[0].lower().rstrip(".") if lines else ""

    if output_type == "boolean":
        result["value_boolean"] = verdict in ("да", "yes", "true", "1")

    elif output_type == "score":
        numbers = re.findall(r"\d+(?:\.\d+)?", verdict)
        if numbers:
            score = float(numbers[0])
            result["value_score"] = min(max(score, 0), 10)

    elif output_type == "category":

        result["value_category"] = lines[0].strip() if lines else raw_response.strip()

    return result
