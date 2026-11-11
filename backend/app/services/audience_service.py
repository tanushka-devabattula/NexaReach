"""Audience helpers: clean-up of values, duplicate detection, CSV / Excel reading.

Simple rules used everywhere (form, API, bulk upload):
* a phone number is cleaned to digits (a leading + is kept) and must have 7-15 digits
* "the same person" = same email (ignoring upper/lower case) OR same phone
  (compared by its last 10 digits, so +91 98765 43210 equals 9876543210)
"""
import csv
import io
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.models import AudienceMember

LANGUAGES = [
    "English", "Hindi", "Telugu", "Kannada", "Tamil", "Marathi",
    "Bengali", "Gujarati", "Malayalam", "Punjabi", "Urdu",
]
GENDERS = ["Male", "Female", "Other"]
CHANNELS = ["WHATSAPP", "SMS", "EMAIL", "PUSH"]

MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_UPLOAD_ROWS = 5000

TEMPLATE_HEADERS = [
    "full_name", "email", "phone", "age", "gender", "city", "state",
    "occupation", "department", "preferred_language", "preferred_channel", "consent",
]
TEMPLATE_ROWS = [
    ["Ravi Kumar", "ravi@example.com", "9876543210", "34", "Male", "Hyderabad", "Telangana",
     "Teacher", "Education", "Telugu", "WHATSAPP", "yes"],
    ["Meena Iyer", "meena@example.com", "9123456780", "41", "Female", "Chennai", "Tamil Nadu",
     "Farmer", "", "Tamil", "SMS", "yes"],
]

# Other column names people commonly use -> the name we use.
HEADER_ALIASES = {
    "name": "full_name", "fullname": "full_name", "full name": "full_name",
    "mobile": "phone", "phone_number": "phone", "phone number": "phone", "contact": "phone",
    "e-mail": "email", "email_address": "email", "email address": "email",
    "language": "preferred_language", "preferred language": "preferred_language",
    "channel": "preferred_channel", "preferred channel": "preferred_channel",
    "dept": "department", "organization": "department", "organisation": "department",
    "job": "occupation", "profession": "occupation",
    "opt_in": "consent", "opted_in": "consent",
}
KNOWN_COLUMNS = set(TEMPLATE_HEADERS)


# ------------------------------------------------------------------ cleaning
def canonical_phone(raw: Any) -> Optional[str]:
    """'+91 98765-43210' -> '+919876543210'. Blank -> None. Bad -> ValueError."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if not 7 <= len(digits) <= 15:
        raise ValueError("Phone number must have 7 to 15 digits")
    return ("+" if text.startswith("+") else "") + digits


def phone_key(raw: Any) -> Optional[str]:
    """Used only to compare phones (never raises, works on old messy data)."""
    digits = re.sub(r"\D", "", str(raw or ""))
    return digits[-10:] if digits else None


def pick_from(value: Any, options: List[str], label: str, upper: bool = False) -> Optional[str]:
    """Match ignoring case and return the official spelling. Blank -> None."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for option in options:
        if option.lower() == text.lower():
            return option
    raise ValueError(f"Unsupported {label} '{text}'. Choose one of: {', '.join(options)}")


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"true", "yes", "y", "1", "t"}:
        return True
    if text in {"false", "no", "n", "0", "f", ""}:
        return False
    raise ValueError("consent must be yes or no")


# ---------------------------------------------------------------- duplicates
def find_duplicate(db: Session, email: Optional[str], phone: Optional[str],
                   exclude_id: Optional[int] = None) -> Optional[Tuple[str, int]]:
    """Returns ('email' or 'phone', id_of_existing_member) or None."""
    email_l = email.lower() if email else None
    pkey = phone_key(phone)
    if not email_l and not pkey:
        return None
    for member_id, e, p in db.query(AudienceMember.id, AudienceMember.email, AudienceMember.phone).all():
        if exclude_id is not None and member_id == exclude_id:
            continue
        if email_l and e and e.lower() == email_l:
            return "email", member_id
        if pkey and p and phone_key(p) == pkey:
            return "phone", member_id
    return None


# ------------------------------------------------------------- file reading
class UploadProblem(Exception):
    """The whole file cannot be used (wrong type, unreadable, missing column...)."""


def _normalize_header(name: Any) -> str:
    text = str(name or "").strip().lower().lstrip("\ufeff")
    text = HEADER_ALIASES.get(text, text)
    underscored = text.replace(" ", "_")
    return underscored if underscored in KNOWN_COLUMNS else text


def _check_columns(headers: List[str]) -> None:
    if "full_name" not in headers:
        raise UploadProblem("Missing required column: full_name (see the sample template)")
    if "email" not in headers and "phone" not in headers:
        raise UploadProblem("The file needs an email column or a phone column (see the sample template)")


def read_csv(raw: bytes) -> List[Dict[str, str]]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise UploadProblem("The file must be UTF-8 text. In Excel use: Save As -> CSV UTF-8.")
    reader = csv.reader(io.StringIO(text))
    try:
        header_row = next(reader)
    except StopIteration:
        raise UploadProblem("The file is empty")
    headers = [_normalize_header(h) for h in header_row]
    _check_columns(headers)
    rows = []
    for values in reader:
        if not any(str(v).strip() for v in values):
            rows.append({})  # keep row numbers right; blank lines are ignored later
            continue
        rows.append({headers[i]: (values[i].strip() if i < len(values) else "") for i in range(len(headers))})
    return rows


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def read_xlsx(raw: bytes) -> List[Dict[str, str]]:
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise UploadProblem("Excel upload needs the 'openpyxl' package (pip install openpyxl). Or upload a CSV.")
    try:
        workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    except Exception:
        raise UploadProblem("Could not read this Excel file. Is it a valid .xlsx?")
    sheet = workbook.worksheets[0]
    iterator = sheet.iter_rows(values_only=True)
    try:
        header_row = next(iterator)
    except StopIteration:
        raise UploadProblem("The file is empty")
    headers = [_normalize_header(h) for h in header_row]
    _check_columns(headers)
    rows = []
    for values in iterator:
        cells = [_cell_text(v) for v in values]
        if not any(cells):
            rows.append({})
            continue
        rows.append({headers[i]: (cells[i] if i < len(cells) else "") for i in range(len(headers))})
    workbook.close()
    return rows


def template_csv() -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(TEMPLATE_HEADERS)
    writer.writerows(TEMPLATE_ROWS)
    return buffer.getvalue()
