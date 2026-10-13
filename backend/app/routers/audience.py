
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import AudienceMember
from app.schemas.audience import AudienceCreate, AudienceResponse

router = APIRouter(prefix="/audience", tags=["Audience"])


@router.post(
    "",
    response_model=AudienceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_audience_member(
    audience_data: AudienceCreate,
    db: Session = Depends(get_db),
):
    member = AudienceMember(
        full_name=audience_data.full_name,
        email=audience_data.email,
        phone=audience_data.phone,
        preferred_language=audience_data.preferred_language,
    )

    db.add(member)
    db.commit()
    db.refresh(member)

    return member


@router.get("", response_model=list[AudienceResponse])
def list_audience_members(
    db: Session = Depends(get_db),
):
    return (
        db.query(AudienceMember)
        .order_by(AudienceMember.id.desc())
        .all()
    )
