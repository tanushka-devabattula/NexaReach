from pydantic import BaseModel, Field


class LanguageInfo(BaseModel):
    name: str
    code: str
    native_name: str
    script: str
    direction: str = "ltr"
    is_rtl: bool = False


class TranslationRequest(BaseModel):
    text: str = Field(min_length=1, description="Source message to translate")
    target_language: str = Field(description="Target language name (e.g., Hindi, Telugu, Urdu)")
    source_language: str = Field(default="English", description="Source language name")
    preserve_placeholders: bool = Field(default=True, description="Whether to protect tokens like {{name}}")


class TranslationResult(BaseModel):
    language: str
    language_code: str
    native_name: str
    translated_text: str
    is_rtl: bool = False
    direction: str = "ltr"
    provider: str = "offline-fallback"
    is_fallback: bool = True
    bidi_safe_text: str
    placeholders_preserved: list[str] = []


class BatchTranslationRequest(BaseModel):
    text: str = Field(min_length=1, description="Source message to translate")
    target_languages: list[str] = Field(
        default_factory=list,
        description="List of target languages. If empty, all 10 supported Indian languages will be translated."
    )
    source_language: str = Field(default="English")


class BatchTranslationResponse(BaseModel):
    source_text: str
    source_language: str
    results: list[TranslationResult]

