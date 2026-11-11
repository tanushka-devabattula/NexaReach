"""Campaign sending service.

Sends APPROVED campaign content to eligible audience members:
  * only members who gave consent
  * only content whose language matches the member's preferred language
  * only members who have the contact detail the channel needs
  * prevent duplicate successful sends; allow a new attempt after a failed send
Every attempt is stored as a Message (with tracking_id) and a DeliveryLog.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.services.personalization_service import members_matching_segment

from app.models.models import (
    AudienceMember,
    Campaign,
    CampaignContent,
    DeliveryLog,
    DeviceToken,
    Message,
    Segment,
)
from app.services.channels.channel_factory import (
    get_email_channel,
    get_push_channel,
    get_sms_channel,
    get_whatsapp_channel,
)

logger = logging.getLogger(__name__)

# The lambdas look the function up when called, so tests can patch them.
_CHANNEL_GETTERS = {
    "SMS": lambda: get_sms_channel(),
    "EMAIL": lambda: get_email_channel(),
    "WHATSAPP": lambda: get_whatsapp_channel(),
    "PUSH": lambda: get_push_channel(),
}

# Which contact detail each channel needs.
_REQUIRED_CONTACT = {"SMS": "phone", "WHATSAPP": "phone", "EMAIL": "email"}


def _fill_placeholders(text: str, member: AudienceMember) -> str:
    values = {
        "name": member.full_name or "",
        "email": member.email or "",
        "phone": member.phone or "",
        "language": member.preferred_language or "",
    }
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value).replace("{" + key + "}", value)
    return text


def _members_for_campaign(campaign: Campaign, db: Session) -> List[AudienceMember]:
    """Return only audience members matching the campaign's saved segment."""
    if campaign.segment_id is None:
        return db.query(AudienceMember).all()

    segment = db.query(Segment).filter(Segment.id == campaign.segment_id).first()
    if segment is None:
        return []

    return members_matching_segment(segment, db)


# Channels a fallback order may contain.
SUPPORTED_CHANNELS = ("WHATSAPP", "SMS", "EMAIL", "PUSH")
# A member who already has a message in one of these states has been reached.
_REACHED_STATES = ("sent", "delivered", "read")


def _normalize_order(raw: Any) -> List[str]:
    """['whatsapp','SMS','sms'] -> ['WHATSAPP','SMS']. Unknown names are ignored."""
    if not isinstance(raw, list):
        return []
    order: List[str] = []
    for item in raw:
        name = str(item).strip().upper()
        if name in SUPPORTED_CHANNELS:
            if name not in order:
                order.append(name)
        else:
            logger.warning("Ignoring unsupported channel %r in fallback_order", item)
    return order


def _recipient_for(member: AudienceMember, channel: str, db: Session):
    """Returns (recipient_dict, None) or (None, reason_it_cannot_be_used)."""
    if channel == "PUSH":
        token = (
            db.query(DeviceToken)
            .filter(DeviceToken.audience_member_id == member.id, DeviceToken.active == True)  # noqa: E712
            .order_by(DeviceToken.id.desc())
            .first()
        )
        if token is None:
            return None, "missing device_token"
        return {"device_token": token.token, "email": member.email, "phone": member.phone}, None
    needed = _REQUIRED_CONTACT.get(channel)
    if needed and not getattr(member, needed):
        return None, f"missing {needed}"
    return {"email": member.email, "phone": member.phone}, None


