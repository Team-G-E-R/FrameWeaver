from fastapi import APIRouter, HTTPException, Request

from app.schemas import HealthResponse, TranslateRequest, TranslateResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    translator = request.app.state.translator
    return HealthResponse(
        status="ok" if translator.is_loaded else "loading",
        model_loaded=translator.is_loaded,
        provider=translator.provider,
        model=translator.model_name,
    )


@router.post("/translate", response_model=TranslateResponse)
def translate(request: Request, payload: TranslateRequest) -> TranslateResponse:
    translator = request.app.state.translator

    try:
        result = translator.translate(
            text=payload.text,
            source_lang=payload.source_lang,
            target_lang=payload.target_lang,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="translation_failed") from exc

    return TranslateResponse(
        original_text=result.original_text,
        translated_text=result.translated_text,
        detected_source_lang=result.detected_source_lang,
        target_lang=result.target_lang,
        was_translated=result.was_translated,
        provider=result.provider,
        model=result.model,
    )