import base64
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional
import requests


@dataclass(frozen=True)
class WebuiResult:
    png_bytes: bytes
    info: Optional[Dict[str, Any]]


class SdWebuiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def txt2img(self, payload: Dict[str, Any], timeout_s: int = 600) -> WebuiResult:
        url = f"{self.base_url}/sdapi/v1/txt2img"
        r = requests.post(url, json=payload, timeout=timeout_s)
        r.raise_for_status()
        data = r.json()

        images = data.get("images") or []
        if not images:
            raise RuntimeError("SD WebUI returned no images")

        png_b64 = images[0]
        png_bytes = base64.b64decode(png_b64)

        info = None
        if "info" in data and isinstance(data["info"], str):
            # info часто строкой JSON
            try:
                import json
                info = json.loads(data["info"])
            except Exception:
                info = {"raw": data["info"]}

        return WebuiResult(png_bytes=png_bytes, info=info)


def get_sd_webui_url() -> str:
    url = os.getenv("SD_WEBUI_URL")
    if not url:
        raise RuntimeError("SD_WEBUI_URL is not set (expected like http://sd_webui:7860)")
    return url