def _deliver(db: Session, campaign: Campaign, member: AudienceMember, content: CampaignContent,
             channel: str, recipient: Dict[str, Any]):
    """Create the Message + DeliveryLog and call the channel. Returns (ok, error_text)."""
    text = _fill_placeholders(content.content, member)
    message = Message(
        campaign_id=campaign.id,
        audience_member_id=member.id,
        channel=channel,
        language=content.language or "English",
        content=text,
        status="pending",
    )
    db.add(message)
    db.flush()  # gives message.id and tracking_id

    try:
        result = _CHANNEL_GETTERS[channel]().send(text, recipient)
    except Exception as err:  # the provider crashed: record it, do not hide it
        logger.exception("Channel %s raised an error", channel)
        result = {"success": False, "provider_message_id": None, "error": str(err)}

    ok = bool(result.get("success"))
    message.status = "sent" if ok else "failed"
    message.provider_message_id = result.get("provider_message_id")
    error_text = None if ok else (result.get("error") or "Unknown error")
    db.add(
        DeliveryLog(
            message_id=message.id,
            channel=channel,
            status=message.status,
            provider_response=error_text,
            sent_at=datetime.utcnow() if ok else None,
            provider_message_id=message.provider_message_id,
        )
    )
    return ok, error_text


def _send_with_fallback(campaign: Campaign, contents: List[CampaignContent],
                        members: List[AudienceMember], order: List[str], db: Session,
                        allow_failed_retry: bool = False) -> Dict[str, Any]:
    """Per member: try the channels in `order`; stop at the first one that works.

    * a channel is skipped if there is no approved content for it in the member's language,
      the member lacks the needed contact detail / device token, or it was already tried
    * a failed attempt moves on to the next channel in the order
    * a member who was already reached is never messaged again
    Counts: `sent` / `failed` / `skipped` are per MEMBER; `channels` counts each attempt.
    """
    content_for = {}
    for content in contents:  # first approved content per (channel, language) wins
        content_for.setdefault(((content.channel or "SMS").upper(), (content.language or "").lower()), content)

    channels: Dict[str, Dict[str, int]] = {}
    skip_reasons: List[str] = []
    sent = failed = skipped = attempts = fallback_used = 0

    def stats(name: str) -> Dict[str, int]:
        return channels.setdefault(name, {"sent": 0, "failed": 0, "skipped": 0})

    for member in members:
        who = member.full_name or f"member {member.id}"

        if not member.consent:
            skipped += 1
            skip_reasons.append(f"{who}: no consent")
            continue

        reached = (
            db.query(Message)
            .filter(
                Message.campaign_id == campaign.id,
                Message.audience_member_id == member.id,
                Message.status.in_(_REACHED_STATES),
            )
            .first()
        )
        if reached:
            skipped += 1
            skip_reasons.append(f"{who}: Duplicate delivery prevented (already delivered via {reached.channel})")
            continue

        language = (member.preferred_language or "").lower()
        not_used: List[str] = []
        tried = 0
        success_channel = None

        for channel in order:
            content = content_for.get((channel, language))
            if content is None:
                not_used.append(f"{channel}: no approved {member.preferred_language} content")
                continue
            if channel not in _CHANNEL_GETTERS:
                not_used.append(f"{channel}: unsupported channel")
                continue
            already_tried = (
                db.query(Message)
                .filter(
                    Message.campaign_id == campaign.id,
                    Message.audience_member_id == member.id,
                    Message.channel == channel,
                )
                .order_by(Message.id.desc())
                .first()
            )
            if already_tried and not (
                allow_failed_retry and already_tried.status == "failed"
            ):
                not_used.append(f"{channel}: already attempted")
                continue
            recipient, problem = _recipient_for(member, channel, db)
            if recipient is None:
                not_used.append(f"{channel}: {problem}")
                continue

            tried += 1
            attempts += 1
            ok, error_text = _deliver(db, campaign, member, content, channel, recipient)
            if ok:
                stats(channel)["sent"] += 1
                success_channel = channel
                break
            stats(channel)["failed"] += 1
            skip_reasons.append(f"{who} ({channel}): send failed ({error_text}); trying next channel")

        if success_channel:
            sent += 1
            if success_channel != order[0]:
                fallback_used += 1
        elif tried:
            failed += 1  # every channel we tried failed
        else:
            skipped += 1
            skip_reasons.append(f"{who}: " + "; ".join(not_used))

    db.commit()
    return {
        "campaign_id": campaign.id,
        "total_audience_considered": len(members),
        "total_considered": len(members),
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
        "queued": 0,
        "sent_count": sent,
        "failed_count": failed,
        "skipped_count": skipped,
        "channels": channels,
        "per_channel_summary": channels,
        "skip_reasons": skip_reasons,
        "fallback_order": order,
        "fallback_used": fallback_used,
        "attempts": attempts,
    }


