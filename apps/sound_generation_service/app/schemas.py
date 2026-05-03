from pydantic import BaseModel, Field


class GenerateSoundRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=1000)
    audio_kind: str = Field(default="music", max_length=32)
    duration_seconds: float = Field(default=5.0, ge=1.0, le=160.0)
    sample_rate: int = Field(default=44100, ge=8000, le=48000)


class GenerateSoundResponse(BaseModel):
    audio_base64: str
    model: str
    prompt: str
    duration_seconds: float
    sample_rate: int
    duration_ms: int