import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse

from app.config import settings
from app.models.schemas import (
    FileContentResponse,
    HealthResponse,
    JobState,
)
from app.services.processor import process_job_stream, SUPPORTED_MIME_TYPES
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api")

_MAX_FILES = 10
_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    configured = bool(settings.google_api_key)
    return HealthResponse(
        status="ok" if configured else "degraded",
        model=settings.gemini_model,
        api_key_configured=configured,
    )


@router.post("/jobs")
async def create_job(files: list[UploadFile] = File(...)) -> StreamingResponse:
    """
    Process documents and stream NDJSON progress updates.
    Each line is a complete JobState JSON so the client can render live progress.
    Final line has status=complete and embedded output file content.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    if len(files) > _MAX_FILES:
        raise HTTPException(
            status_code=400, detail=f"Too many files. Maximum is {_MAX_FILES}."
        )

    file_data: list[tuple[str, bytes]] = []
    for upload in files:
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in SUPPORTED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{suffix}' for '{upload.filename}'. "
                       f"Accepted: {', '.join(SUPPORTED_MIME_TYPES)}",
            )
        content = await upload.read()
        if len(content) > _MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File '{upload.filename}' exceeds 10 MB limit.",
            )
        file_data.append((upload.filename or f"file_{len(file_data)}", content))

    job_id = str(uuid.uuid4())
    job = JobState(job_id=job_id, total=len(file_data))
    logger.info("Starting job %s with %d files", job_id, len(file_data))

    return StreamingResponse(
        process_job_stream(job, file_data),
        media_type="application/x-ndjson",
        headers={"X-Job-Id": job_id},
    )


@router.get("/jobs/{job_id}/download/{filename}")
async def download_file(job_id: str, filename: str) -> FileResponse:
    output_dir = Path(settings.output_dir) / job_id
    file_path = output_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found or session expired")

    _mime = {"csv": "text/csv", "json": "application/json", "pdf": "application/pdf"}
    suffix = file_path.suffix.lstrip(".")
    media_type = _mime.get(suffix, "application/octet-stream")
    return FileResponse(path=str(file_path), filename=filename, media_type=media_type)


@router.get("/jobs/{job_id}/files/{filename}", response_model=FileContentResponse)
async def get_file_content(job_id: str, filename: str) -> FileContentResponse:
    """Fallback: read a file from disk for inline viewing."""
    import csv as _csv, json as _json

    output_dir = Path(settings.output_dir) / job_id
    file_path = output_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found or session expired")

    suffix = file_path.suffix.lstrip(".")
    if suffix == "json":
        with open(file_path, encoding="utf-8") as f:
            data = _json.load(f)
        columns = list(data[0].keys()) if data else []
        return FileContentResponse(filename=filename, format="json", data=data, columns=columns)

    rows: list[dict] = []
    with open(file_path, encoding="utf-8-sig") as f:
        reader = _csv.DictReader(f)
        columns = list(reader.fieldnames or [])
        for row in reader:
            rows.append({k: (None if v == "" else v) for k, v in row.items()})
    return FileContentResponse(filename=filename, format="csv", data=rows, columns=columns)
