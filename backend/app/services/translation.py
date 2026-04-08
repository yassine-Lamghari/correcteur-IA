from app.models.schemas import TranslateRequest, TranslateResponse


class TranslationService:
    """Simple placeholder translation service.

    Replace this with a real provider integration (Azure, DeepL, etc.).
    """

    def translate(self, request: TranslateRequest) -> TranslateResponse:
        if request.source_lang == request.target_lang:
            return TranslateResponse(translated_text=request.text, provider="identity")

        translated = f"[{request.target_lang}] {request.text}"
        return TranslateResponse(translated_text=translated, provider="mock")
