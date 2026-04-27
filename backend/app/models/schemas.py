from enum import Enum
from typing import Any
from pydantic import BaseModel


class DocumentCategory(str, Enum):
    cnic = "cnic"
    driving_licence = "driving_licence"
    forms = "forms"
    invoices = "invoices"
    receipt = "receipt"
    resumes = "resumes"
    other = "other"


class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class ImageResult(BaseModel):
    filename: str
    category: str | None = None
    fields: dict[str, Any] | None = None
    error: str | None = None
    status: str = "pending"


class OutputFile(BaseModel):
    filename: str
    category: str
    format: str  # "csv", "json", or "pdf"
    record_count: int
    path: str
    content: str | None = None  # raw text content embedded for client-side viewing


class JobState(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.pending
    total: int = 0
    processed: int = 0
    images: list[ImageResult] = []
    output_files: list[OutputFile] = []
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    model: str
    api_key_configured: bool


class JobCreateResponse(BaseModel):
    job_id: str
    total: int
    message: str


class FileContentResponse(BaseModel):
    filename: str
    format: str
    data: list[dict[str, Any]]
    columns: list[str]
