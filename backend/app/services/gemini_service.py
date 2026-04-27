import asyncio
import io
import json
import re
from typing import Any

from PIL import Image
import google.genai as genai
from google.genai import types

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

CATEGORIES = ["cnic", "driving_licence", "forms", "invoices", "receipt", "resumes", "other"]

_MAX_IMAGE_PX = 2000
_MAX_IMAGE_BYTES = 4 * 1024 * 1024  # 4MB threshold before resize

_CATEGORY_HINTS: dict[str, str] = {
    "cnic": "name, cnic_number (format: XXXXX-XXXXXXX-X), date_of_birth, gender, issue_date, expiry_date",
    "driving_licence": "name, licence_number, dob, issue_date, expiry_date, address, blood_group",
    "forms": "extract all visible key-value pairs from the form fields",
    "invoices": "vendor_name, date, invoice_number, items (array), subtotal, tax, total_amount, address",
    "receipt": "vendor_name, date, items (array), subtotal, tax, total_amount, payment_method, address",
    "resumes": "name, email, phone, address, skills (array), education (array), experience (array), summary",
    "other": "extract any visible structured information as key-value pairs",
}

_CLASSIFICATION_PROMPT = f"""You are a document classifier. Look at this image carefully and classify the document.

Classify into ONE of these exact category names:
- cnic           → Pakistani national ID card (CNIC / NIC / identity card)
- driving_licence → driving license / licence document
- forms           → printed or handwritten form with fields to fill
- invoices        → business invoice or bill issued to a customer
- receipt         → purchase receipt or payment receipt (e.g. shop, ATM, POS)
- resumes         → CV or resume showing work experience, education, skills
- other           → anything that does not match the above

Respond with ONLY this JSON object and nothing else:
{{"category": "<one of the category names above>"}}"""

_EXTRACTION_PROMPT_TEMPLATE = """Extract all visible text and structured information from this {category} document image.

Typical fields for this document type: {hints}

Rules:
- Return ONLY a valid JSON object, no markdown, no extra text
- Include ALL visible fields you can read, not just the typical ones listed above
- Normalize dates to YYYY-MM-DD format
- Normalize numbers to clean numeric format (remove currency symbols, commas)
- If a field is unclear or not present, use null
- Use snake_case for all field names
- For list fields (items, skills, etc.), use JSON arrays

Respond with ONLY the JSON object."""


def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.google_api_key)


def _get_generation_config() -> types.GenerateContentConfig:
    # Do NOT pass ThinkingConfig — flash-lite does not support it and the
    # API raises a 400 error that gets silently swallowed, causing all
    # classifications to fall back to "other".
    return types.GenerateContentConfig(
        temperature=0.1,
        response_mime_type="application/json",
    )


