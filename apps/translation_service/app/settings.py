import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))

    translation_model_name: str = os.getenv(
        "TRANSLATION_MODEL_NAME",
        "Helsinki-NLP/opus-mt-ru-en",
    )
    translation_target_lang: str = os.getenv("TRANSLATION_TARGET_LANG", "en")
    translation_max_text_length: int = int(
        os.getenv("TRANSLATION_MAX_TEXT_LENGTH", "1000")
    )
    translation_device: str = os.getenv("TRANSLATION_DEVICE", "cpu")

    provider_name: str = "local_translation_service"


settings = Settings()