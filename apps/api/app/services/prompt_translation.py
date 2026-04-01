import os
from typing import Any

import httpx


TRANSLATION_SERVICE_URL = os.getenv("TRANSLATION_SERVICE_URL", "http://translation_service:8000")
TRANSLATION_TIMEOUT_SECONDS = float(os.getenv("TRANSLATION_TIMEOUT_SECONDS", "5"))


def _has_cyrillic(text: str) -> bool:
    for ch in text.lower():
        if "а" <= ch <= "я" or ch == "ё":
            return True
    return False


async def translate_prompt_to_english(text: str) -> str:
    text = text.strip()
    if not text:
        return text

    if not _has_cyrillic(text):
        return text

    url = f"{TRANSLATION_SERVICE_URL}/translate"

    payload: dict[str, Any] = {
        "text": text,
        "source_lang": "auto",
        "target_lang": "en",
    }

    async with httpx.AsyncClient(timeout=TRANSLATION_TIMEOUT_SECONDS) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    translated = data.get("translated_text")
    if not isinstance(translated, str) or not translated.strip():
        raise RuntimeError("Translation service returned empty translated_text")

    return translated.strip()