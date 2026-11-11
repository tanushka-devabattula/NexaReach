"""Push notification router.

Register/unregister device tokens (JSON body) and send a test notification.
IMPORTANT: sending is a MOCK unless a real provider (Firebase) is added. Registering a
token stores it for real; no real notification reaches a phone yet.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.models import AudienceMember, DeviceToken
from app.services.channels.channel_factory import get_push_channel

router = APIRouter(prefix="/push", tags=["Push Notifications"])


class PushRegisterRequest(BaseModel):
    token: str = Field(min_length=1, max_length=255)
    platform: Optional[str] = Field(default=None, max_length=50)
    audience_member_id: Optional[int] = None
    email: Optional[str] = Field(default=None, description="Used to find the audience member if no id is given")


class PushUnregisterRequest(BaseModel):
    token: str = Field(min_length=1, max_length=255)


@router.post("/register", summary="Register a device token for push notifications")
def register_token(data: PushRegisterRequest, db: Session = Depends(get_db)):
    if data.audience_member_id is not None:
        member = db.query(AudienceMember).filter(AudienceMember.id == data.audience_member_id).first()
    elif data.email:
        member = (
            db.query(AudienceMember)
            .filter(func.lower(AudienceMember.email) == data.email.strip().lower())
            .first()
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide audience_member_id or the email the audience member registered with.",
        )
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audience member not found")

    existing = db.query(DeviceToken).filter(DeviceToken.token == data.token).first()
    if existing:
        existing.audience_member_id = member.id
        existing.platform = data.platform
        existing.active = True
    else:
        db.add(DeviceToken(audience_member_id=member.id, token=data.token, platform=data.platform, active=True))
    db.commit()
    return {"detail": "Device token registered", "audience_member_id": member.id}


@router.post("/unregister", summary="Unregister a device token")
def unregister_token(data: PushUnregisterRequest, db: Session = Depends(get_db)):
    token_obj = db.query(DeviceToken).filter(DeviceToken.token == data.token).first()
    if not token_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    token_obj.active = False
    db.commit()
    return {"detail": "Device token deactivated"}


@router.post(
    "/test",
    summary="Send a test push notification to a token (mock unless a real provider is added)",
    dependencies=[Depends(get_current_user)],
)
def test_push(token: str, message: str = "Test push notification", db: Session = Depends(get_db)):
    token_obj = db.query(DeviceToken).filter(DeviceToken.token == token, DeviceToken.active == True).first()  # noqa: E712
    if not token_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active token not found")
    try:
        channel = get_push_channel()
    except NotImplementedError as e:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))
    result = channel.send(message, {"device_token": token})
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=result.get("error", "Push send failed"))
    return {"detail": "Push mock send succeeded", "provider_message_id": result.get("provider_message_id")}