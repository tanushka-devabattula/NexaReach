"""Database-backed scheduled campaign execution with basic retries."""

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.models import Campaign
from app.services.campaign_send_service import send_campaign_messages

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone="UTC")


def _retry_or_fail(campaign: Campaign, db: Session, error: str) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    campaign.last_error = str(error)[:2000]
    campaign.last_run_at = now

    if campaign.retry_count < campaign.max_retries:
        campaign.retry_count += 1
        campaign.schedule_status = "retry_pending"
        campaign.next_retry_at = now + timedelta(minutes=campaign.retry_count)
        logger.warning(
            "Campaign %s retry %s scheduled", campaign.id, campaign.retry_count
        )
    else:
        campaign.schedule_status = "failed"
        campaign.next_retry_at = None

    db.commit()


def process_due_campaigns() -> None:
    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        due_campaigns = (
            db.query(Campaign)
            .filter(
                or_(
                    (
                        (Campaign.schedule_status == "scheduled")
                        & (Campaign.scheduled_at.isnot(None))
                        & (Campaign.scheduled_at <= now)
                    ),
                    (
                        (Campaign.schedule_status == "retry_pending")
                        & (Campaign.next_retry_at.isnot(None))
                        & (Campaign.next_retry_at <= now)
                    ),
                )
            )
            .order_by(Campaign.scheduled_at.asc())
            .all()
        )

        for item in due_campaigns:
            campaign_id = item.id
            item.schedule_status = "processing"
            item.last_run_at = now
            db.commit()

            try:
                result = send_campaign_messages(campaign_id, db, allow_failed_retry=True)
                campaign = (
                    db.query(Campaign)
                    .filter(Campaign.id == campaign_id)
                    .first()
                )
                if campaign is None:
                    continue

                failed_count = int(result.get("failed", 0))
                if failed_count > 0:
                    _retry_or_fail(
                        campaign, db, f"{failed_count} delivery failure(s)"
                    )
                else:
                    campaign.schedule_status = "completed"
                    campaign.next_retry_at = None
                    campaign.last_error = None
                    campaign.last_run_at = (
                        datetime.now(timezone.utc).replace(tzinfo=None)
                    )
                    db.commit()

            except Exception as exc:
                db.rollback()
                campaign = (
                    db.query(Campaign)
                    .filter(Campaign.id == campaign_id)
                    .first()
                )
                if campaign is not None:
                    _retry_or_fail(campaign, db, str(exc))
                logger.exception("Campaign %s processing failed", campaign_id)

    except Exception:
        db.rollback()
        logger.exception("Scheduler processing error")
    finally:
        db.close()


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.add_job(
            process_due_campaigns,
            trigger="interval",
            seconds=30,
            id="scheduled_campaign_checker",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
        logger.info("Campaign scheduler started")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Campaign scheduler stopped")
