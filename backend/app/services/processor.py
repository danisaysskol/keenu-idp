import io
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.models.schemas import ImageResult, JobState, JobStatus
from app.services.gemini_service import classify_document, extract_fields
from app.services.output_generator import generate_outputs
from app.utils.logger import get_logger
from app.utils.validators import validate_fields

logger = get_logger(__name__)

SUPPORTED_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _get_mime_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return SUPPORTED_MIME_TYPES.get(suffix, "image/jpeg")


def _validate_image_bytes(image_bytes: bytes) -> bool:
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
        return True
    except (UnidentifiedImageError, Exception):
        return False


async def process_job(
    job_id: str,
    file_data: list[tuple[str, bytes]],  # [(filename, bytes), ...]
    job_store: dict[str, JobState],
) -> None:
    """
    Serial pipeline: classify → extract → validate, one image at a time.
    Sequential processing avoids exhausting the Gemini API quota.
    """
    job = job_store[job_id]
    job.status = JobStatus.processing
    job.total = len(file_data)
    job.images = [ImageResult(filename=name, status="pending") for name, _ in file_data]

    results: list[dict] = []

    for index, (filename, image_bytes) in enumerate(file_data):
        img_result = job.images[index]
        img_result.status = "processing"
        logger.info("[%s] (%d/%d) Processing %s", job_id, index + 1, job.total, filename)

        if not _validate_image_bytes(image_bytes):
            img_result.status = "error"
            img_result.error = "Invalid or corrupted image file"
            logger.warning("[%s] Skipping corrupted image: %s", job_id, filename)
            job.processed += 1
            continue

        mime_type = _get_mime_type(filename)

        try:
            category = await classify_document(image_bytes, mime_type)
            logger.info("[%s] %s → %s", job_id, filename, category)

            fields = await extract_fields(image_bytes, mime_type, category)
            validated = validate_fields(fields, category)

            img_result.category = category
            img_result.fields = validated
            img_result.status = "done"

            # image_bytes and mime_type are kept so output_generator can build the PDF
            results.append({
                "filename": filename,
                "category": category,
                "fields": validated,
                "image_bytes": image_bytes,
                "mime_type": mime_type,
            })

        except Exception as exc:
            logger.error("[%s] Failed processing %s: %s", job_id, filename, exc)
            img_result.status = "error"
            img_result.error = str(exc)

        finally:
            job.processed += 1

    if results:
        try:
            output_files = generate_outputs(job_id, results)
            job.output_files = output_files
            logger.info("[%s] Generated %d output files", job_id, len(output_files))
        except Exception as exc:
            logger.error("[%s] Output generation failed: %s", job_id, exc)
            job.error = f"Output generation failed: {exc}"
            job.status = JobStatus.failed
            return

    job.status = JobStatus.complete
    logger.info("[%s] Done. %d/%d processed.", job_id, job.processed, job.total)
