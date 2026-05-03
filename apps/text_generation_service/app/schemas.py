from typing import Literal

from pydantic import BaseModel, Field


TextKind = Literal["character", "item", "quest", "dialogue", "lore", "other"]


class GenerateTextRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    text_kind: TextKind = "other"
    language: str = Field(default="ru", min_length=2, max_length=16)
    word_count: int = Field(default=80, ge=10, le=300)
    max_new_tokens: int | None = Field(default=None, ge=16, le=512)
    temperature: float | None = Field(default=None, ge=0.1, le=2.0)
    top_p: float | None = Field(default=None, ge=0.1, le=1.0)


class GenerateTextResponse(BaseModel):
    text: str
    model: str
    text_kind: TextKind
    language: str
    word_count: int
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    duration_ms: int