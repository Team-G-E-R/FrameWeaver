import os
import time
from dataclasses import dataclass

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from app.schemas import GenerateTextRequest, GenerateTextResponse


@dataclass(frozen=True)
class TextGenerationConfig:
    model_name: str
    device: str
    max_new_tokens: int
    temperature: float
    top_p: float


class TextGenerator:
    def _cleanup_generated_text(self, text: str, word_count: int) -> str:
        cleaned = text.strip()

        cleaned = self._extract_between_separators(cleaned)
        cleaned = self._remove_markdown_noise(cleaned)
        cleaned = self._remove_service_phrases(cleaned)
        cleaned = self._trim_to_word_limit(cleaned, word_count)

        return cleaned.strip()

    def _extract_between_separators(self, text: str) -> str:
        parts = text.split("---")

        if len(parts) >= 3:
            middle = parts[1].strip()
            if middle:
                return middle

        if len(parts) == 2:
            right = parts[1].strip()
            if right:
                return right

        return text

    def _remove_markdown_noise(self, text: str) -> str:
        lines = []

        for line in text.splitlines():
            line = line.strip()

            if not line:
                lines.append("")
                continue

            line = line.replace("**", "")
            line = line.replace("__", "")
            line = line.lstrip("#").strip()

            if line in {"-", "—", "---"}:
                continue

            lines.append(line)

        return "\n".join(lines).strip()

    def _remove_service_phrases(self, text: str) -> str:
        banned_fragments = (
            "желаемый объем",
            "желаемый объём",
            "вот как",
            "этот текст будет",
            "будет легко вставить",
            "давайте",
            "с удовольствием",
        )

        result_lines = []

        for line in text.splitlines():
            low = line.lower().strip()

            if any(fragment in low for fragment in banned_fragments):
                continue

            result_lines.append(line)

        return "\n".join(result_lines).strip()

    def _trim_to_word_limit(self, text: str, word_count: int) -> str:
        max_words = max(10, int(word_count * 1.15))

        words = text.split()
        if len(words) <= max_words:
            return text

        trimmed = " ".join(words[:max_words]).strip()

        last_sentence_end = max(
            trimmed.rfind("."),
            trimmed.rfind("!"),
            trimmed.rfind("?"),
            trimmed.rfind("…"),
        )

        if last_sentence_end > len(trimmed) * 0.6:
            return trimmed[:last_sentence_end + 1].strip()

        return trimmed.rstrip(" ,;:") + "."
    
    def _estimate_max_new_tokens(self, word_count: int) -> int:
        return max(64, min(512, int(word_count * 2.2)))

    def __init__(self) -> None:
        self.config = TextGenerationConfig(
            model_name=os.getenv("TEXT_GENERATION_MODEL_NAME", "Qwen/Qwen2.5-0.5B-Instruct"),
            device=os.getenv("TEXT_GENERATION_DEVICE", "cpu"),
            max_new_tokens=int(os.getenv("TEXT_GENERATION_MAX_NEW_TOKENS", "256")),
            temperature=float(os.getenv("TEXT_GENERATION_TEMPERATURE", "0.6")),
            top_p=float(os.getenv("TEXT_GENERATION_TOP_P", "0.9")),
        )

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_name,
            trust_remote_code=True,
        )

        self.model = AutoModelForCausalLM.from_pretrained(
            self.config.model_name,
            torch_dtype=torch.float32,
            device_map=None,
            trust_remote_code=True,
        )

        self.model.to(self.config.device)
        self.model.eval()

    def generate(self, request: GenerateTextRequest) -> GenerateTextResponse:
        started_at = time.perf_counter()

        max_new_tokens = request.max_new_tokens or self._estimate_max_new_tokens(request.word_count)
        temperature = request.temperature or self.config.temperature
        top_p = request.top_p or self.config.top_p

        system_prompt = self._build_system_prompt(request)
        user_prompt = request.prompt.strip()

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ]

        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        inputs = self.tokenizer([text], return_tensors="pt").to(self.config.device)

        with torch.inference_mode():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=temperature,
                top_p=top_p,
                repetition_penalty=1.08,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        generated_ids = output_ids[0][inputs.input_ids.shape[-1]:]
        generated_text = self.tokenizer.decode(
            generated_ids,
            skip_special_tokens=True,
        ).strip()
        
        generated_text = self._cleanup_generated_text(
            generated_text,
            request.word_count,
        )

        duration_ms = int((time.perf_counter() - started_at) * 1000)

        return GenerateTextResponse(
            text=generated_text,
            model=self.config.model_name,
            text_kind=request.text_kind,
            language=request.language,
            word_count=request.word_count,
            prompt_tokens=int(inputs.input_ids.shape[-1]),
            completion_tokens=int(generated_ids.shape[-1]),
            duration_ms=duration_ms,
        )

    def _build_system_prompt(self, request: GenerateTextRequest) -> str:
        kind_description = {
            "character": "описание персонажа",
            "item": "описание предмета",
            "quest": "описание квеста",
            "dialogue": "короткий игровой диалог",
            "lore": "лоровый текст для игрового мира",
            "other": "короткий игровой текст",
        }.get(request.text_kind, "короткий игровой текст")

        min_words = max(10, int(request.word_count * 0.8))
        max_words = request.word_count

        if request.text_kind == "dialogue":
            return (
                "Ты генератор текстовых ассетов для видеоигр. "
                f"Сгенерируй {kind_description}. "
                f"Язык ответа: {request.language}. "
                f"Объем: от {min_words} до {max_words} слов. "
                "Верни только готовый диалог. "
                "Формат каждой строки: Имя персонажа: реплика. "
                "Не добавляй вступление. "
                "Не пиши фразы вроде 'вот вариант', 'конечно', 'давайте', 'с удовольствием'. "
                "Не упоминай желаемый объем. "
                "Не используй markdown. "
                "Не используй заголовки, списки, разделители или символы ---. "
                "Не добавляй пояснения после диалога."
            )

        return (
            "Ты генератор текстовых ассетов для видеоигр. "
            f"Сгенерируй {kind_description}. "
            f"Язык ответа: {request.language}. "
            f"Объем: от {min_words} до {max_words} слов. "
            "Верни только финальный игровой текст. "
            "Не добавляй вступление. "
            "Не пиши фразы вроде 'вот вариант', 'конечно', 'давайте', 'с удовольствием'. "
            "Не упоминай желаемый объем. "
            "Не используй markdown. "
            "Не используй заголовки, списки, разделители или символы ---. "
            "Не добавляй пояснения после текста. "
            "Текст должен быть готов к вставке в игру."
        )
