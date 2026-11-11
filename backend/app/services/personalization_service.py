
"""Personalization for NexaReach.

1. preview_personalization: fill {{name}} / {name} style tokens using a real
   audience member and/or values the user typed.
2. generate_segment_variants: find segment members, translate once per
   preferred language, then personalize their messages.

Missing tokens are reported in missing_tokens and left untouched.
"""

import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.models import AudienceMember, Segment
from app.schemas.personalization import (
    PersonalizePreviewRequest,
    SegmentVariantRequest,
)
from app.schemas.translation import TranslationRequest
from app.services.translation_service import translate_text


class NotFoundError(Exception):
    """A member or segment the caller asked for does not exist."""


# Supports {{name}}, {{city|Your Town}}, and {name}
_TOKEN_RE = re.compile(
    r"\{\{\s*([^{}]+?)\s*\}\}|\{([A-Za-z_][A-Za-z0-9_]*)\}"
)

# Friendly token name -> AudienceMember column
_ALIASES = {
    "name": "full_name",
    "full_name": "full_name",
    "language": "preferred_language",
    "preferred_language": "preferred_language",
    "email": "email",
    "phone": "phone",
}


def _member_values(
    member: Optional[AudienceMember],
) -> Dict[str, str]:
    """Get personalization values from an audience record."""
    if member is None:
        return {}

    values: Dict[str, str] = {}

    for column in member.__table__.columns.keys():
        value = getattr(member, column, None)

        if value not in (None, "") and not isinstance(value, bool):
            values[column] = str(value)

    for token, column in _ALIASES.items():
        if column in values:
            values[token] = values[column]

    return values


def extract_tokens(text: str) -> List[str]:
    """Return unique raw tokens found in the text."""
    tokens: List[str] = []

    for match in _TOKEN_RE.finditer(text or ""):
        raw = (match.group(1) or match.group(2)).strip()

        if raw not in tokens:
            tokens.append(raw)

    return tokens


def render_personalization(
    text: str,
    values: Dict[str, str],
):
    """Fill tokens and return rendered text, replacements, and missing tokens."""

    replaced: Dict[str, str] = {}
    missing: List[str] = []

    def repl(match):
        raw = (match.group(1) or match.group(2)).strip()
        name, separator, default = raw.partition("|")

        name = name.strip()
        default = default.strip()

        if name in values:
            replaced[name] = values[name]
            return values[name]

        if separator:
            replaced[name] = default
            return default

        if name not in missing:
            missing.append(name)

        return match.group(0)

    return _TOKEN_RE.sub(repl, text or ""), replaced, missing


def _fill(text: str, values: Dict[str, str]):
    rendered, replaced, missing = render_personalization(text, values)

    found = [
        token.partition("|")[0].strip()
        for token in extract_tokens(text)
    ]

    return rendered, found, replaced, missing


def preview_personalization(
    request: PersonalizePreviewRequest,
    db: Session,
) -> Dict[str, Any]:

    template = (request.template_text or "").strip()

    if not template:
        raise ValueError("Message text must not be empty.")

    member = None

    if request.audience_member_id is not None:
        member = (
            db.query(AudienceMember)
            .filter(
                AudienceMember.id == request.audience_member_id
            )
            .first()
        )

        if member is None:
            raise NotFoundError(
                f"Audience member {request.audience_member_id} not found."
            )

    values = _member_values(member)

    values.update({
        key: value
        for key, value in (request.custom_attributes or {}).items()
        if value not in (None, "")
    })

    text, found, replaced, missing = _fill(template, values)

    return {
        "original_text": template,
        "personalized_text": text,
        "tokens_found": found,
        "tokens_replaced": replaced,
        "missing_tokens": missing,
    }


