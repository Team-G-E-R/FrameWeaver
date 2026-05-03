import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.generator import TextGenerator
from app.schemas import GenerateTextRequest, GenerateTextResponse


generator: TextGenerator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global generator
    generator = TextGenerator()
    yield
    generator = None


app = FastAPI(
    title="FrameWeaver Text Generation Service",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model": os.getenv("TEXT_GENERATION_MODEL_NAME", "Qwen/Qwen2.5-0.5B-Instruct"),
    }


@app.post("/generate", response_model=GenerateTextResponse)
def generate_text(request: GenerateTextRequest) -> GenerateTextResponse:
    if generator is None:
        raise RuntimeError("Text generator is not initialized")

    return generator.generate(request)