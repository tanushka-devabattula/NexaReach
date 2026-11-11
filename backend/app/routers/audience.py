"""Audience API (Task 4).

GET    /audience                 list: pagination, search, filters, sorting
GET    /audience/stats           totals by language / city / channel ...
GET    /audience/template.csv    sample file for bulk upload
POST   /audience/bulk            CSV / Excel upload with a per-row report
POST   /audience                 create          (admin, campaign_manager)
GET    /audience/{id}            one member
PATCH  /audience/{id}            update          (admin, campaign_manager)
DELETE /audience/{id}            delete          (admin, campaign_manager)
"""
import math
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.models import AudienceMember, DeviceToken, Message
from app.schemas.audience import (
    AudienceCreate,
    AudiencePage,
    AudienceResponse,
    AudienceUpdate,
    BulkUploadResult,
)
from app.services import audience_service as svc

router = APIRouter(prefix="/audience", tags=["Audience"])

manage = Depends(require_role("admin", "campaign_manager"))

SORTABLE = {
    "id": AudienceMember.id,
    "full_name": AudienceMember.full_name,
    "email": AudienceMember.email,
    "city": AudienceMember.city,
    "occupation": AudienceMember.occupation,
    "preferred_language": AudienceMember.preferred_language,
    "age": AudienceMember.age,
    "created_at": AudienceMember.created_at,
}


def _get_or_404(db: Session, member_id: int) -> AudienceMember:
    member = db.query(AudienceMember).filter(AudienceMember.id == member_id).first()
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audience member not found")
    return member


def _duplicate_error(field: str, other_id: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"Another audience member (ID {other_id}) already has this {field}.",
    )


def _group(db: Session, column):
    rows = (
        db.query(column, func.count(AudienceMember.id))
        .group_by(column)
        .order_by(func.count(AudienceMember.id).desc())
        .all()
    )
    return [{"label": value if value not in (None, "") else "Not set", "count": count} for value, count in rows]


# ------------------------------------------------------------------ reading
@router.get("", response_model=AudiencePage, summary="List audience members")
def list_audience_members(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=200),
    search: Optional[str] = Query(default=None, description="Matches name, email, phone, city, occupation"),
    language: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    occupation: Optional[str] = None,
    gender: Optional[str] = None,
    channel: Optional[str] = None,
    consent: Optional[bool] = None,
    sort_by: str = "id",
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    if sort_by not in SORTABLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot sort by '{sort_by}'. Use one of: {', '.join(SORTABLE)}",
        )

    query = db.query(AudienceMember)
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                AudienceMember.full_name.ilike(term),
                AudienceMember.email.ilike(term),
                AudienceMember.phone.ilike(term),
                AudienceMember.city.ilike(term),
                AudienceMember.occupation.ilike(term),
            )
        )
    for column, value in (
        (AudienceMember.preferred_language, language),
        (AudienceMember.city, city),
        (AudienceMember.state, state),
        (AudienceMember.occupation, occupation),
        (AudienceMember.gender, gender),
        (AudienceMember.preferred_channel, channel),
    ):
        if value and value.strip():
            query = query.filter(func.lower(column) == value.strip().lower())
    if consent is not None:
        query = query.filter(AudienceMember.consent == consent)

    total = query.count()
    sort_column = SORTABLE[sort_by]
    order = sort_column.asc() if sort_dir == "asc" else sort_column.desc()
    items = (
        query.order_by(order, AudienceMember.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, math.ceil(total / page_size)),
    }


@router.get("/stats", summary="Audience totals by language, city, channel ...")
def audience_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(AudienceMember.id)).scalar() or 0
    consented = (
        db.query(func.count(AudienceMember.id)).filter(AudienceMember.consent == True).scalar() or 0  # noqa: E712
    )
    by_language = _group(db, AudienceMember.preferred_language)
    return {
        "total": total,
        "consented": consented,
        "not_consented": total - consented,
        "languages_count": len([row for row in by_language if row["label"] != "Not set"]),
        "by_language": by_language,
        "by_city": _group(db, AudienceMember.city),
        "by_channel": _group(db, AudienceMember.preferred_channel),
        "by_occupation": _group(db, AudienceMember.occupation),
        "by_gender": _group(db, AudienceMember.gender),
    }


@router.get("/template.csv", summary="Download a sample CSV for bulk upload")
def download_template():
    return Response(
        content=svc.template_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="audience_template.csv"'},
    )


# --------------------------------------------------------------- bulk upload
@router.post("/bulk", response_model=BulkUploadResult, dependencies=[manage],
             summary="Bulk upload members from a CSV or Excel file")
