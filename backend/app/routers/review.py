from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import ContentReview
from app.schemas.review import (
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    ReviewDecisionRequest,
    ReviewResponse,
    ReviewSubmitRequest,
)
from app.services.compliance_service import (
    check_compliance,
    decide_review,
    submit_for_review,
)

router = APIRouter(prefix="/review", tags=["Compliance & Quality Review"])


@router.post(
    "/compliance-check",
    response_model=ComplianceCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Screen message against compliance rules",
)
def run_compliance_check(request: ComplianceCheckRequest):
    """
    Evaluates message against SMS length limits, prohibited misleading words,
    placeholder syntax, and mandatory helpline / opt-out notices.
    """
    return check_compliance(request)


@router.post(
    "/submit",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit message for quality and regulatory review",
)
def submit_message_review(
    request: ReviewSubmitRequest,
    db: Session = Depends(get_db),
):
    """
    Runs automated compliance checks and registers a ContentReview entry in
    status='pending_review' with audit results saved to SQLite.
    """
    return submit_for_review(request, db=db)


@router.get(
    "/list",
    response_model=list[ReviewResponse],
    summary="List content reviews",
)
def list_reviews(
    status_filter: str | None = Query(default=None, description="Optional status filter ('pending_review', 'approved', etc.)"),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Returns list of content reviews stored in SQLite.
    """
    query = db.query(ContentReview)
    if status_filter:
        query = query.filter(ContentReview.status == status_filter)
    return query.order_by(ContentReview.id.desc()).limit(limit).all()


@router.get(
    "/{review_id}",
    response_model=ReviewResponse,
    summary="Get content review details by ID",
)
def get_review_details(
    review_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieves a specific review record by ID.
    """
    review = db.query(ContentReview).filter(ContentReview.id == review_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ContentReview #{review_id} not found.",
        )
    return review


@router.post(
    "/{review_id}/decision",
    response_model=ReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve, reject, or request revisions on a review",
)
def apply_review_decision(
    review_id: int,
    request: ReviewDecisionRequest,
    db: Session = Depends(get_db),
):
    """
    Applies review decision ('approved', 'rejected', or 'changes_requested')
    and records reviewer feedback and timestamp in the database.
    """
    updated = decide_review(review_id, request, db=db)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ContentReview #{review_id} not found.",
        )
    return updated

