
from datetime import datetime

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
    created_at = Column(DateTime, default=datetime.utcnow)


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


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    audience_member_id = Column(
        Integer, ForeignKey("audience_members.id"), nullable=False
    )
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)
    channel = Column(String(50), nullable=False)
    language = Column(String(50), default="English")
    content = Column(Text, nullable=False)
    status = Column(String(50), default="pending", nullable=False)
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


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    audience_member_id = Column(
        Integer, ForeignKey("audience_members.id"), nullable=True
    )
    rating = Column(Integer, nullable=True)
    comment = Column(Text, nullable=True)
    sentiment = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
