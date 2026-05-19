import json
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
    pass


class LLMFatalError(Exception):
    pass


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
        raise LLMFatalError("YANDEX_GPT_API_KEY or YANDEX_GPT_FOLDER_ID not found")

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
        raise LLMRetryableError(f"retryable HTTP {response.status_code}: {response.text[:200]}")
    if response.status_code >= 400:
        raise LLMFatalError(f"fatal HTTP {response.status_code}: {response.text[:200]}")

    data = response.json()
    alternatives = data.get("result", {}).get("alternatives", [])
    if alternatives:
        return alternatives[0].get("message", {}).get("text", "")
    return ""


async def identify_manager_speaker(speaker_texts: dict[str, str]) -> str | None:
    if len(speaker_texts) < 2:
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
        f"Перед тобой расшифровка телефонного звонка, разделённая по дорожкам. "
        f"Определи, какая дорожка принадлежит МЕНЕДЖЕРУ компании (сотруднику, "
        f"который консультирует/продаёт), а какие — КЛИЕНТУ.\n\n"
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
    logger.warning("LLM returned unrecognized manager label: %r", raw)
    return None


async def generate_summary(transcript: str, turns_text: str = "") -> str:
    dialog = turns_text[:4000] if turns_text else transcript[:4000]
    prompt = (
        f"Составь краткое резюме телефонного звонка (3-5 предложений). "
        f"Выдели: тему разговора, ключевые договорённости, итог.\n"
        f"Диалог: {dialog}"
    )
    return await call_yandex_gpt(prompt)


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> dict | None:
    if not text:
        return None
    match = _JSON_RE.search(text)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        cleaned = match.group(0).replace("\n", " ")
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None


def _format_block(output_type: str) -> str:
    if output_type == "boolean":
        return '"verdict" — строка "да" или "нет"'
    if output_type == "score":
        return '"verdict" — число от 0 до 10'
    if output_type == "category":
        return '"verdict" — одно слово-категория'
    return '"verdict" — короткая строка-ответ'


def _build_dialog(turns: list[dict] | None, transcript: str, limit: int = 4000) -> str:
    if turns:
        lines = [f"[{t.get('speaker', '?')}]: {(t.get('text') or '').strip()}" for t in turns]
        text = "\n".join(lines)
    else:
        text = transcript or ""
    return text[:limit]


def _parse_verdict(value, output_type: str) -> dict:
    result = {
        "value_boolean": None,
        "value_score": None,
        "value_category": None,
    }
    if value is None:
        return result
    s = str(value).strip()
    if output_type == "boolean":
        result["value_boolean"] = s.lower().rstrip(".") in ("да", "yes", "true", "1")
    elif output_type == "score":
        numbers = re.findall(r"\d+(?:\.\d+)?", s)
        if numbers:
            result["value_score"] = min(max(float(numbers[0]), 0), 10)
    elif output_type == "category":
        result["value_category"] = s
    return result


async def run_llm_check(
        prompt_template: str,
        transcript: str,
        turns: list[dict] | None,
        output_type: str,
) -> dict:
    from services.sentiment import analyze_turns as sentiment_analyze, format_for_prompt as sentiment_format

    user_instruction = prompt_template
    dialog_block = _build_dialog(turns, transcript)
    user_instruction = user_instruction.replace("{{transcript}}", transcript[:4000])
    user_instruction = user_instruction.replace("{{turns}}", dialog_block)
    user_instruction = user_instruction.replace("{transcript}", transcript[:4000])
    user_instruction = user_instruction.replace("{turns}", dialog_block)

    fmt = _format_block(output_type)

    step1_prompt = (
        f"Задание: {user_instruction}\n\n"
        f"Диалог для анализа:\n{dialog_block}\n\n"
        f"Если для уверенного ответа нужен анализ тональности (sentiment) реплик — "
        f"верни JSON:\n"
        f'{{"need_sentiment": true, "reason": "<коротко зачем>"}}\n\n'
        f"Иначе верни JSON с финальным ответом:\n"
        f'{{"need_sentiment": false, {fmt}, "explanation": "<1-2 предложения>"}}\n\n'
        f"Никакого текста вне JSON. Только валидный JSON."
    )

    logger.info("LLM step1 prompt (%s): %d chars", output_type, len(step1_prompt))

    try:
        raw_step1 = await call_yandex_gpt(step1_prompt, temperature=0.1, max_tokens=600)
    except LLMFatalError:
        raise
    parsed = _extract_json(raw_step1)

    if parsed and not parsed.get("need_sentiment"):
        verdict_fields = _parse_verdict(parsed.get("verdict"), output_type)
        explanation = (parsed.get("explanation") or "").strip()
        raw_combined = f"{parsed.get('verdict', '')}\n{explanation}".strip()
        return {
            **verdict_fields,
            "raw_response": raw_combined or raw_step1.strip(),
        }

    if parsed and parsed.get("need_sentiment"):
        logger.info("LLM requested sentiment: %s", parsed.get("reason", ""))
        sent = sentiment_analyze(turns or [])
        sent_block = sentiment_format(sent)

        step2_prompt = (
            f"Задание: {user_instruction}\n\n"
            f"Диалог:\n{dialog_block}\n\n"
            f"Анализ тональности (от модели sentiment):\n{sent_block}\n\n"
            f"Учти sentiment и верни JSON с финальным ответом:\n"
            f'{{{fmt}, "explanation": "<1-2 предложения>"}}\n\n'
            f"Никакого текста вне JSON."
        )
        logger.info("LLM step2 prompt: %d chars", len(step2_prompt))
        try:
            raw_step2 = await call_yandex_gpt(step2_prompt, temperature=0.1, max_tokens=600)
        except LLMFatalError:
            raise
        parsed2 = _extract_json(raw_step2)
        if parsed2 is not None:
            verdict_fields = _parse_verdict(parsed2.get("verdict"), output_type)
            explanation = (parsed2.get("explanation") or "").strip()
            raw_combined = f"{parsed2.get('verdict', '')}\n{explanation}".strip()
            return {
                **verdict_fields,
                "raw_response": raw_combined or raw_step2.strip(),
            }
        return _legacy_parse(raw_step2, output_type)

    return _legacy_parse(raw_step1, output_type)


def _legacy_parse(raw_response: str, output_type: str) -> dict:
    result = {
        "value_boolean": None,
        "value_score": None,
        "value_category": None,
        "raw_response": (raw_response or "").strip(),
    }
    lines = [l.strip() for l in (raw_response or "").strip().split("\n") if l.strip()]
    verdict = lines[0].lower().rstrip(".") if lines else ""

    if output_type == "boolean":
        result["value_boolean"] = verdict in ("да", "yes", "true", "1")
    elif output_type == "score":
        numbers = re.findall(r"\d+(?:\.\d+)?", verdict)
        if numbers:
            result["value_score"] = min(max(float(numbers[0]), 0), 10)
    elif output_type == "category":
        result["value_category"] = lines[0].strip() if lines else (raw_response or "").strip()
    return result
