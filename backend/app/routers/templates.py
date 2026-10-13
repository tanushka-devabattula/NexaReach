
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Template
from app.schemas.template import TemplateCreate, TemplateResponse

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.post(
    "",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_template(
    template_data: TemplateCreate,
    db: Session = Depends(get_db),
):
    template = Template(
        name=template_data.name,
        channel=template_data.channel,
        language=template_data.language,
        subject=template_data.subject,
        body=template_data.body,
    )

    db.add(template)
    db.commit()
    db.refresh(template)

    return template


@router.get("", response_model=list[TemplateResponse])
def list_templates(db: Session = Depends(get_db)):
    return (
        db.query(Template)
        .order_by(Template.id.desc())
        .all()
    )


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
):
    template = (
        db.query(Template)
        .filter(Template.id == template_id)
        .first()
    )

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    return template
