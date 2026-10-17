
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Segment
from app.schemas.segment import SegmentCreate, SegmentResponse

router = APIRouter(prefix="/segments", tags=["Segments"])


@router.post(
    "",
    response_model=SegmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_segment(
    data: SegmentCreate,
    db: Session = Depends(get_db),
):
    existing = db.query(Segment).filter(Segment.name == data.name).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A segment with this name already exists.",
        )

    segment = Segment(
        name=data.name,
        description=data.description,
        criteria=data.criteria,
    )

    db.add(segment)
    db.commit()
    db.refresh(segment)
    return segment


@router.get("", response_model=list[SegmentResponse])
def list_segments(db: Session = Depends(get_db)):
    return db.query(Segment).order_by(Segment.id.desc()).all()


@router.get("/{segment_id}", response_model=SegmentResponse)
def get_segment(
    segment_id: int,
    db: Session = Depends(get_db),
):
    segment = db.query(Segment).filter(Segment.id == segment_id).first()

    if segment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segment not found.",
        )

    return segment
