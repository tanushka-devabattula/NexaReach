from pydantic import BaseModel, Field


class ToneAnalysisRequest(BaseModel):
    content: str = Field(min_length=1, description="Message content to evaluate")
    channel: str = Field(default="SMS", description="Intended delivery channel")
    target_tone: str | None = Field(default=None, description="Optional expected tone to benchmark against")


class ReadabilityMetrics(BaseModel):
    flesch_reading_ease: float
    flesch_kincaid_grade: float
    reading_ease_level: str
    word_count: int
    sentence_count: int
    character_count: int
    avg_words_per_sentence: float
    avg_syllables_per_word: float
    public_clarity_score: int = Field(ge=0, le=100)


class ToneMetrics(BaseModel):
    primary_tone: str
    secondary_tone: str | None = None
    sentiment: str
    confidence: float
    tone_distribution: dict[str, float]


class ToneAnalysisResponse(BaseModel):
    content: str
    channel: str
    readability: ReadabilityMetrics
    tone: ToneMetrics
    recommendations: list[str]


class ToneImprovementRequest(BaseModel):
    content: str = Field(min_length=1, description="Message text to optimize and rewrite")
    target_tone: str = Field(default="Informative", description="Target tone: Formal, Friendly, Urgent, Empathetic, Persuasive, Informative")
    channel: str = Field(default="SMS", description="Delivery channel (SMS, WhatsApp, Email, Social Media)")


class ToneImprovementResponse(BaseModel):
    original_content: str
    improved_content: str
    target_tone: str
    channel: str
    provider: str
    is_fallback: bool
    suggestions: list[str] = []
    character_count: int

