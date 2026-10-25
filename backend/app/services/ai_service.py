from datetime import datetime
import logging
import os
import re
import time
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import AIContentHistory
from app.schemas.ai import AIGenerateRequest, AIGenerateResponse

logger = logging.getLogger(__name__)


def _generate_offline_variations(prompt: str, channel: str, tone: str, count: int = 2) -> list[str]:
    """
    Intelligent offline generator for public awareness messages.
    Produces channel-tailored and tone-aligned content without external API dependencies.
    """
    clean_prompt = prompt.strip()
    topic = clean_prompt.capitalize()
    # Short subject for offline templates to avoid echoing full prompt.
    short_subject = topic
    
    # Sector awareness keywords
    is_health = bool(re.search(r"health|vaccin|disease|clinic|water|dengue|covid|pulse|polio|hospital|fever", clean_prompt, re.I))
    is_disaster = bool(re.search(r"flood|storm|rain|cyclone|quake|disaster|fire|emergency|weather", clean_prompt, re.I))
    is_civic = bool(re.search(r"vote|election|tax|pan|aadhaar|ration|sanitation|garbage|clean", clean_prompt, re.I))

    channel_normalized = (channel or "SMS").upper()
    tone_normalized = (tone or "Informative").capitalize()

    variations = []

    # Variation 1
    if channel_normalized == "SMS":
        if tone_normalized == "Urgent":
            v1 = f"URGENT ADVISORY: {short_subject}. Immediate precautions recommended. Call helpline 1800-000-111 for verified guidance."
            v2 = f"ALERT: Important update regarding {short_subject}. Visit official center or call 1800-000-111. Stay safe."
        elif tone_normalized == "Empathetic":
            v1 = f"Dear citizen, your community is here for you regarding {short_subject}. Free assistance available at your nearest center."
            v2 = f"We care for your family's safety: {short_subject}. Reach out to helpline 1800-000-111 anytime."
        elif tone_normalized == "Formal":
            v1 = f"PUBLIC NOTICE: General guidelines issued on {short_subject}. Compliance advised by local authorities. Info: 1800-000-111."
            v2 = f"OFFICIAL CIRCULAR: {clean_prompt}. Citizens requested to cooperate with public health teams. Helpline: 1800-000-111."
        else: # Informative / Persuasive
            v1 = f"Public Awareness: Protect your community on {clean_prompt}. Follow verified guidelines. Info: 1800-000-111."
            v2 = f"Community Notice: Take proactive steps on {clean_prompt}. Visit local center or call 1800-000-111 today."

    elif channel_normalized == "WHATSAPP":
        if tone_normalized == "Urgent":
            v1 = (
                f"🚨 *CRITICAL PUBLIC NOTICE: {topic}* 🚨\n\n"
                f"Immediate awareness update regarding: {clean_prompt}\n\n"
                f"📌 *Required Actions:*\n"
                f"1. Stay indoors and follow verified district advisories.\n"
                f"2. Keep emergency contacts and basic supplies accessible.\n"
                f"3. Do not forward unverified rumors.\n\n"
                f"📞 *Official Helpline:* 1800-000-111\n"
                f"🌐 Official Portal: https://nexareach.gov.in/advisory"
            )
            v2 = (
                f"⚠️ *URGENT SAFETY BULLETIN: {topic}*\n\n"
                f"Please note this priority alert on {clean_prompt}.\n\n"
                f"• Follow official instructions from authorized personnel.\n"
                f"• Share this advisory with neighbors and vulnerable family members.\n\n"
                f"📞 24x7 Help Desk: 1800-000-111"
            )
        else:
            v1 = (
                f"📢 *Public Awareness Advisory: {topic}*\n\n"
                f"Dear Community Member,\n\n"
                f"We are sharing vital information regarding {clean_prompt}.\n\n"
                f"✅ Key Steps to Follow:\n"
                f"• Maintain proper hygiene and preventive protocols.\n"
                f"• Access free public support at your nearest civil center.\n"
                f"• Reach out to district coordinators for any assistance.\n\n"
                f"📞 *Toll-Free Helpline:* 1800-000-111\n"
                f"Reply 'STOP' to unsubscribe from public broadcast alerts."
            )
            v2 = (
                f"🤝 *Community Health & Safety Bulletin*\n\n"
                f"Update on: {clean_prompt}\n\n"
                f"Together, we can ensure community well-being by following verified steps:\n"
                f"1. Check official guidelines before acting.\n"
                f"2. Assist senior citizens and children.\n"
                f"3. Report concerns to local field workers.\n\n"
                f"For details, visit: https://nexareach.gov.in"
            )

    elif channel_normalized == "EMAIL":
        v1 = (
            f"Subject: Official Public Awareness Advisory: {topic}\n\n"
            f"Dear Resident,\n\n"
            f"This is an official public awareness communication regarding {clean_prompt}.\n\n"
            f"Context & Guidance:\n"
            f"The district administration encourages all residents to take informed precautions. "
            f"Field officers and public centers are operational to support your neighborhood.\n\n"
            f"Action Points:\n"
            f"- Verify official announcements at https://nexareach.gov.in\n"
            f"- Reach emergency response coordinators at 1800-000-111\n\n"
            f"Sincerely,\n"
            f"Public Awareness & Citizen Services Division\n"
            f"NexaReach Platform"
        )
        v2 = (
            f"Subject: Important Community Update Regarding {topic}\n\n"
            f"Dear Citizen,\n\n"
            f"We are reaching out with verified recommendations concerning {clean_prompt}.\n\n"
            f"Please take a few moments to review preventive guidelines and share them with family members.\n"
            f"Helpline: 1800-000-111 | https://nexareach.gov.in\n\n"
            f"Regards,\nNexaReach Public Outreach Team"
        )

    else: # Social Media / Default
        v1 = f"📢 Public Advisory on {clean_prompt}. Stay informed, stay prepared, and rely on official district sources. Call 1800-000-111. #NexaReach #PublicAwareness #{re.sub(r'[^a-zA-Z0-9]', '', topic)[:15]}"
        v2 = f"💡 Awareness Alert: {clean_prompt}. Take preventive steps today to protect your family. Official helpline: 1800-000-111. #CommunityFirst #NexaReach"

    variations = [v1, v2]
    return variations[:count]


