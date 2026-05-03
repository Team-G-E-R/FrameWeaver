from copy import deepcopy
from typing import Any


TRANSLATABLE_PROMPT_JOB_TYPES   = {"sprites", "icon", "sound"}


async def prepare_job_params(job_type: str, params: dict[str, Any]) -> dict[str, Any]:
    prepared = deepcopy(params if isinstance(params, dict) else {})

    prompt = prepared.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return prepared

    prompt = prompt.strip()
    prepared["prompt_original"] = prompt

    if job_type not in TRANSLATABLE_PROMPT_JOB_TYPES :
        prepared["prompt"] = prompt
        return prepared

    try:
        translated = await translate_prompt_to_english(prompt)
    except Exception:
        translated = prompt

    prepared["prompt_en"] = translated
    prepared["prompt"] = translated

    return prepared