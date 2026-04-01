from pydantic import BaseModel, Field


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    source_lang: str = Field(default="auto")
    target_lang: str = Field(default="en")
    domain: str = Field(default="game_asset_prompt")


class TranslateResponse(BaseModel):
    original_text: str
    translated_text: str
    detected_source_lang: str
    target_lang: str
    was_translated: bool
    provider: str
    model: str


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    provider: str
    model: str