def _strip_markdown_json(text: str) -> str:
    """Remove markdown code fences that Gemini sometimes wraps around JSON."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _resize_image_if_needed(image_bytes: bytes, mime_type: str) -> tuple[bytes, str]:
    """Resize image if > _MAX_IMAGE_BYTES to avoid Gemini payload limits."""
    if len(image_bytes) <= _MAX_IMAGE_BYTES:
        return image_bytes, mime_type
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.thumbnail((_MAX_IMAGE_PX, _MAX_IMAGE_PX), Image.LANCZOS)
        buf = io.BytesIO()
        rgb = img.convert("RGB")
        rgb.save(buf, format="JPEG", quality=85)
        resized = buf.getvalue()
        logger.info(
            "Resized image from %.1fMB to %.1fMB",
            len(image_bytes) / 1e6,
            len(resized) / 1e6,
        )
        return resized, "image/jpeg"
    except Exception as exc:
        logger.warning("Could not resize image: %s", exc)
        return image_bytes, mime_type


def _build_image_part(image_bytes: bytes, mime_type: str) -> types.Part:
    # Pass raw bytes to Blob.data — the SDK handles base64 encoding internally.
    # Passing a base64 string here would cause double-encoding and corrupt the image.
    return types.Part(
        inline_data=types.Blob(mime_type=mime_type, data=image_bytes)
    )


async def _call_gemini_with_retry(
    client: genai.Client,
    contents: list,
    config: types.GenerateContentConfig,
    max_retries: int = 3,
) -> str:
    """Call Gemini with exponential backoff on rate-limit (429) errors."""
    delay = 1.0
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=settings.gemini_model,
                contents=contents,
                config=config,
            )
            return response.text or ""
        except Exception as exc:
            last_exc = exc
            err_str = str(exc)
            is_retryable = (
                "429" in err_str
                or "503" in err_str
                or "quota" in err_str.lower()
                or "rate" in err_str.lower()
                or "unavailable" in err_str.lower()
                or "high demand" in err_str.lower()
            )
            if is_retryable and attempt < max_retries - 1:
                logger.warning("Rate limit hit, retrying in %.1fs (attempt %d)", delay, attempt + 1)
                await asyncio.sleep(delay)
                delay *= 2
            else:
                # Re-raise so callers can log the full exception and file name
                raise
    raise last_exc  # unreachable but satisfies type checker


async def classify_document(image_bytes: bytes, mime_type: str) -> str:
    """Classify a document image into one of the predefined categories."""
    image_bytes, mime_type = _resize_image_if_needed(image_bytes, mime_type)
    client = _get_client()
    config = _get_generation_config()

    contents = [
        types.Content(
            role="user",
            parts=[
                _build_image_part(image_bytes, mime_type),
                types.Part(text=_CLASSIFICATION_PROMPT),
            ],
        )
    ]

    raw = ""
    try:
        raw = await _call_gemini_with_retry(client, contents, config)
        logger.debug("Classification raw response: %.300s", raw)
        cleaned = _strip_markdown_json(raw)
        parsed = json.loads(cleaned)
        category = str(parsed.get("category", "other")).lower().strip()
        if category not in CATEGORIES:
            logger.warning("Gemini returned unknown category '%s', using 'other'", category)
            return "other"
        logger.info("Classified as: %s", category)
        return category
    except json.JSONDecodeError as exc:
        logger.error(
            "Classification JSON parse failed: %s | raw response was: %.300s", exc, raw
        )
        return "other"
    except Exception as exc:
        logger.error(
            "Classification API call failed (model=%s): %s",
            settings.gemini_model,
            exc,
        )
        return "other"


async def extract_fields(image_bytes: bytes, mime_type: str, category: str) -> dict[str, Any]:
    """Extract structured fields from a document image."""
    image_bytes, mime_type = _resize_image_if_needed(image_bytes, mime_type)
    client = _get_client()
    config = _get_generation_config()

    hints = _CATEGORY_HINTS.get(category, "any visible structured information")
    prompt = _EXTRACTION_PROMPT_TEMPLATE.format(category=category, hints=hints)

    contents = [
        types.Content(
            role="user",
            parts=[
                _build_image_part(image_bytes, mime_type),
                types.Part(text=prompt),
            ],
        )
    ]

    raw = ""
    try:
        raw = await _call_gemini_with_retry(client, contents, config)
        logger.debug("Extraction raw response (%.100s...)", raw)
        if not raw.strip():
            logger.warning("Empty extraction response for category '%s'", category)
            return {}
        cleaned = _strip_markdown_json(raw)
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            logger.warning("Extraction returned non-dict type %s", type(parsed))
            return {}
        return parsed
    except json.JSONDecodeError as exc:
        logger.error(
            "Extraction JSON parse failed for '%s': %s | raw: %.300s", category, exc, raw
        )
        return {}
    except Exception as exc:
        logger.error(
            "Extraction API call failed for '%s' (model=%s): %s",
            category,
            settings.gemini_model,
            exc,
        )
        return {}
