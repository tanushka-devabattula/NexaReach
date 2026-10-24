from datetime import datetime
import re
from sqlalchemy.orm import Session

from app.models.models import ContentReview
from app.schemas.review import (
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    ComplianceIssue,
    ReviewDecisionRequest,
    ReviewResponse,
    ReviewSubmitRequest,
)

# Prohibited / misleading terms in official public communications
PROHIBITED_TERMS = [
    r"\b100% cure\b",
    r"\bguaranteed cure\b",
    r"\bmiracle medicine\b",
    r"\bsecret remedy\b",
    r"\bwin cash\b",
    r"\blottery winner\b",
    r"\bclaim prize\b",
    r"\bwire money\b",
    r"\burgent transfer\b",
    r"\bconfidential password\b",
]


def check_compliance(request: ComplianceCheckRequest) -> ComplianceCheckResponse:
    """
    Evaluates message against regulatory, channel, and content compliance rules.
    """
    text = request.content.strip()
    channel = (request.channel or "SMS").upper()
    issues: list[ComplianceIssue] = []
    score = 100

    # Rule 1: Channel length validation
    char_len = len(text)
    if channel == "SMS":
        max_rec = 160
        if char_len > 320:
            score -= 30
            issues.append(
                ComplianceIssue(
                    rule="SMS_LENGTH_HARD_CAP",
                    severity="error",
                    message=f"SMS exceeds multi-part limit (320 chars). Current: {char_len} chars.",
                    passed=False,
                )
            )
        elif char_len > 160:
            score -= 15
            issues.append(
                ComplianceIssue(
                    rule="SMS_LENGTH_SINGLE_SEGMENT",
                    severity="warning",
                    message=f"SMS exceeds 160-char segment limit ({char_len} chars). Will be billed as multiple segments.",
                    passed=False,
                )
            )
        else:
            issues.append(
                ComplianceIssue(
                    rule="SMS_LENGTH",
                    severity="info",
                    message="SMS conforms to single-part standard (<= 160 characters).",
                    passed=True,
                )
            )
    elif channel == "WHATSAPP":
        max_rec = 1024
        if char_len > 1024:
            score -= 20
            issues.append(
                ComplianceIssue(
                    rule="WHATSAPP_LENGTH",
                    severity="warning",
                    message=f"Message is very long for mobile chat ({char_len} chars). Recommend <= 1024 chars.",
                    passed=False,
                )
            )
        else:
            issues.append(
                ComplianceIssue(
                    rule="WHATSAPP_LENGTH",
                    severity="info",
                    message="Length is suitable for WhatsApp delivery.",
                    passed=True,
                )
            )
    elif channel == "EMAIL":
        max_rec = 4000
        if not request.subject or not request.subject.strip():
            score -= 25
            issues.append(
                ComplianceIssue(
                    rule="EMAIL_SUBJECT_REQUIRED",
                    severity="error",
                    message="Subject line is required for Email broadcasts.",
                    passed=False,
                )
            )
        else:
            issues.append(
                ComplianceIssue(
                    rule="EMAIL_SUBJECT_CHECK",
                    severity="info",
                    message="Email subject line is present.",
                    passed=True,
                )
            )
    else:
        max_rec = 500

    # Rule 2: Prohibited / Sensational Claims Check
    found_prohibited = []
    for pattern in PROHIBITED_TERMS:
        if re.search(pattern, text, re.IGNORECASE):
            found_prohibited.append(pattern.replace(r"\b", ""))

    if found_prohibited:
        score -= 40
        issues.append(
            ComplianceIssue(
                rule="PROHIBITED_TERMS",
                severity="error",
                message=f"Message contains prohibited or misleading phrases: {', '.join(found_prohibited)}.",
                passed=False,
            )
        )
    else:
        issues.append(
            ComplianceIssue(
                rule="PROHIBITED_TERMS",
                severity="info",
                message="No prohibited or misleading medical/financial terms detected.",
                passed=True,
            )
        )

    # Rule 3: Placeholder syntax integrity
    unclosed = re.findall(r"\{\{[^}]*$", text) + re.findall(r"^[^{]*\}\}", text)
    if unclosed:
        score -= 25
        issues.append(
            ComplianceIssue(
                rule="PLACEHOLDER_SYNTAX",
                severity="error",
                message="Malformed placeholder token detected (unclosed curly braces).",
                passed=False,
            )
        )
    else:
        issues.append(
            ComplianceIssue(
                rule="PLACEHOLDER_SYNTAX",
                severity="info",
                message="All dynamic placeholders are properly closed and formatted.",
                passed=True,
            )
        )

    # Rule 4: Mandatory Opt-Out / Official Helpline verification
    has_opt_out = bool(re.search(r"\bstop\b|unsubscribe|opt-out", text, re.I))
    has_helpline = bool(re.search(r"\b1800[-\d]+\b|\bhelpline\b|\bhttps?://", text, re.I))

    if not has_opt_out and not has_helpline and channel in ["SMS", "WHATSAPP"]:
        score -= 15
        issues.append(
            ComplianceIssue(
                rule="BROADCAST_TRANSPARENCY",
                severity="warning",
                message="Public awareness broadcasts should include an official helpline (e.g. 1800-000-111) or opt-out notice ('Reply STOP').",
                passed=False,
            )
        )
    else:
        issues.append(
            ComplianceIssue(
                rule="BROADCAST_TRANSPARENCY",
                severity="info",
                message="Broadcast includes verifiable helpline or opt-out disclaimer.",
                passed=True,
            )
        )

    final_score = max(0, min(100, score))
    passed = not any(i.severity == "error" for i in issues) and final_score >= 60

    return ComplianceCheckResponse(
        passed=passed,
        score=final_score,
        issues=issues,
        character_count=char_len,
        max_recommended_characters=max_rec,
        contains_opt_out=has_opt_out,
    )


def submit_for_review(request: ReviewSubmitRequest, db: Session, user_id: int | None = None) -> ContentReview:
    """
    Creates a new ContentReview entry in pending_review status with automated compliance results.
    """
    check_req = ComplianceCheckRequest(
        content=request.content,
        channel=request.channel,
        language=request.language,
    )
    compliance_res = check_compliance(check_req)

    issues_dump = [i.model_dump() for i in compliance_res.issues]

    review = ContentReview(
        campaign_id=request.campaign_id,
        template_id=request.template_id,
        reviewer_id=None,
        status="pending_review",
        compliance_score=compliance_res.score,
        compliance_issues=issues_dump,
        reviewer_notes=request.reviewer_notes,
        created_at=datetime.utcnow(),
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def decide_review(review_id: int, request: ReviewDecisionRequest, db: Session, reviewer_id: int | None = None) -> ContentReview | None:
    """
    Applies review decision: 'approved', 'rejected', or 'changes_requested'.
    """
    review = db.query(ContentReview).filter(ContentReview.id == review_id).first()
    if not review:
        return None

    review.status = request.decision
    review.reviewer_notes = request.reviewer_notes or review.reviewer_notes
    review.reviewer_id = reviewer_id or review.reviewer_id
    review.reviewed_at = datetime.utcnow()

    db.commit()
    db.refresh(review)
    return review

