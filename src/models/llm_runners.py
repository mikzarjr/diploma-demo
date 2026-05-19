from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Callable, Optional

import requests
from dotenv import load_dotenv

load_dotenv()


@dataclass
class LLMResponse:
    text: str
    latency_sec: float
    error: Optional[str] = None
    input_tokens_est: int = 0
    output_tokens_est: int = 0


def _est_tokens(text: str) -> int:
    return max(1, len(text) // 4)


YA_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"


def _yandex_completion(model_uri: str, prompt: str, system: Optional[str]) -> LLMResponse:
    api_key = os.getenv("YANDEX_API_KEY")
    folder_id = os.getenv("YANDEX_FOLDER_ID")
    if not api_key or not folder_id:
        return LLMResponse(
            text="",
            latency_sec=0.0,
            error="YANDEX_API_KEY or YANDEX_FOLDER_ID is not set in .env",
        )

    full_model_uri = model_uri.replace("{folder}", folder_id)
    messages = []
    if system:
        messages.append({"role": "system", "text": system})
    messages.append({"role": "user", "text": prompt})

    headers = {
        "Authorization": f"Api-Key {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "modelUri": full_model_uri,
        "completionOptions": {
            "stream": False,
            "temperature": 0.1,
            "maxTokens": 800,
        },
        "messages": messages,
    }
    t0 = time.perf_counter()
    try:
        r = requests.post(YA_URL, headers=headers, json=body, timeout=60)
        latency = time.perf_counter() - t0
        if r.status_code != 200:
            return LLMResponse(
                text="",
                latency_sec=latency,
                error=f"HTTP {r.status_code}: {r.text[:300]}",
            )
        data = r.json()
        alt = data.get("result", {}).get("alternatives", [{}])[0]
        text = alt.get("message", {}).get("text", "")
        usage = data.get("result", {}).get("usage", {})
        return LLMResponse(
            text=text,
            latency_sec=latency,
            input_tokens_est=int(usage.get("inputTextTokens", _est_tokens(prompt + (system or "")))),
            output_tokens_est=int(usage.get("completionTokens", _est_tokens(text))),
        )
    except Exception as exc:
        return LLMResponse(text="", latency_sec=time.perf_counter() - t0, error=str(exc))


def yandex_lite(prompt: str, system: Optional[str] = None) -> LLMResponse:
    return _yandex_completion("gpt://{folder}/yandexgpt-lite/latest", prompt, system)


def yandex_pro(prompt: str, system: Optional[str] = None) -> LLMResponse:
    return _yandex_completion("gpt://{folder}/yandexgpt/latest", prompt, system)


_LOCAL_MODEL_CACHE: dict[str, object] = {}


def _load_local(model_id: str):
    if model_id in _LOCAL_MODEL_CACHE:
        return _LOCAL_MODEL_CACHE[model_id]
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch

    tok = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.float16 if torch.backends.mps.is_available() else torch.float32,
        device_map="mps" if torch.backends.mps.is_available() else "cpu",
    )
    _LOCAL_MODEL_CACHE[model_id] = (tok, model)
    return tok, model


def local_qwen_1_5b(prompt: str, system: Optional[str] = None) -> LLMResponse:
    model_id = "Qwen/Qwen2.5-1.5B-Instruct"
    try:
        tok, model = _load_local(model_id)
        import torch

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tok([text], return_tensors="pt").to(model.device)
        t0 = time.perf_counter()
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=800,
                do_sample=False,
                temperature=0.1,
                pad_token_id=tok.eos_token_id,
            )
        latency = time.perf_counter() - t0
        gen = out[0, inputs["input_ids"].shape[1]:]
        completion = tok.decode(gen, skip_special_tokens=True)
        return LLMResponse(
            text=completion,
            latency_sec=latency,
            input_tokens_est=int(inputs["input_ids"].shape[1]),
            output_tokens_est=int(gen.shape[0]),
        )
    except Exception as exc:
        return LLMResponse(text="", latency_sec=0.0, error=str(exc))


def mock_runner(prompt: str, system: Optional[str] = None) -> LLMResponse:
    return LLMResponse(
        text='{"checklist": {}, "summary": "", "sentiment_overall": "neutral", "key_facts": []}',
        latency_sec=0.001,
    )


RUNNERS: dict[str, Callable[[str, Optional[str]], LLMResponse]] = {
    "yandex_lite": yandex_lite,
    "yandex_pro": yandex_pro,
    "local_qwen_1_5b": local_qwen_1_5b,
    "mock": mock_runner,
}