def members_matching_segment(
    segment: Segment,
    db: Session,
) -> List[AudienceMember]:
    """Match legacy criteria and advanced AND/OR segment rules."""

    criteria = (
        segment.criteria
        if isinstance(segment.criteria, dict)
        else {}
    )

    aliases = {
        "language": "preferred_language",
        "preferred_language": "preferred_language",
    }

    valid_columns = set(
        AudienceMember.__table__.columns.keys()
    )

    members = db.query(AudienceMember).all()

    def normalize(value):
        if isinstance(value, bool):
            return str(value).lower()

        return str(value).strip().casefold()

    def evaluate_rule(member, rule):
        """Evaluate one advanced segment rule."""

        if not isinstance(rule, dict):
            return False

        requested_field = rule.get("field")
        field = aliases.get(requested_field, requested_field)

        operator = rule.get("operator", "equals")
        value = rule.get("value")

        if field not in valid_columns or value is None:
            return False

        actual = getattr(member, field, None)

        if operator == "equals":
            return normalize(actual) == normalize(value)

        if operator == "in":
            return (
                isinstance(value, list)
                and bool(value)
                and any(
                    normalize(actual) == normalize(item)
                    for item in value
                    if item is not None
                )
            )

        if field != "age":
            return False

        if actual is None or isinstance(actual, bool):
            return False

        if operator in (
            "greater_than",
            "greater_than_or_equal",
            "less_than",
            "less_than_or_equal",
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
            ):
                return False

            if operator == "greater_than":
                return actual > value

            if operator == "greater_than_or_equal":
                return actual >= value

            if operator == "less_than":
                return actual < value

            return actual <= value

        if operator == "between":
            if (
                not isinstance(value, list)
                or len(value) != 2
                or any(
                    isinstance(item, bool)
                    or not isinstance(item, (int, float))
                    for item in value
                )
                or value[0] > value[1]
            ):
                return False

            return value[0] <= actual <= value[1]

        return False

    # Advanced visual-builder format:
    # {
    #     "logic": "AND",
    #     "rules": [
    #         {"field": "preferred_language", "operator": "equals",
    #          "value": "Telugu"},
    #         {"field": "age", "operator": "between",
    #          "value": [18, 30]}
    #     ]
    # }

    if "rules" in criteria:
        logic = str(criteria.get("logic", "AND")).upper()
        rules = criteria.get("rules")

        if (
            logic not in ("AND", "OR")
            or not isinstance(rules, list)
            or not rules
        ):
            return []

        for rule in rules:
            if not isinstance(rule, dict):
                return []

            field = aliases.get(
                rule.get("field"),
                rule.get("field"),
            )

            if field not in valid_columns:
                return []

        matched = []

        for member in members:
            results = [
                evaluate_rule(member, rule)
                for rule in rules
            ]

            if (
                all(results)
                if logic == "AND"
                else any(results)
            ):
                matched.append(member)

        return matched

    # Backward-compatible legacy JSON format:
    # {"language": "Telugu"}
    # {"gender": "Female", "city": "Hyderabad"}
    # {"min_age": 18, "max_age": 30}

    range_keys = {"min_age", "max_age"}

    unknown = (
        set(criteria)
        - valid_columns
        - set(aliases)
        - range_keys
    )

    if unknown:
        return []

    minimum = criteria.get("min_age")
    maximum = criteria.get("max_age")

    for bound in (minimum, maximum):
        if bound is not None and (
            isinstance(bound, bool)
            or not isinstance(bound, (int, float))
        ):
            return []

    if (
        minimum is not None
        and maximum is not None
        and minimum > maximum
    ):
        return []

    matched = []

    for member in members:
        age = member.age

        if minimum is not None and (
            age is None or age < minimum
        ):
            continue

        if maximum is not None and (
            age is None or age > maximum
        ):
            continue

        accepted = True

        for key, wanted in criteria.items():
            if key in range_keys:
                continue

            column = aliases.get(key, key)

            choices = (
                wanted
                if isinstance(wanted, list)
                else [wanted]
            )

            if not choices:
                accepted = False
                break

            actual = getattr(member, column, None)

            if not any(
                choice is not None
                and normalize(actual) == normalize(choice)
                for choice in choices
            ):
                accepted = False
                break

        if accepted:
            matched.append(member)

    return matched


def generate_segment_variants(
    request: SegmentVariantRequest,
    db: Session,
) -> Dict[str, Any]:

    segment = (
        db.query(Segment)
        .filter(Segment.id == request.segment_id)
        .first()
    )

    if segment is None:
        raise NotFoundError(
            f"Segment with ID {request.segment_id} not found."
        )

    base = (request.base_text or "").strip()

    if not base:
        raise ValueError("Message text must not be empty.")

    members = members_matching_segment(segment, db)
    sample = members[:request.sample_limit]

    # Translate once per preferred language.
    per_language: Dict[str, str] = {}

    for lang in {
        member.preferred_language or "English"
        for member in sample
    }:
        if lang.lower() == "english":
            per_language[lang] = base
        else:
            per_language[lang] = translate_text(
                TranslationRequest(
                    text=base,
                    target_language=lang,
                    source_language="English",
                ),
                db=db,
            ).translated_text

    variants = []

    for member in sample:
        language = member.preferred_language or "English"

        text, *_ = _fill(
            per_language[language],
            _member_values(member),
        )

        variants.append({
            "audience_member_id": member.id,
            "full_name": member.full_name,
            "preferred_language": language,
            "phone": member.phone,
            "email": member.email,
            "personalized_content": text,
        })

    return {
        "segment_id": segment.id,
        "segment_name": segment.name,
        "criteria": segment.criteria,
        "total_matched_members": len(members),
        "sample_variants": variants,
    }


# Old name retained for backward compatibility.
personalize_message = preview_personalization
