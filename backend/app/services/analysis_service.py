import re
from app.schemas.analysis import (
    ReadabilityMetrics,
    ToneAnalysisRequest,
    ToneAnalysisResponse,
    ToneMetrics,
)


def _count_syllables_in_word(word: str) -> int:
    """Estimates the number of syllables in an English word."""
    clean = re.sub(r"[^a-zA-Z]", "", word.lower())
    if not clean:
        return 1
    if len(clean) <= 3:
        return 1

    # Simple vowel group heuristic
    clean = re.sub(r"(?:[^laeiouy]|ed|es|e)$", "", clean)
    clean = re.sub(r"^y", "", clean)
    syllables = len(re.findall(r"[aeiouy]{1,2}", clean))
    return max(1, syllables)


def calculate_readability(text: str) -> ReadabilityMetrics:
    """
    Computes standard Flesch Reading Ease and Flesch-Kincaid Grade Level metrics.
    """
    clean_text = text.strip()
    if not clean_text:
        return ReadabilityMetrics(
            flesch_reading_ease=100.0,
            flesch_kincaid_grade=1.0,
            reading_ease_level="Very Easy",
            word_count=0,
            sentence_count=1,
            character_count=0,
            avg_words_per_sentence=0.0,
            avg_syllables_per_word=1.0,
            public_clarity_score=100,
        )

    # Sentences split by [.!?\n]+
    sentences = [s.strip() for s in re.split(r"[.!?\n]+", clean_text) if s.strip()]
    sentence_count = max(1, len(sentences))

    # Words
    words = re.findall(r"\b[a-zA-Z0-9'-]+\b", clean_text)
    word_count = max(1, len(words))

    # Total syllables
    total_syllables = sum(_count_syllables_in_word(w) for w in words)

    avg_words_per_sentence = word_count / sentence_count
    avg_syllables_per_word = total_syllables / word_count

    # Flesch Reading Ease formula:
    # 206.835 - 1.015 * (words/sentences) - 84.6 * (syllables/words)
    fre = 206.835 - (1.015 * avg_words_per_sentence) - (84.6 * avg_syllables_per_word)
    fre = round(max(0.0, min(100.0, fre)), 1)

    # Flesch-Kincaid Grade Level formula:
    # 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59
    fkgl = (0.39 * avg_words_per_sentence) + (11.8 * avg_syllables_per_word) - 15.59
    fkgl = round(max(1.0, min(18.0, fkgl)), 1)

    if fre >= 80:
        level = "Very Easy (Ideal for mass public awareness)"
        clarity_score = 95
    elif fre >= 70:
        level = "Easy (Conversational & accessible)"
        clarity_score = 85
    elif fre >= 60:
        level = "Standard (Standard plain English)"
        clarity_score = 75
    elif fre >= 50:
        level = "Fairly Difficult (High-school reading level)"
        clarity_score = 60
    else:
        level = "Difficult (Consider simplifying sentences)"
        clarity_score = 45

    return ReadabilityMetrics(
        flesch_reading_ease=fre,
        flesch_kincaid_grade=fkgl,
        reading_ease_level=level,
        word_count=word_count,
        sentence_count=sentence_count,
        character_count=len(clean_text),
        avg_words_per_sentence=round(avg_words_per_sentence, 1),
        avg_syllables_per_word=round(avg_syllables_per_word, 2),
        public_clarity_score=clarity_score,
    )


def classify_tone_and_sentiment(text: str) -> ToneMetrics:
    """
    Analyzes lexical tone distribution and sentiment polarity for public communications.
    """
    clean = text.lower()

    urgent_words = [
        "urgent", "alert", "immediate", "emergency", "critical", "warning",
        "danger", "severe", "evacuate", "flood", "hazard", "threat", "storm"
    ]
    empathetic_words = [
        "care", "support", "together", "family", "health", "well-being",
        "help", "kindly", "protect", "community", "compassion", "dear", "safe"
    ]
    formal_words = [
        "hereby", "advisory", "official", "circular", "directive", "compliance",
        "authorized", "pursuant", "notification", "department", "regulations"
    ]
    informative_words = [
        "notice", "guidelines", "information", "update", "schedule", "details",
        "steps", "visit", "learn", "timing", "center", "clinic", "portal"
    ]
    persuasive_words = [
        "join", "participate", "action", "act", "ensure", "empower", "benefit",
        "together", "register", "stand", "future"
    ]

    scores = {
        "Urgent": sum(1 for w in urgent_words if w in clean),
        "Empathetic": sum(1 for w in empathetic_words if w in clean),
        "Formal": sum(1 for w in formal_words if w in clean),
        "Informative": sum(1 for w in informative_words if w in clean),
        "Persuasive": sum(1 for w in persuasive_words if w in clean),
    }

    total_hits = sum(scores.values()) or 1
    distribution = {k: round(v / total_hits, 2) for k, v in scores.items()}

    # Determine primary and secondary tone
    sorted_tones = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    primary_tone = sorted_tones[0][0] if sorted_tones[0][1] > 0 else "Informative"
    secondary_tone = sorted_tones[1][0] if len(sorted_tones) > 1 and sorted_tones[1][1] > 0 else None

    # Sentiment detection
    if scores["Urgent"] > 1:
        sentiment = "Urgent / Critical"
    elif scores["Empathetic"] > 0 or "thank" in clean or "well-being" in clean:
        sentiment = "Positive"
    else:
        sentiment = "Neutral / Informative"

    confidence = round(min(0.95, 0.60 + (sorted_tones[0][1] * 0.08)), 2)

    return ToneMetrics(
        primary_tone=primary_tone,
        secondary_tone=secondary_tone,
        sentiment=sentiment,
        confidence=confidence,
        tone_distribution=distribution,
    )


def analyze_tone_and_readability(request: ToneAnalysisRequest) -> ToneAnalysisResponse:
    """
    Main analysis orchestrator for Tone, Readability, and Channel-specific guidance.
    """
    readability = calculate_readability(request.content)
    tone = classify_tone_and_sentiment(request.content)

    recommendations: list[str] = []

    # Channel-specific length recommendations
    channel_norm = (request.channel or "SMS").upper()
    if channel_norm == "SMS":
        if readability.character_count > 160:
            recommendations.append(
                f"SMS length ({readability.character_count} chars) exceeds single SMS segment (160 chars). Consider shortening."
            )
        else:
            recommendations.append("Length is optimized for single-segment SMS delivery.")

    if readability.avg_words_per_sentence > 20:
        recommendations.append(
            f"Average sentence length is {readability.avg_words_per_sentence} words. Shorter sentences (< 18 words) improve citizen retention."
        )

    if readability.flesch_reading_ease < 60:
        recommendations.append(
            "Readability score is below recommended threshold for mass public broadcasts. Replace complex terms with simpler synonyms."
        )

    if request.target_tone and tone.primary_tone.lower() != request.target_tone.lower():
        recommendations.append(
            f"Detected tone is '{tone.primary_tone}', but target tone is '{request.target_tone}'. Adjust vocabulary to align tone."
        )

    if not recommendations:
        recommendations.append("Content is well-structured, clear, and ready for public dissemination.")

    return ToneAnalysisResponse(
        content=request.content,
        channel=request.channel,
        readability=readability,
        tone=tone,
        recommendations=recommendations,
    )

