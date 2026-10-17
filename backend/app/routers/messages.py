
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import (
    Message,
    Campaign,
    AudienceMember,
    Template,
)
from app.schemas.message import MessageCreate, MessageResponse

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.post(
    "",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_message(
    message_data: MessageCreate,
    db: Session = Depends(get_db),
):
    campaign = db.query(Campaign).filter(
        Campaign.id == message_data.campaign_id
    ).first()

    if campaign is None:
        raise HTTPException(
            status_code=404,
            detail="Campaign not found",
        )

    audience_member = db.query(AudienceMember).filter(
        AudienceMember.id == message_data.audience_member_id
    ).first()

    if audience_member is None:
        raise HTTPException(
            status_code=404,
            detail="Audience member not found",
        )

    if message_data.template_id is not None:
        template = db.query(Template).filter(
            Template.id == message_data.template_id
        ).first()

        if template is None:
            raise HTTPException(
                status_code=404,
                detail="Template not found",
            )

    message = Message(
        campaign_id=message_data.campaign_id,
        audience_member_id=message_data.audience_member_id,
        template_id=message_data.template_id,
        channel=message_data.channel,
        language=message_data.language,
        content=message_data.content,
        status="pending",
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message


@router.get("", response_model=list[MessageResponse])
def list_messages(db: Session = Depends(get_db)):
    return (
        db.query(Message)
        .order_by(Message.id.desc())
        .all()
    )


@router.get("/{message_id}", response_model=MessageResponse)
def get_message(
    message_id: int,
    db: Session = Depends(get_db),
):
    message = db.query(Message).filter(
        Message.id == message_id
    ).first()

    if message is None:
        raise HTTPException(
            status_code=404,
            detail="Message not found",
        )

    return message
