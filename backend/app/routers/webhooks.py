"""WhatsApp webhooks: delivery-status updates and incoming replies.

Security: every request must carry X-WhatsApp-Signature = HMAC-SHA256(raw body, secret)
as hex, where secret = WHATSAPP_WEBHOOK_SECRET. If the secret is not set the request is
rejected, EXCEPT in mock/dev mode (WHATSAPP_MOCK=1, the default) where unsigned calls are
accepted so you can test locally. Never run with WHATSAPP_MOCK=1 on a public server.
"""
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import AudienceMember, DeliveryLog, Feedback, Message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook/whatsapp", tags=["WhatsApp Webhooks"])

ALLOWED_STATUSES = {"sent", "delivered", "read", "failed"}


def _validate_signature(body: bytes, signature: str) -> bool:
    secret = os.getenv("WHATSAPP_WEBHOOK_SECRET")
    if not secret:
        return os.getenv("WHATSAPP_MOCK", "1") == "1"  # fail closed unless in mock mode
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


async def _verified_json(request: Request, signature: str) -> dict:
    body = await request.body()
    if not _validate_signature(body, signature or ""):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")
    try:
        payload = json.loads(body or b"{}")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Body must be valid JSON")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Body must be a JSON object")
    return payload


@router.post("/status", summary="WhatsApp delivery status webhook")
async def whatsapp_status(
    request: Request,
    x_signature: str = Header(None, alias="X-WhatsApp-Signature"),
    db: Session = Depends(get_db),
):
    payload = await _verified_json(request, x_signature)
    provider_id = payload.get("provider_message_id")
    new_status = str(payload.get("status") or "").lower()
    if not provider_id or not new_status:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing fields")
    if new_status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown status '{new_status}'. Allowed: {', '.join(sorted(ALLOWED_STATUSES))}",
        )

    msg = db.query(Message).filter(Message.provider_message_id == provider_id).first()
    if msg:
        msg.status = new_status
        for log in db.query(DeliveryLog).filter(DeliveryLog.message_id == msg.id).all():
            log.status = new_status
            if new_status == "failed":
                log.provider_response = str(payload.get("error") or "Provider reported failure")
            elif new_status == "delivered" and log.sent_at is None:
                log.sent_at = datetime.utcnow()
        db.commit()
    else:
        logger.warning("WhatsApp status for unknown provider_message_id %s", provider_id)
    return {"detail": "WhatsApp status webhook processed", "matched": msg is not None, "payload": payload}


@router.post("/reply", summary="Incoming reply webhook from WhatsApp")
async def whatsapp_reply(
    request: Request,
    x_signature: str = Header(None, alias="X-WhatsApp-Signature"),
    db: Session = Depends(get_db),
):
    """A reply is stored as Feedback linked to the message it answers.

    We find that message by `context_message_id` (WhatsApp tells us which message was
    replied to) or, failing that, by the sender's phone number (`from`).
    A reply we cannot link to a sent message is NOT stored (there is nothing to attach it to).
    """
    payload = await _verified_json(request, x_signature)
    text = str(payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing reply text")

    original = None
    context_id = payload.get("context_message_id")
    if context_id:
        original = db.query(Message).filter(Message.provider_message_id == context_id).first()
    sender = payload.get("from")
    if original is None and sender:
        original = (
            db.query(Message)
            .join(AudienceMember, Message.audience_member_id == AudienceMember.id)
            .filter(AudienceMember.phone == sender, Message.channel == "WHATSAPP")
            .order_by(Message.id.desc())
            .first()
        )

    if original is None:
        logger.warning("WhatsApp reply could not be matched to a sent message")
        return {
            "detail": "WhatsApp reply received but could not be matched to a sent message; not stored",
            "matched": False,
        }

    feedback = Feedback(
        message_id=original.id,
        audience_member_id=original.audience_member_id,
        comment=text,
    )
    db.add(feedback)
    db.commit()
    return {"detail": "WhatsApp reply webhook processed", "matched": True, "feedback_id": feedback.id}