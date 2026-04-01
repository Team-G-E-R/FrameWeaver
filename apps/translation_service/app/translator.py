from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import torch
from transformers import MarianMTModel, MarianTokenizer

from app.language import detect_language
from app.settings import settings


@dataclass
class TranslationResult:
    original_text: str
    translated_text: str
    detected_source_lang: str
    target_lang: str
    was_translated: bool
    provider: str
    model: str


class Translator:
    def __init__(self) -> None:
        self.model_name = settings.translation_model_name
        self.target_lang = settings.translation_target_lang
        self.provider = settings.provider_name

        self.tokenizer: Optional[MarianTokenizer] = None
        self.model: Optional[MarianMTModel] = None
        self.device = torch.device("cpu")

    def load(self) -> None:
        self.tokenizer = MarianTokenizer.from_pretrained(self.model_name)
        self.model = MarianMTModel.from_pretrained(self.model_name)
        self.model.to(self.device)
        self.model.eval()

    @property
    def is_loaded(self) -> bool:
        return self.tokenizer is not None and self.model is not None

    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "en") -> TranslationResult:
        if not self.is_loaded:
            raise RuntimeError("Translator is not loaded")

        text = text.strip()
        if not text:
            raise ValueError("Text is empty")

        detected_source_lang = detect_language(text) if source_lang == "auto" else source_lang

        if detected_source_lang == target_lang:
            return TranslationResult(
                original_text=text,
                translated_text=text,
                detected_source_lang=detected_source_lang,
                target_lang=target_lang,
                was_translated=False,
                provider=self.provider,
                model=self.model_name,
            )

        if detected_source_lang != "ru" or target_lang != "en":
            raise ValueError(
                f"Unsupported translation direction: {detected_source_lang}->{target_lang}"
            )

        assert self.tokenizer is not None
        assert self.model is not None

        batch = self.tokenizer(
            [text],
            return_tensors="pt",
            truncation=True,
            max_length=256,
            padding=True,
        )

        batch = {k: v.to(self.device) for k, v in batch.items()}

        with torch.inference_mode():
            generated = self.model.generate(
                **batch,
                max_new_tokens=256,
                num_beams=4,
            )

        translated = self.tokenizer.batch_decode(generated, skip_special_tokens=True)[0]
        translated = self._postprocess_prompt(translated)

        return TranslationResult(
            original_text=text,
            translated_text=translated,
            detected_source_lang=detected_source_lang,
            target_lang=target_lang,
            was_translated=True,
            provider=self.provider,
            model=self.model_name,
        )

    @staticmethod
    def _postprocess_prompt(text: str) -> str:
        return " ".join(text.replace(" ,", ",").split())