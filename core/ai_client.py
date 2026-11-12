"""
core/ai_client.py — High-Availability AI Generation Client for JARVIS Mark 78
Provides automatic multi-model fallback and exponential backoff retry across:
1. gemini-2.5-flash (Primary fast reasoning & structured JSON/Markdown)
2. gemini-2.5-flash-lite (Ultra-low-latency fallback)
3. gemini-flash-latest / gemini-flash-lite-latest
4. OpenRouter multi-provider fallback (if configured in config/api_keys.json)
Prevents 503 high demand, 404 model aliases, or 429 rate limit exceptions from interrupting
document authoring, presentation design, code generation, or skill creation.
"""

import time
import json
import urllib.request
from pathlib import Path
from typing import Optional, List, Union, Any
from google import genai

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_keys() -> dict:
    cfg = BASE_DIR / "config" / "api_keys.json"
    if cfg.exists():
        try:
            return json.loads(cfg.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def get_api_key() -> str:
    return _load_keys().get("gemini_api_key", "")


def get_openrouter_key() -> str:
    return _load_keys().get("openrouter_api_key", "")


def get_gemini_client() -> Optional[genai.Client]:
    k = get_api_key()
    if not k:
        return None
    return genai.Client(api_key=k)


DEFAULT_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
]


def _extract_plain_prompt(prompt_or_contents: Union[str, List[Any]]) -> str:
    if isinstance(prompt_or_contents, str):
        return prompt_or_contents
    parts_txt = []
    if isinstance(prompt_or_contents, list):
        for item in prompt_or_contents:
            if isinstance(item, str):
                parts_txt.append(item)
            elif isinstance(item, dict):
                for p in item.get("parts", []):
                    if isinstance(p, dict) and "text" in p:
                        parts_txt.append(p["text"])
                    elif isinstance(p, str):
                        parts_txt.append(p)
    return "\n".join(parts_txt)


def _openrouter_fallback(prompt_text: str) -> Optional[str]:
    or_key = get_openrouter_key()
    if not or_key or not prompt_text:
        return None
    try:
        payload = json.dumps({
            "model": "google/gemini-2.5-flash",
            "messages": [{"role": "user", "content": prompt_text}],
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {or_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            choices = data.get("choices") or []
            if choices:
                return (choices[0].get("message", {}).get("content") or "").strip()
    except Exception:
        pass
    return None


def generate_text_with_retry(
    prompt_or_contents: Union[str, List[Any]],
    client: Optional[genai.Client] = None,
    models: Optional[List[str]] = None,
    max_retries_per_model: int = 2
) -> str:
    """
    Executes generate_content with multi-model fallback and backoff.
    """
    if client is None:
        client = get_gemini_client()

    model_list = models or DEFAULT_MODELS
    last_err = ""

    if client is not None:
        for model_name in model_list:
            for attempt in range(max_retries_per_model):
                try:
                    res = client.models.generate_content(
                        model=model_name,
                        contents=prompt_or_contents
                    )
                    if res and res.text:
                        return res.text.strip()
                except Exception as e:
                    err_s = str(e)
                    last_err = err_s
                    if any(x in err_s for x in ["503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED"]):
                        time.sleep(0.8 * (attempt + 1))
                        continue
                    if "404" in err_s or "NOT_FOUND" in err_s:
                        break
                    break

    # Try OpenRouter fallback if configured
    plain_prompt = _extract_plain_prompt(prompt_or_contents)
    or_res = _openrouter_fallback(plain_prompt)
    if or_res:
        return or_res

    if client is None:
        return "Gemini API key is missing. Please add it to config/api_keys.json."

    return f"Service temporarily busy across AI endpoints ({last_err[:100]}). Please try again in a few moments."
