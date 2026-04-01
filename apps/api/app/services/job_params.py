from copy import deepcopy
from typing import Any

from app.services.prompt_translation import translate_prompt_to_english


async def prepare_job_params(job_type: str, params: dict[str, Any]) -> dict[str, Any]:
    prepared = deepcopy(params if isinstance(params, dict) else {})

    prompt = prepared.get("prompt")
    if isinstance(prompt, str) and prompt.strip():
        prepared["prompt_original"] = prompt

        try:
            translated = await translate_prompt_to_english(prompt)
        except Exception:
            translated = prompt

        prepared["prompt_en"] = translated
        prepared["prompt"] = translated

    return prepared