def generate_content(request: AIGenerateRequest, db: Session | None = None) -> AIGenerateResponse:
    """
    Generate public awareness content.
    Attempts OpenAI API when API_KEY is set; otherwise falls back to deterministic offline generator.
    Always marks provider and is_fallback transparently.
    """
    api_key = settings.API_KEY or os.getenv("OPENAI_API_KEY") or ""
    provider = "offline-fallback"
    is_fallback = True
    model_name = None
    primary_content = ""
    variations: list[str] = []

    if api_key and not api_key.startswith("replace-") and len(api_key) > 20:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, timeout=10.0)
            prompt_instruction = (
                f"You are a public awareness mass communication specialist for the NexaReach platform. "
                f"Generate a {request.tone} message for the channel '{request.channel}' regarding: '{request.prompt}'. "
                f"Target audience: {request.target_audience or 'General Public'}. "
                f"Keep length appropriate for the channel (SMS < 160 chars, WhatsApp formatted with emojis, Email with Subject). "
                f"Include emergency helpline placeholder '1800-000-111' where relevant."
            )
            for attempt in range(2 + 1):
                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You create impactful, verified public awareness messages."},
                            {"role": "user", "content": prompt_instruction}
                        ],
                        max_tokens=300,
                        temperature=0.7,
                        n=request.variations or 1,
                        timeout=10.0,
                    )
                    choices = [c.message.content.strip() for c in response.choices if c.message.content]
                    if choices:
                        primary_content = choices[0]
                        variations = choices
                        provider = "openai"
                        is_fallback = False
                        model_name = "gpt-3.5-turbo"
                    break
                except Exception as err:
                    if attempt < 2:
                        time.sleep(0.5 * (attempt + 1))
                    else:
                        safe_msg = re.sub(r"sk-[a-zA-Z0-9_-]{8,}", "[REDACTED_API_KEY]", str(err))
                        logger.warning("OpenAI content generation failed after retries: %s", safe_msg)
                        provider = "offline-fallback"
                        is_fallback = True
        except Exception as e:
            safe_msg = re.sub(r"sk-[a-zA-Z0-9_-]{8,}", "[REDACTED_API_KEY]", str(e))
            logger.warning("Failed to initialize OpenAI client for content generation: %s", safe_msg)
            # Fall back to offline generator on any error
            provider = "offline-fallback"
            is_fallback = True

    if is_fallback or not primary_content:
        variations = _generate_offline_variations(
            prompt=request.prompt,
            channel=request.channel,
            tone=request.tone,
            count=request.variations or 2,
        )
        primary_content = variations[0]

    history_record_id = None
    if db is not None:
        try:
            record = AIContentHistory(
                user_id=request.user_id,
                campaign_id=request.campaign_id,
                prompt=request.prompt,
                channel=request.channel,
                tone=request.tone,
                language="English",
                generated_content=primary_content,
                provider=provider,
                is_fallback=is_fallback,
                created_at=datetime.utcnow(),
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            history_record_id = record.id
        except Exception:
            db.rollback()

    return AIGenerateResponse(
        content=primary_content,
        variations=variations,
        channel=request.channel,
        tone=request.tone,
        provider=provider,
        is_fallback=is_fallback,
        model=model_name,
        history_id=history_record_id,
        created_at=datetime.utcnow(),
    )


def list_generation_history(db: Session, limit: int = 20) -> list[AIContentHistory]:
    """Retrieve recent AI content generation history from the database."""
    return (
        db.query(AIContentHistory)
        .order_by(AIContentHistory.id.desc())
        .limit(limit)
        .all()
    )

