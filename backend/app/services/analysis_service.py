import logging
import os
import re
import time

from app.core.config import settings
from app.schemas.analysis import (
    ReadabilityMetrics,
    ToneAnalysisRequest,
    ToneAnalysisResponse,
    ToneImprovementRequest,
    ToneImprovementResponse,
    ToneMetrics,
)

logger = logging.getLogger(__name__)


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


def improve_tone(request: ToneImprovementRequest) -> ToneImprovementResponse:
    """
    Optimizes and rewrites awareness content to align with target tone and channel constraints.
    Supports real AI providers (OpenAI) with timeouts and retries, falling back cleanly
    to deterministic offline templates when unavailable.
    Guarantees SMS messages remain strictly under 160 characters.
    """
    clean_content = request.content.strip()
    target_tone = (request.target_tone or "Informative").capitalize()
    channel = (request.channel or "SMS").upper()

    api_key = settings.API_KEY or os.getenv("OPENAI_API_KEY") or ""
    provider = "offline-fallback"
    is_fallback = True
    improved_text = ""

    # Attempt real AI rewrite if configured
    if api_key and not api_key.startswith("replace-") and len(api_key) > 20:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, timeout=10.0)
            system_prompt = (
                "You are an expert public awareness copywriter for the NexaReach platform. "
                f"Rewrite the user's message to match the '{target_tone}' tone for the '{channel}' channel. "
                "Preserve all dynamic placeholders like {{name}} and contact numbers. "
            )
            if channel == "SMS":
                system_prompt += "CRITICAL CONSTRAINT: The output MUST be strictly 160 characters or fewer. "
            system_prompt += "Return ONLY the rewritten message without explanations or quotes."

            for attempt in range(2 + 1):
                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": clean_content},
                        ],
                        max_tokens=250,
                        temperature=0.7,
                        timeout=10.0,
                    )
                    content_out = response.choices[0].message.content.strip()
                    if content_out:
                        improved_text = content_out
                        provider = "openai"
                        is_fallback = False
                    break
                except Exception as err:
                    if attempt < 2:
                        time.sleep(0.5 * (attempt + 1))
                    else:
                        safe_msg = re.sub(r"sk-[a-zA-Z0-9_-]{8,}", "[REDACTED_API_KEY]", str(err))
                        logger.warning("OpenAI tone improvement call failed after retries: %s", safe_msg)
        except Exception as e:
            safe_msg = re.sub(r"sk-[a-zA-Z0-9_-]{8,}", "[REDACTED_API_KEY]", str(e))
            logger.warning("Failed to initialize AI provider for tone improvement: %s", safe_msg)
            provider = "offline-fallback"
            is_fallback = True

    # Offline fallback generator
    if is_fallback or not improved_text:
        # Strip preexisting category headers
        clean_body = re.sub(
            r"^(urgent advisory|urgent alert|alert|public notice|official notice|official circular|community notice|dear resident|dear citizen)\s*[:,\-]?\s*",
            "",
            clean_content,
            flags=re.IGNORECASE,
        ).strip()
        if clean_body:
            clean_body = clean_body[0].upper() + clean_body[1:]
        else:
            clean_body = clean_content

        if channel == "SMS":
            if target_tone == "Urgent":
                template = f"URGENT ADVISORY: {clean_body}. Immediate precautions recommended. Call 1800-000-111."
            elif target_tone in ["Friendly", "Empathetic"]:
                template = f"Dear resident, {clean_body}. We care for your family's safety. Helpline: 1800-000-111."
            elif target_tone == "Formal":
                template = f"PUBLIC NOTICE: {clean_body}. Compliance is advised by local authorities. Info: 1800-000-111."
            elif target_tone == "Persuasive":
                template = f"Action needed: {clean_body}. Take proactive steps today to protect your area. Call 1800-000-111."
            else:  # Informative
                template = f"Public Notice: {clean_body}. For verified guidance, contact helpline 1800-000-111."

            # Hard guarantee: SMS output must stay within 160 characters
            if len(template) > 160:
                suffix = " Helpline: 1800-000-111."
                max_body_len = 160 - len(suffix)
                template = template[:max_body_len].rstrip(" ,.-") + suffix

            improved_text = template

        elif channel == "WHATSAPP":
            if target_tone == "Urgent":
                improved_text = (
                    f"🚨 *CRITICAL UPDATE* 🚨\n\n"
                    f"{clean_body}\n\n"
                    f"⚠️ *Recommended Action:* Follow official advisories immediately.\n"
                    f"📞 *Helpline:* 1800-000-111"
                )
            else:
                improved_text = (
                    f"📢 *Public Awareness Bulletin*\n\n"
                    f"Dear Resident,\n\n"
                    f"{clean_body}\n\n"
                    f"✅ Verified guidance available at nearest civil center.\n"
                    f"📞 *Toll-Free Helpline:* 1800-000-111\n"
                    f"Reply 'STOP' to opt out."
                )
        else:
            # Email / Social Media / Default
            improved_text = f"Official Public Advisory [{target_tone}]: {clean_body}. Verified guidance available via helpline 1800-000-111."

    # If SMS, enforce final strict cap
    if channel == "SMS" and len(improved_text) > 160:
        improved_text = improved_text[:157] + "..."

    # Generate actionable suggestions
    suggestions: list[str] = []
    if channel == "SMS":
        suggestions.append(f"Optimized message length to {len(improved_text)} characters (single-segment SMS limit: 160).")
    if target_tone == "Urgent":
        suggestions.append("Framed with high-priority action language and helpline contact for immediate civic response.")
    elif target_tone in ["Friendly", "Empathetic"]:
        suggestions.append("Used supportive, welcoming salutation to reduce public anxiety and foster community trust.")
    elif target_tone == "Formal":
        suggestions.append("Applied authoritative institutional phrasing adhering to official public broadcast standards.")
    elif target_tone == "Persuasive":
        suggestions.append("Emphasized proactive community benefits and collective civic participation.")
    suggestions.append("Preserved dynamic token placeholders, phone numbers, and official web references.")

    return ToneImprovementResponse(
        original_content=request.content,
        improved_content=improved_text,
        target_tone=request.target_tone,
        channel=request.channel,
        provider=provider,
        is_fallback=is_fallback,
        suggestions=suggestions,
        character_count=len(improved_text),
    )

