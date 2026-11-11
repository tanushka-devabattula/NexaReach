"""WhatsApp channel router.
Provides a test endpoint to verify WhatsApp channel configuration.
The endpoint uses the mock channel unless WHATSAPP_MOCK is set to 0, in which
case a NotImplementedError is raised (real integration not in scope).
"""

from fastapi import APIRouter, HTTPException, status
from app.services.channels.channel_factory import get_whatsapp_channel

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])

@router.get("/test", summary="Test WhatsApp channel connectivity")
def test_whatsapp():
    try:
        channel = get_whatsapp_channel()
    except NotImplementedError as e:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))
    # Send a dummy message to a dummy recipient
    result = channel.send("Test WhatsApp message", {"phone": "+1234567890"})
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=result.get("error", "WhatsApp send failed"))
    return {"detail": "WhatsApp mock send succeeded", "provider_message_id": result.get("provider_message_id")}
