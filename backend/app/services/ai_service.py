"""AI content generation for NexaReach.

Simple version of what happens:
  1. Check the user's prompt is not empty.
  2. Ask OpenAI to write the message (for the chosen channel / tone / language).
  3. Save it in the AI history table and return it.

If the API key is missing or OpenAI fails, we raise AIProviderError with the real
reason. We NEVER return made-up text pretending to be AI output.
"""
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import AIContentHistory

logger = logging.getLogger(__name__)

# Maximum characters a channel should have (None = no strict limit).
CHANNEL_LIMITS = {"SMS": 160, "WHATSAPP": 1000, "PUSH": 120}


class AIProviderError(Exception):
    """The AI provider is missing, rejected us, or failed."""


def _api_key() -> str:
    # settings reads backend/.env (os.getenv does NOT), so use settings first.
    import os

    return (settings.API_KEY or os.getenv("OPENAI_API_KEY") or "").strip()


def _system_prompt(category: str, tone: str, channel: str, language: str, audience: str) -> str:
    limit = CHANNEL_LIMITS.get(channel.upper())
    limit_rule = (
        f"- The message MUST be at most {limit} characters including spaces.\n" if limit else ""
    )
    return (
        "You write public-awareness messages for Indian government, health and NGO campaigns.\n"
        f"Category: {category}. Tone: {tone}. Channel: {channel}. Audience: {audience}.\n"
        f"Write the message in {language}.\n"
        "Rules:\n"
        f"{limit_rule}"
        "- Use simple everyday words that ordinary citizens understand.\n"
        "- Include one clear action the reader should take.\n"
        "- Do not invent phone numbers, links, dates or statistics. If a detail is needed, "
        "use a placeholder such as {phone}, {url} or {date}.\n"
        "- Reply with ONLY the message text. No quotes, titles or explanations."
    )


def _call_openai(system_prompt: str, user_prompt: str, n: int) -> List[str]:
    api_key = _api_key()
    if not api_key:
        raise AIProviderError(
            "AI provider is not configured. Add API_KEY=<your OpenAI key> to backend/.env "
            "and restart the backend."
        )
    try:
        import openai
        from openai import OpenAI
    except ImportError as err:
        raise AIProviderError("The 'openai' package is not installed. Run: pip install openai") from err

    client = OpenAI(api_key=api_key, timeout=settings.TRANSLATION_TIMEOUT, max_retries=1)
    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            temperature=0.7,
            max_tokens=400,
            n=n,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except openai.AuthenticationError as err:
        raise AIProviderError("The AI provider rejected the API key (invalid or revoked).") from err
    except openai.RateLimitError as err:
        raise AIProviderError("AI provider rate limit or quota exceeded. Check the key's credit.") from err
    except (openai.APITimeoutError, openai.APIConnectionError) as err:
        raise AIProviderError("Could not reach the AI provider (timeout or network problem).") from err
    except openai.OpenAIError as err:
        raise AIProviderError(f"AI provider error: {type(err).__name__}.") from err

    texts = [(c.message.content or "").strip() for c in response.choices]
    texts = [t for t in texts if t]
    if not texts:
        raise AIProviderError("The AI provider returned an empty message.")
    return texts


def generate_content(
    prompt: str,
    category: str = "Public Health",
    target_language: str = "English",
    tone: Optional[str] = "Informative",
    channel: Optional[str] = "SMS",
    audience: str = "General Public",
    variations: int = 1,
    db: Optional[Session] = None,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    topic = (prompt or "").strip()
    if not topic:
        raise ValueError("Please enter a topic or prompt.")

    tone = (tone or "Informative").strip()
    channel = (channel or "SMS").strip()
    variations = max(1, min(int(variations or 1), 3))

    texts = _call_openai(
        _system_prompt(category, tone, channel, target_language, audience), topic, variations
    )
    main_text = texts[0]
    limit = CHANNEL_LIMITS.get(channel.upper())
    provider = f"openai:{settings.OPENAI_MODEL}"

    history_id = None
    if db is not None:
        try:
            record = AIContentHistory(
                user_id=user_id,
                prompt=topic,
                channel=channel,
                tone=tone,
                language=target_language,
                generated_content=main_text,
                provider=provider[:50],
                is_fallback=False,
            )
            db.add(record)
            db.commit()
            history_id = record.id
        except Exception:  # saving history must never break a good result
            logger.exception("Could not save AI history")
            db.rollback()

    return {
        "id": history_id,
        "content": main_text,
        "variations": texts,
        "channel": channel,
        "tone": tone,
        "language": target_language,
        "provider": provider,
        "model": settings.OPENAI_MODEL,
        "is_fallback": False,
        "character_count": len(main_text),
        "max_characters": limit,
        "within_limit": (len(main_text) <= limit) if limit else True,
        "status": "success",
    }


generate_ai_content = generate_content  # old name, kept so nothing else breaks


def list_generation_history(db: Optional[Session] = None, limit: int = 10, **_ignored) -> List[Dict[str, Any]]:
    if db is None:
        return []
    rows = (
        db.query(AIContentHistory)
        .order_by(AIContentHistory.id.desc())
        .limit(max(1, min(int(limit or 10), 100)))
        .all()
    )
    return [
        {
            "id": r.id,
            "prompt": r.prompt,
            "generated_content": r.generated_content,
            "channel": r.channel,
            "tone": r.tone,
            "language": r.language,
            "provider": r.provider,
            "is_fallback": bool(r.is_fallback),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]