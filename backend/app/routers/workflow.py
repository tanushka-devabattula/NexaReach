from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ai import AIGenerateRequest
from app.schemas.analysis import ToneAnalysisRequest
from app.schemas.personalization import SegmentVariantRequest
from app.schemas.review import ComplianceCheckRequest, ReviewSubmitRequest
from app.schemas.translation import BatchTranslationRequest
from app.schemas.workflow import (
    WorkflowExecutionResponse,
    WorkflowRunRequest,
)
from app.services.ai_service import generate_content
from app.services.analysis_service import analyze_tone_and_readability
from app.services.compliance_service import check_compliance, submit_for_review
from app.services.personalization_service import generate_segment_variants
from app.services.translation_service import batch_translate

router = APIRouter(prefix="/workflow", tags=["Campaign Content Workflow"])


@router.post(
    "/run",
    response_model=WorkflowExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Run integrated Generate -> Translate -> Personalize -> Tone -> Review pipeline",
)
def run_integrated_campaign_workflow(
    request: WorkflowRunRequest,
    db: Session = Depends(get_db),
):
    """
    Executes the end-to-end Milestone 2 workflow:
    1. Generate: AI generation with channel and tone adaptation (offline fallback if no key).
    2. Translate: Batch translation into selected Indian languages (with Urdu RTL bidi isolation).
    3. Personalize: Cohort variant generation if segment_id is specified.
    4. Tone & Readability: Automated Flesch score, clarity metrics, and tone classification.
    5. Compliance: Rule check for channel limits, prohibited words, and mandatory opt-outs.
    6. Review: Automatically registers a ContentReview record if auto_submit_for_review is True.
    """
    # Step 1: Content Generation
    gen_req = AIGenerateRequest(
        prompt=request.prompt,
        channel=request.channel,
        tone=request.tone,
        campaign_id=request.campaign_id,
        user_id=request.user_id,
        variations=2,
    )
    generated = generate_content(gen_req, db=db)

    # Step 2: Multilingual Translation
    trans_req = BatchTranslationRequest(
        text=generated.content,
        target_languages=request.target_languages,
        source_language="English",
    )
    translations = batch_translate(trans_req, db=db)

    # Step 3: Personalization & Segment Variants (if segment_id provided)
    personalization_res = None
    if request.segment_id:
        try:
            seg_req = SegmentVariantRequest(
                base_text=generated.content,
                segment_id=request.segment_id,
                sample_limit=5,
            )
            personalization_res = generate_segment_variants(seg_req, db=db)
        except Exception:
            personalization_res = None

    # Step 4: Tone and Readability Analysis
    analysis_req = ToneAnalysisRequest(
        content=generated.content,
        channel=request.channel,
        target_tone=request.tone,
    )
    analysis = analyze_tone_and_readability(analysis_req)

    # Step 5: Compliance Check
    comp_req = ComplianceCheckRequest(
        content=generated.content,
        channel=request.channel,
        language="English",
    )
    compliance = check_compliance(comp_req)

    # Step 6: Review Registration
    review_res = None
    if request.auto_submit_for_review:
        sub_req = ReviewSubmitRequest(
            campaign_id=request.campaign_id,
            content=generated.content,
            channel=request.channel,
            language="English",
            reviewer_notes=request.reviewer_notes or "Auto-generated from workflow pipeline.",
        )
        review_model = submit_for_review(sub_req, db=db, user_id=request.user_id)
        # Store readability metrics on the review model as well
        try:
            review_model.readability_metrics = analysis.model_dump()
            db.commit()
            db.refresh(review_model)
        except Exception:
            db.rollback()

        review_res = review_model

    return WorkflowExecutionResponse(
        status="completed",
        generated_content=generated,
        translations=translations,
        personalization=personalization_res,
        analysis=analysis,
        compliance=compliance,
        review=review_res,
    )

