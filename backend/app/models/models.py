from datetime import datetime
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)

from app.db.session import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255))


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    organization = Column(String(150), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AudienceMember(Base):
    __tablename__ = "audience_members"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(30), nullable=True)
    preferred_language = Column(String(50), default="English")
    created_at = Column(DateTime, default=datetime.utcnow)
    consent = Column(Boolean, default=False, nullable=False)
    # Task 4 profile fields (all optional)
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    occupation = Column(String(100), nullable=True)
    department = Column(String(150), nullable=True)
    preferred_channel = Column(String(20), nullable=True)


class Segment(Base):
    __tablename__ = "segments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text)
    criteria = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    objective = Column(Text)
    status = Column(String(50), default="draft", nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    segment_id = Column(Integer, ForeignKey("segments.id"), nullable=True)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    fallback_order = Column(JSON, nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    schedule_status = Column(String(30), default="not_scheduled", nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    next_retry_at = Column(DateTime, nullable=True)
    last_run_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)


class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    channel = Column(String(50), nullable=False)
    language = Column(String(50), default="English")
    subject = Column(String(255), nullable=True)
    body = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(Integer, primary_key=True, index=True)
    audience_member_id = Column(Integer, ForeignKey("audience_members.id"), nullable=False)
    token = Column(String(255), nullable=False, unique=True)
    platform = Column(String(50), nullable=True)  # e.g., 'web', 'android', 'ios'
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WhatsAppTemplate(Base):
    __tablename__ = "whatsapp_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    content_template = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)




class DeliveryLog(Base):
    __tablename__ = "delivery_logs"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    channel = Column(String(50), nullable=False)
    status = Column(String(50), default="pending", nullable=False)
    provider_response = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    provider_message_id = Column(String, nullable=True)


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    audience_member_id = Column(Integer, ForeignKey("audience_members.id"), nullable=True)
    rating = Column(Integer, nullable=True)
    comment = Column(Text, nullable=True)
    sentiment = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AIContentHistory(Base):
    __tablename__ = "ai_content_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    prompt = Column(Text, nullable=False)
    channel = Column(String(50), nullable=True)
    tone = Column(String(50), nullable=True)
    language = Column(String(50), default="English")
    generated_content = Column(Text, nullable=False)
    provider = Column(String(50), default="offline-fallback")
    is_fallback = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ContentReview(Base):
    __tablename__ = "content_reviews"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)
    campaign_content_id = Column(Integer, ForeignKey("campaign_contents.id"), nullable=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(50), default="pending_review", nullable=False)
    compliance_score = Column(Integer, default=100)
    compliance_issues = Column(JSON, nullable=True)
    readability_metrics = Column(JSON, nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TranslationRecord(Base):
    __tablename__ = "translation_records"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    source_text = Column(Text, nullable=False)
    source_language = Column(String(50), default="English")
    target_language = Column(String(50), nullable=False)
    translated_text = Column(Text, nullable=False)
    status = Column(String(50), default="Auto-translated", nullable=True)
    is_rtl = Column(Boolean, default=False)
    is_fallback = Column(Boolean, default=True)
    provider = Column(String(50), default="offline-fallback")
    created_at = Column(DateTime, default=datetime.utcnow)


class ComplianceRule(Base):
    __tablename__ = "compliance_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_type = Column(String(50), nullable=False)  # banned_word, mandatory_phrase, max_length, etc.
    pattern = Column(String(255), nullable=False)
    channel = Column(String(50), nullable=True)     # SMS, WhatsApp, Email, or all
    severity = Column(String(50), default="error", nullable=False)  # error, warning, info
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ContentVariant(Base):
    __tablename__ = "content_variants"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    segment_id = Column(Integer, ForeignKey("segments.id"), nullable=True)
    language = Column(String(50), default="English", nullable=False)
    variant_text = Column(Text, nullable=False)
    sample_audience_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class CampaignContent(Base):
    __tablename__ = "campaign_contents"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    language = Column(String(50), default="English", nullable=False)
    segment_id = Column(Integer, ForeignKey("segments.id"), nullable=True)
    channel = Column(String(50), default="SMS", nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(50), default="draft", nullable=False)  # draft, in_review, approved, rejected
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# ---------------------------------------------------------------------------
# Message model (restored)
# ---------------------------------------------------------------------------
class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    audience_member_id = Column(Integer, ForeignKey("audience_members.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)
    channel = Column(String(50), nullable=False)
    language = Column(String(50), default="English", nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(50), default="pending", nullable=False)
    tracking_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    provider_message_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships (optional)
    delivery_logs = None  # will be populated by SQLAlchemy relationship in DeliveryLog if needed
