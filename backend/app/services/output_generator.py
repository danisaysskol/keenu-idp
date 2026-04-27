import csv
import io
import json
from datetime import datetime
from pathlib import Path

from PIL import Image

from app.config import settings
from app.models.schemas import OutputFile
from app.services.schema_merger import merge_schemas
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _build_category_pdf(image_entries: list[tuple[str, bytes, str]], pdf_path: Path) -> bool:
    """
    Render all images for a category into a single multi-page PDF.
    Each image becomes one page. Returns True if the file was written.
    """
    pil_images: list[Image.Image] = []

    for filename, img_bytes, mime_type in image_entries:
        try:
            img = Image.open(io.BytesIO(img_bytes))
            # PDF writer requires RGB; drop alpha/palette modes
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            pil_images.append(img)
        except Exception as exc:
            logger.warning("Skipping %s from PDF: %s", filename, exc)

    if not pil_images:
        return False

    first, rest = pil_images[0], pil_images[1:]
    first.save(
        pdf_path,
        format="PDF",
        save_all=True,
        append_images=rest,
        resolution=100.0,
    )
    return True


def generate_outputs(job_id: str, results: list[dict]) -> list[OutputFile]:
    """
    Group results by category, write CSV + JSON + PDF (one set per category).
    Each result dict must have: filename, category, fields, image_bytes, mime_type.
    """
    job_dir = Path(settings.output_dir) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Group field records and raw images by category, preserving insertion order
    field_records: dict[str, list[dict]] = {}
    image_entries: dict[str, list[tuple[str, bytes, str]]] = {}

    for result in results:
        category = result.get("category") or "other"
        filename = result.get("filename", "")
        fields = dict(result.get("fields") or {})
        fields["_source_file"] = filename
        img_bytes = result.get("image_bytes", b"")
        mime_type = result.get("mime_type", "image/jpeg")

        field_records.setdefault(category, []).append(fields)
        image_entries.setdefault(category, []).append((filename, img_bytes, mime_type))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_files: list[OutputFile] = []

    for category in field_records:
        records = field_records[category]
        images = image_entries.get(category, [])
        merged = merge_schemas(records)
        if not merged:
            continue

        columns = list(merged[0].keys())
        record_count = len(merged)

        # ── JSON ──────────────────────────────────────────────────────────────
        json_filename = f"{timestamp}_{category}.json"
        json_path = job_dir / json_filename
        json_content = json.dumps(merged, indent=2, default=str)
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json_content)
        logger.info("Wrote JSON: %s (%d records)", json_filename, record_count)
        output_files.append(OutputFile(
            filename=json_filename,
            category=category,
            format="json",
            record_count=record_count,
            path=str(json_path),
            content=json_content,
        ))

        # ── CSV ───────────────────────────────────────────────────────────────
        csv_filename = f"{timestamp}_{category}.csv"
        csv_path = job_dir / csv_filename
        csv_buf = io.StringIO()
        writer = csv.DictWriter(csv_buf, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in merged:
            writer.writerow({k: ("" if v is None else v) for k, v in row.items()})
        csv_content = csv_buf.getvalue()
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            f.write(csv_content)
        logger.info("Wrote CSV: %s (%d records)", csv_filename, record_count)
        output_files.append(OutputFile(
            filename=csv_filename,
            category=category,
            format="csv",
            record_count=record_count,
            path=str(csv_path),
            content=csv_content,
        ))

        # ── PDF ───────────────────────────────────────────────────────────────
        pdf_filename = f"{timestamp}_{category}.pdf"
        pdf_path = job_dir / pdf_filename
        if _build_category_pdf(images, pdf_path):
            logger.info("Wrote PDF: %s (%d pages)", pdf_filename, len(images))
            output_files.append(OutputFile(
                filename=pdf_filename,
                category=category,
                format="pdf",
                record_count=len(images),  # page count
                path=str(pdf_path),
            ))
        else:
            logger.warning("PDF skipped for category '%s' (no valid images)", category)

    return output_files


def read_output_file(path: str, fmt: str) -> tuple[list[dict], list[str]]:
    """Return (records, columns) from a saved JSON or CSV file."""
    file_path = Path(path)
    if not file_path.exists():
        return [], []

    if fmt == "json":
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        columns = list(data[0].keys()) if data else []
        return data, columns

    # CSV
    rows = []
    with open(file_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        for row in reader:
            rows.append({k: (None if v == "" else v) for k, v in row.items()})
    return rows, list(columns)
