from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import router
from app.translator import Translator


@asynccontextmanager
async def lifespan(app: FastAPI):
    translator = Translator()
    translator.load()
    app.state.translator = translator
    yield


app = FastAPI(
    title="translation-service",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)