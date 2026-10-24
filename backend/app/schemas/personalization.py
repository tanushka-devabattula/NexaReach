from pydantic import BaseModel, Field


class PersonalizePreviewRequest(BaseModel):
    template_text: str = Field(min_length=1, description="Message containing tokens like {{name}}")
    audience_member_id: int | None = Field(default=None, description="Optional audience member ID to pull live values")
    custom_attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Optional ad-hoc attribute overrides (e.g. {'name': 'Ramesh', 'city': 'Hyderabad'})"
    )


class PersonalizePreviewResponse(BaseModel):
    original_text: str
    personalized_text: str
    tokens_found: list[str]
    tokens_replaced: dict[str, str]
    missing_tokens: list[str]


class SegmentVariantRequest(BaseModel):
    base_text: str = Field(min_length=1, description="Base message template")
    segment_id: int = Field(description="Segment ID to evaluate criteria against")
    sample_limit: int = Field(default=5, ge=1, le=50, description="Max sample audience members to preview")


class SegmentVariantItem(BaseModel):
    audience_member_id: int
    full_name: str
    preferred_language: str
    phone: str | None = None
    email: str | None = None
    personalized_content: str


class SegmentVariantResponse(BaseModel):
    segment_id: int
    segment_name: str
    criteria: dict | None = None
    total_matched_members: int
    sample_variants: list[SegmentVariantItem]

