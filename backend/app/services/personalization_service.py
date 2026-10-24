import re
from sqlalchemy.orm import Session

from app.models.models import AudienceMember, Segment
from app.schemas.personalization import (
    PersonalizePreviewRequest,
    PersonalizePreviewResponse,
    SegmentVariantItem,
    SegmentVariantRequest,
    SegmentVariantResponse,
)


def extract_tokens(text: str) -> list[str]:
    """Finds all unique token names enclosed in {{token_name}} in text."""
    matches = re.findall(r"\{\{([^}]+)\}\}", text)
    cleaned = [m.strip() for m in matches]
    return list(dict.fromkeys(cleaned))


def render_personalization(text: str, context: dict[str, str | None]) -> tuple[str, dict[str, str], list[str]]:
    """
    Substitutes placeholder tokens with values from context dict.
    Supports default fallback syntax like {{name|Citizen}}.
    Returns (rendered_text, tokens_replaced_map, missing_tokens_list).
    """
    tokens = extract_tokens(text)
    replaced_map: dict[str, str] = {}
    missing_tokens: list[str] = []
    result = text

    for token in tokens:
        # Check for fallback syntax: {{token_key|fallback}}
        if "|" in token:
            key, default_val = token.split("|", 1)
            key = key.strip().lower()
            default_val = default_val.strip()
        else:
            key = token.strip().lower()
            default_val = None

        raw_val = context.get(key)
        if raw_val is not None and str(raw_val).strip() != "":
            replacement = str(raw_val).strip()
            replaced_map[token] = replacement
        elif default_val is not None:
            replacement = default_val
            replaced_map[token] = replacement
        else:
            # Token could not be satisfied
            missing_tokens.append(token)
            replacement = f"[{token}]"

        result = result.replace(f"{{{{{token}}}}}", replacement)

    return result, replaced_map, missing_tokens


def preview_personalization(
    request: PersonalizePreviewRequest, db: Session | None = None
) -> PersonalizePreviewResponse:
    """
    Simulates personalization for a message template.
    Uses real audience member data from database if audience_member_id is supplied,
    augmented by custom_attributes.
    """
    context: dict[str, str | None] = {}

    # Set default standard tokens
    context["name"] = "Citizen"
    context["full_name"] = "Citizen"
    context["language"] = "English"
    context["preferred_language"] = "English"
    context["phone"] = "1800-000-111"
    context["email"] = "resident@example.com"

    # If DB and audience_member_id supplied, pull real member data
    if db is not None and request.audience_member_id:
        member = (
            db.query(AudienceMember)
            .filter(AudienceMember.id == request.audience_member_id)
            .first()
        )
        if member:
            context["name"] = member.full_name
            context["full_name"] = member.full_name
            context["email"] = member.email or context["email"]
            context["phone"] = member.phone or context["phone"]
            context["preferred_language"] = member.preferred_language or "English"
            context["language"] = member.preferred_language or "English"

    # Merge custom user attributes
    for k, v in request.custom_attributes.items():
        context[k.lower()] = v

    tokens_found = extract_tokens(request.template_text)
    rendered, replaced_map, missing = render_personalization(
        request.template_text, context
    )

    return PersonalizePreviewResponse(
        original_text=request.template_text,
        personalized_text=rendered,
        tokens_found=tokens_found,
        tokens_replaced=replaced_map,
        missing_tokens=missing,
    )


def generate_segment_variants(
    request: SegmentVariantRequest, db: Session
) -> SegmentVariantResponse:
    """
    Evaluates segment criteria against audience members and produces sample personalized variants.
    """
    segment = db.query(Segment).filter(Segment.id == request.segment_id).first()
    segment_name = segment.name if segment else f"Segment #{request.segment_id}"
    criteria = segment.criteria if segment else {}

    # Query audience members
    query = db.query(AudienceMember)

    # Filter by preferred_language if specified in criteria
    if criteria and isinstance(criteria, dict):
        target_lang = criteria.get("language") or criteria.get("preferred_language")
        if target_lang:
            query = query.filter(AudienceMember.preferred_language == target_lang)

    total_count = query.count()
    members = query.limit(request.sample_limit).all()

    # If criteria yielded no members, fallback to general audience sample
    if not members:
        members = db.query(AudienceMember).limit(request.sample_limit).all()
        total_count = len(members)

    sample_variants: list[SegmentVariantItem] = []
    for m in members:
        member_context = {
            "name": m.full_name,
            "full_name": m.full_name,
            "email": m.email,
            "phone": m.phone,
            "language": m.preferred_language or "English",
            "preferred_language": m.preferred_language or "English",
        }
        personalized, _, _ = render_personalization(request.base_text, member_context)
        sample_variants.append(
            SegmentVariantItem(
                audience_member_id=m.id,
                full_name=m.full_name,
                preferred_language=m.preferred_language or "English",
                phone=m.phone,
                email=m.email,
                personalized_content=personalized,
            )
        )

    return SegmentVariantResponse(
        segment_id=request.segment_id,
        segment_name=segment_name,
        criteria=criteria if isinstance(criteria, dict) else {},
        total_matched_members=total_count,
        sample_variants=sample_variants,
    )

