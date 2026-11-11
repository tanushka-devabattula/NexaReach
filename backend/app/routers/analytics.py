from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.models.models import (
    Campaign, Message, DeliveryLog, Feedback, AudienceMember
)

router = APIRouter(prefix="/analytics", tags=["Analytics & Feedback"])


class FeedbackCreate(BaseModel):
    message_id: int = Field(gt=0)
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


@router.get("/overview")
def analytics_overview(db: Session = Depends(get_db)):
    total = db.query(Message).count()
    sent = db.query(Message).filter(Message.status == "sent").count()
    delivered = db.query(Message).filter(Message.status == "delivered").count()
    read = db.query(Message).filter(Message.status == "read").count()
    failed = db.query(Message).filter(Message.status == "failed").count()
    pending = db.query(Message).filter(Message.status == "pending").count()
    campaigns = db.query(Campaign).count()
    feedback_count = db.query(Feedback).count()

    successful = sent + delivered + read

    return {
        "total_messages": total,
        "sent": sent,
        "delivered": delivered,
        "read": read,
        "failed": failed,
        "pending": pending,
        "successful": successful,
        "delivery_rate": round(successful / total * 100, 2) if total else 0,
        "failure_rate": round(failed / total * 100, 2) if total else 0,
        "total_campaigns": campaigns,
        "total_feedback": feedback_count,
    }


@router.get("/campaigns")
def campaign_analytics(db: Session = Depends(get_db)):
    campaigns = db.query(Campaign).order_by(Campaign.id.desc()).all()
    results = []

    for campaign in campaigns:
        messages = db.query(Message).filter(
            Message.campaign_id == campaign.id
        )
        total = messages.count()
        sent = messages.filter(Message.status == "sent").count()
        delivered = messages.filter(Message.status == "delivered").count()
        read = messages.filter(Message.status == "read").count()
        failed = messages.filter(Message.status == "failed").count()

        results.append({
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "campaign_status": campaign.status,
            "total_messages": total,
            "sent": sent,
            "delivered": delivered,
            "read": read,
            "failed": failed,
            "success_rate": round((sent + delivered + read) / total * 100, 2) if total else 0,
        })

    return results


@router.get("/messages")
def message_analytics(
    limit: int = Query(default=100, ge=1, le=500),
    campaign_id: int | None = Query(default=None, gt=0),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
):
    query = db.query(Message)
    if campaign_id is not None:
        query = query.filter(Message.campaign_id == campaign_id)
    if status_filter:
        query = query.filter(Message.status == status_filter.lower())

    messages = query.order_by(Message.id.desc()).limit(limit).all()

    return [{
        "id": item.id,
        "tracking_id": item.tracking_id,
        "campaign_id": item.campaign_id,
        "audience_member_id": item.audience_member_id,
        "channel": item.channel,
        "language": item.language,
        "status": item.status,
        "provider_message_id": item.provider_message_id,
        "created_at": item.created_at,
        "content": item.content,
    } for item in messages]


@router.post("/feedback", status_code=201)
def submit_feedback(data: FeedbackCreate, db: Session = Depends(get_db)):
    message = db.query(Message).filter(Message.id == data.message_id).first()
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")

    feedback = Feedback(
        message_id=message.id,
        audience_member_id=message.audience_member_id,
        rating=data.rating,
        comment=data.comment,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return {
        "id": feedback.id,
        "message_id": feedback.message_id,
        "rating": feedback.rating,
        "comment": feedback.comment,
        "detail": "Feedback submitted successfully",
    }


@router.get("/feedback")
def list_feedback(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    records = db.query(Feedback).order_by(Feedback.id.desc()).limit(limit).all()
    return [{
        "id": item.id,
        "message_id": item.message_id,
        "audience_member_id": item.audience_member_id,
        "rating": item.rating,
        "comment": item.comment,
        "sentiment": item.sentiment,
        "created_at": item.created_at,
    } for item in records]


@router.get("/feedback/summary")
def feedback_summary(db: Session = Depends(get_db)):
    average = db.query(func.avg(Feedback.rating)).scalar()
    count = db.query(Feedback).count()
    distribution = (
        db.query(Feedback.rating, func.count(Feedback.id))
        .filter(Feedback.rating.isnot(None))
        .group_by(Feedback.rating)
        .all()
    )

    return {
        "total_feedback": count,
        "average_rating": round(float(average), 2) if average is not None else 0,
        "rating_distribution": {
            str(rating): amount for rating, amount in distribution
        },
    }
