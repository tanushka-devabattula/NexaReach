"""One-click workflow used by the AI Studio "Workflow" tab.

Generate -> Translate -> Personalize (optional) -> Tone/Readability -> Compliance -> Review.
Every step is real. If a step cannot work (for example no API key) the endpoint
returns a clear error instead of fake output.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analysis import ToneAnalysisRequest
from app.schemas.personalization import SegmentVariantRequest
from app.schemas.review import ComplianceCheckRequest, ReviewResponse, ReviewSubmitRequest
from app.schemas.translation import BatchTranslationRequest
from app.services.ai_service import AIProviderError, generate_content
from app.services.analysis_service import analyze_tone_and_readability
from app.services.compliance_service import check_compliance, submit_for_review
from app.services.personalization_service import NotFoundError, generate_segment_variants
from app.services.translation_service import TranslationProviderError, batch_translate

router = APIRouter(prefix="/workflow", tags=["Workflow"])


class WorkflowRunPayload(BaseModel):
    prompt: str = Field(default="", description="Topic / instruction for the AI")
    channel: str = "SMS"
    tone: str = "Informative"
    category: str = "Public Health"
    target_languages: List[str] = Field(default_factory=list)
    segment_id: Optional[int] = None
    campaign_id: Optional[int] = None
    auto_submit_for_review: bool = True


@router.post("/run", summary="Run the full content workflow")
def run_workflow(payload: WorkflowRunPayload, db: Session = Depends(get_db)):
    try:
        generated = generate_content(
            prompt=payload.prompt,
            category=payload.category,
            tone=payload.tone,
            channel=payload.channel,
            db=db,
        )
        text = generated["content"]

        if payload.target_languages:
            translations = batch_translate(
                BatchTranslationRequest(text=text, target_languages=payload.target_languages), db=db
            )
            if not translations.results:
                reasons = list(dict.fromkeys(e.detail for e in translations.errors))
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=" | ".join(reasons) or "No translations were produced.",
                )
            translations_out = translations.model_dump(mode="json")
        else:
            translations_out = {"source_text": text, "source_language": "English", "results": [], "errors": []}

        personalization_out = None
        if payload.segment_id is not None:
            personalization_out = generate_segment_variants(
                SegmentVariantRequest(base_text=text, segment_id=payload.segment_id, sample_limit=5), db
            )

        analysis = analyze_tone_and_readability(
            ToneAnalysisRequest(content=text, channel=payload.channel, target_tone=payload.tone)
        )
        compliance = check_compliance(ComplianceCheckRequest(content=text, channel=payload.channel))

        review_out = None
        translation_reviews = []

        if payload.auto_submit_for_review:
            review = submit_for_review(
                ReviewSubmitRequest(
                    content=text,
                    channel=payload.channel,
                    campaign_id=payload.campaign_id,
                ),
                db=db,
            )
            review_out = ReviewResponse.model_validate(review).model_dump(mode="json")

            # Each successful translation gets its own linked campaign draft
            # and compliance review when a campaign has been selected.
            if payload.campaign_id is not None:
                for translated in translations_out.get("results", []):
                    translated_review = submit_for_review(
                        ReviewSubmitRequest(
                            content=translated["translated_text"],
                            channel=payload.channel,
                            language=translated["language"],
                            campaign_id=payload.campaign_id,
                        ),
                        db=db,
                    )
                    review_data = ReviewResponse.model_validate(
                        translated_review
                    ).model_dump(mode="json")
                    translation_reviews.append({
                        "language": translated["language"],
                        **review_data,
                    })

    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except NotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except (AIProviderError, TranslationProviderError) as err:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(err))

    return {
        "status": "success",
        "generated_content": generated,
        "translations": translations_out,
        "personalization": personalization_out,
        "analysis": analysis.model_dump(mode="json"),
        "compliance": compliance.model_dump(mode="json"),
        "review": review_out,
        "translation_reviews": translation_reviews,
    }