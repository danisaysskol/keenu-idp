import re
from datetime import datetime
from app.utils.logger import get_logger

logger = get_logger(__name__)

CNIC_PATTERN = re.compile(r"^\d{5}-\d{7}-\d$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_cnic(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = str(value).strip()
    if CNIC_PATTERN.match(cleaned):
        return cleaned
    logger.warning("Invalid CNIC format: %s", value)
    return None


def validate_date(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = str(value).strip()
    try:
        datetime.strptime(cleaned, "%Y-%m-%d")
        return cleaned
    except ValueError:
        logger.warning("Invalid date format (expected YYYY-MM-DD): %s", value)
        return None


def validate_amount(value: str | float | int | None) -> float | None:
    if value is None:
        return None
    try:
        cleaned = re.sub(r"[^\d.]", "", str(value))
        if not cleaned:
            return None
        result = float(cleaned)
        return result
    except (ValueError, TypeError):
        logger.warning("Invalid amount: %s", value)
        return None


def validate_email(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = str(value).strip()
    if EMAIL_PATTERN.match(cleaned):
        return cleaned
    logger.warning("Invalid email: %s", value)
    return None


def validate_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", str(value))
    if 7 <= len(digits) <= 15:
        return str(value).strip()
    logger.warning("Invalid phone (digit count %d): %s", len(digits), value)
    return None


_CATEGORY_VALIDATORS: dict[str, dict[str, callable]] = {
    "cnic": {
        "cnic_number": validate_cnic,
        "date_of_birth": validate_date,
        "issue_date": validate_date,
        "expiry_date": validate_date,
    },
    "driving_licence": {
        "dob": validate_date,
        "issue_date": validate_date,
        "expiry_date": validate_date,
    },
    "invoices": {
        "date": validate_date,
        "total_amount": validate_amount,
        "tax": validate_amount,
    },
    "receipt": {
        "date": validate_date,
        "total_amount": validate_amount,
        "tax": validate_amount,
    },
    "resumes": {
        "email": validate_email,
        "phone": validate_phone,
    },
    "forms": {},
    "other": {},
}


def validate_fields(fields: dict, category: str) -> dict:
    if not fields:
        return {}
    validators = _CATEGORY_VALIDATORS.get(category, {})
    result = dict(fields)
    for field, validator in validators.items():
        if field in result:
            result[field] = validator(result[field])
    return result
