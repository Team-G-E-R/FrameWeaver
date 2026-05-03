import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.generator import SoundGenerator
from app.schemas import GenerateSoundRequest, GenerateSoundResponse


generator: SoundGenerator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global generator
    generator = SoundGenerator()
    yield
    generator = None


app = FastAPI(
    title="FrameWeaver Sound Generation Service",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model": os.getenv("SOUND_GENERATION_MODEL_NAME", "facebook/audiogen-small"),
    }


@app.post("/generate", response_model=GenerateSoundResponse)
def generate_sound(request: GenerateSoundRequest) -> GenerateSoundResponse:
    if generator is None:
        raise RuntimeError("Sound generator is not initialized")

    return generator.generate(request)