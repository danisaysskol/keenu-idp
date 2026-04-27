import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

from app.config import settings
from app.models.schemas import (
    FileContentResponse,
    HealthResponse,
    JobCreateResponse,
    JobState,
    JobStatus,
)
from app.services.output_generator import read_output_file
from app.services.processor import process_job, SUPPORTED_MIME_TYPES
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api")

# In-memory job store (sufficient for demo; not shared across workers)
job_store: dict[str, JobState] = {}

_MAX_FILES = 10
_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    configured = bool(settings.google_api_key)
    return HealthResponse(
        status="ok" if configured else "degraded",
        model=settings.gemini_model,
        api_key_configured=configured,
    )


@router.post("/jobs", response_model=JobCreateResponse, status_code=202)
async def create_job(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
) -> JobCreateResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    if len(files) > _MAX_FILES:
        raise HTTPException(
            status_code=400, detail=f"Too many files. Maximum is {_MAX_FILES}."
        )

    # Read + validate all files eagerly before starting background task
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
                detail=f"File '{upload.filename}' exceeds 10MB limit.",
            )
        file_data.append((upload.filename or f"file_{len(file_data)}", content))

    job_id = str(uuid.uuid4())
    job_store[job_id] = JobState(job_id=job_id, total=len(file_data))

    background_tasks.add_task(process_job, job_id, file_data, job_store)
    logger.info("Created job %s with %d files", job_id, len(file_data))

    return JobCreateResponse(
        job_id=job_id,
        total=len(file_data),
        message=f"Processing {len(file_data)} image(s). Poll /api/jobs/{job_id} for status.",
    )


@router.get("/jobs/{job_id}", response_model=JobState)
async def get_job(job_id: str) -> JobState:
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job


@router.get("/jobs/{job_id}/files", response_model=list)
async def list_job_files(job_id: str) -> list:
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if job.status != JobStatus.complete:
        raise HTTPException(
            status_code=409, detail=f"Job is not complete (status: {job.status})"
        )
    return [f.model_dump() for f in job.output_files]


@router.get("/jobs/{job_id}/files/{filename}", response_model=FileContentResponse)
async def get_file_content(job_id: str, filename: str) -> FileContentResponse:
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    output_file = next((f for f in job.output_files if f.filename == filename), None)
    if not output_file:
        raise HTTPException(
            status_code=404, detail=f"File '{filename}' not found in job '{job_id}'"
        )

    data, columns = read_output_file(output_file.path, output_file.format)
    return FileContentResponse(
        filename=filename,
        format=output_file.format,
        data=data,
        columns=columns,
    )


@router.get("/jobs/{job_id}/download/{filename}")
async def download_file(job_id: str, filename: str) -> FileResponse:
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    output_file = next((f for f in job.output_files if f.filename == filename), None)
    if not output_file:
        raise HTTPException(
            status_code=404, detail=f"File '{filename}' not found in job '{job_id}'"
        )

    file_path = Path(output_file.path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Output file missing from disk")

    _mime = {"csv": "text/csv", "json": "application/json", "pdf": "application/pdf"}
    media_type = _mime.get(output_file.format, "application/octet-stream")
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type,
    )
