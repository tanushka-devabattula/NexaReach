
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Campaign, Template
from app.schemas.template import TemplateCreate, TemplateResponse, TemplateUpdate

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


@router.patch("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: int,
    data: TemplateUpdate,
    db: Session = Depends(get_db),
):
    template = db.query(Template).filter(Template.id == template_id).first()
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found.",
        )

    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update.",
        )

    if "name" in changes:
        if changes["name"] is None or not changes["name"].strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template name cannot be empty.",
            )
        duplicate = (
            db.query(Template)
            .filter(Template.name == changes["name"], Template.id != template_id)
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A template with this name already exists.",
            )
        changes["name"] = changes["name"].strip()

    if "body" in changes and (
        changes["body"] is None or not changes["body"].strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template body cannot be empty.",
        )

    for field, value in changes.items():
        setattr(template, field, value)

    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
):
    template = db.query(Template).filter(Template.id == template_id).first()
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found.",
        )

    linked_campaign = (
        db.query(Campaign.id)
        .filter(Campaign.template_id == template_id)
        .first()
    )
    if linked_campaign:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This template is linked to a campaign. Unlink the campaign before deleting it.",
        )

    db.delete(template)
    db.commit()
    return {"message": "Template deleted successfully.", "template_id": template_id}