async def bulk_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = (file.filename or "").lower()
    raw = await file.read()
    if len(raw) > svc.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail="File is too large (maximum 2 MB).")
    try:
        if filename.endswith(".csv"):
            rows = svc.read_csv(raw)
        elif filename.endswith(".xlsx"):
            rows = svc.read_xlsx(raw)
        else:
            raise svc.UploadProblem("Please upload a .csv or .xlsx file")
    except svc.UploadProblem as problem:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(problem))
    if len(rows) > svc.MAX_UPLOAD_ROWS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Too many rows (maximum {svc.MAX_UPLOAD_ROWS} per file).")

    # who is already in the audience (to catch duplicates, also inside the file itself)
    seen_emails = {}
    seen_phones = {}
    for member_id, email, phone in db.query(
        AudienceMember.id, AudienceMember.email, AudienceMember.phone
    ).all():
        if email:
            seen_emails[email.lower()] = "already in the audience"
        if svc.phone_key(phone):
            seen_phones[svc.phone_key(phone)] = "already in the audience"

    added = 0
    total_rows = 0
    errors = []
    for index, row in enumerate(rows):
        if not row:  # blank line
            continue
        total_rows += 1
        sheet_row = index + 2  # row 1 is the header
        name = row.get("full_name") or None
        try:
            data = {key: value for key, value in row.items() if key in svc.KNOWN_COLUMNS}
            data["consent"] = svc.parse_bool(data.get("consent", ""))
            member_data = AudienceCreate.model_validate(data)
        except ValidationError as err:
            reason = "; ".join(
                f"{'.'.join(str(p) for p in e['loc']) or 'row'}: {e['msg'].removeprefix('Value error, ')}"
                for e in err.errors()
            )
            errors.append({"row": sheet_row, "name": name, "reason": reason})
            continue
        except ValueError as err:
            errors.append({"row": sheet_row, "name": name, "reason": str(err)})
            continue

        email_l = member_data.email.lower() if member_data.email else None
        pkey = svc.phone_key(member_data.phone)
        if email_l and email_l in seen_emails:
            errors.append({"row": sheet_row, "name": name,
                           "reason": f"Duplicate email ({seen_emails[email_l]})"})
            continue
        if pkey and pkey in seen_phones:
            errors.append({"row": sheet_row, "name": name,
                           "reason": f"Duplicate phone ({seen_phones[pkey]})"})
            continue

        db.add(AudienceMember(**member_data.model_dump()))
        added += 1
        if email_l:
            seen_emails[email_l] = f"also in row {sheet_row} of this file"
        if pkey:
            seen_phones[pkey] = f"also in row {sheet_row} of this file"

    db.commit()
    return {"total_rows": total_rows, "added": added, "failed": len(errors), "errors": errors}


# --------------------------------------------------------------------- CRUD
@router.post("", response_model=AudienceResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[manage], summary="Add an audience member")
def create_audience_member(data: AudienceCreate, db: Session = Depends(get_db)):
    duplicate = svc.find_duplicate(db, data.email, data.phone)
    if duplicate:
        raise _duplicate_error(*duplicate)
    member = AudienceMember(**data.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.get("/{member_id}", response_model=AudienceResponse, summary="Get one audience member")
def get_audience_member(member_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, member_id)


@router.patch("/{member_id}", response_model=AudienceResponse, dependencies=[manage],
              summary="Update an audience member")
def update_audience_member(member_id: int, data: AudienceUpdate, db: Session = Depends(get_db)):
    member = _get_or_404(db, member_id)
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    for required in ("full_name", "preferred_language", "consent"):
        if required in changes and changes[required] is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{required} cannot be empty")

    new_email = changes.get("email", member.email)
    new_phone = changes.get("phone", member.phone)
    if not new_email and not new_phone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="A member needs at least an email or a phone number")
    if "email" in changes or "phone" in changes:
        duplicate = svc.find_duplicate(db, new_email, new_phone, exclude_id=member.id)
        if duplicate:
            raise _duplicate_error(*duplicate)

    for field, value in changes.items():
        setattr(member, field, value)
    db.commit()
    db.refresh(member)
    return member


@router.delete("/{member_id}", dependencies=[manage], summary="Delete an audience member")
def delete_audience_member(member_id: int, db: Session = Depends(get_db)):
    member = _get_or_404(db, member_id)
    sent = db.query(func.count(Message.id)).filter(Message.audience_member_id == member.id).scalar() or 0
    if sent:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(f"This person has {sent} message(s) in the delivery history, so they cannot be deleted. "
                    "Turn their consent off instead."),
        )
    db.query(DeviceToken).filter(DeviceToken.audience_member_id == member.id).delete()
    db.delete(member)
    db.commit()
    return {"detail": "Audience member deleted"}