def send_campaign_messages(
    campaign_id: int,
    db: Session,
    allow_failed_retry: bool = False,
) -> Dict[str, Any]:
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    contents = (
        db.query(CampaignContent)
        .filter(CampaignContent.campaign_id == campaign_id, CampaignContent.status == "approved")
        .all()
    )
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign has no approved content to send.",
        )

    members = _members_for_campaign(campaign, db)

    # A saved fallback order switches on the "try the next channel" behaviour.
    order = _normalize_order(getattr(campaign, "fallback_order", None))
    if order:
        return _send_with_fallback(
            campaign, contents, members, order, db,
            allow_failed_retry=allow_failed_retry,
        )

    channels: Dict[str, Dict[str, int]] = {}
    skip_reasons: List[str] = []
    sent = failed = skipped = 0

    for content in contents:
        channel_name = (content.channel or "SMS").upper()
        stats = channels.setdefault(channel_name, {"sent": 0, "failed": 0, "skipped": 0})

        for member in members:
            who = member.full_name or f"member {member.id}"

            def skip(reason: str):
                nonlocal skipped
                skipped += 1
                stats["skipped"] += 1
                skip_reasons.append(f"{who} ({channel_name}): {reason}")

            if not member.consent:
                skip("no consent")
                continue
            if (member.preferred_language or "").lower() != (content.language or "").lower():
                skip(f"content language {content.language} does not match {member.preferred_language}")
                continue
            needed = _REQUIRED_CONTACT.get(channel_name)
            if needed and not getattr(member, needed):
                skip(f"missing {needed}")
                continue
            if channel_name not in _CHANNEL_GETTERS:
                skip("unsupported channel")
                continue
            already = (
                db.query(Message)
                .filter(
                    Message.campaign_id == campaign.id,
                    Message.audience_member_id == member.id,
                    Message.channel == channel_name,
                )
                .order_by(Message.id.desc())
                .first()
            )
            if already and not (
                allow_failed_retry and already.status == "failed"
            ):
                skip("Duplicate delivery prevented (already attempted)")
                continue

            recipient, problem = _recipient_for(member, channel_name, db)
            if recipient is None:
                skip(problem)
                continue

            text = _fill_placeholders(content.content, member)
            message = Message(
                campaign_id=campaign.id,
                audience_member_id=member.id,
                channel=channel_name,
                language=content.language or "English",
                content=text,
                status="pending",
            )
            db.add(message)
            db.flush()  # gives message.id and tracking_id

            try:
                result = _CHANNEL_GETTERS[channel_name]().send(text, recipient)
            except Exception as err:  # provider crashed: record it, do not hide it
                logger.exception("Channel %s raised an error", channel_name)
                result = {"success": False, "provider_message_id": None, "error": str(err)}

            ok = bool(result.get("success"))
            message.status = "sent" if ok else "failed"
            message.provider_message_id = result.get("provider_message_id")
            db.add(
                DeliveryLog(
                    message_id=message.id,
                    channel=channel_name,
                    status=message.status,
                    provider_response=None if ok else (result.get("error") or "Unknown error"),
                    sent_at=datetime.utcnow() if ok else None,
                    provider_message_id=message.provider_message_id,
                )
            )
            if ok:
                sent += 1
                stats["sent"] += 1
            else:
                failed += 1
                stats["failed"] += 1

    db.commit()

    return {
        "campaign_id": campaign.id,
        "total_audience_considered": len(members),
        "total_considered": len(members),
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
        "queued": 0,
        "sent_count": sent,
        "failed_count": failed,
        "skipped_count": skipped,
        "channels": channels,
        "per_channel_summary": channels,
        "skip_reasons": skip_reasons,
    }