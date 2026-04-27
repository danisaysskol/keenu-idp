import io
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.api.routes import job_store
from app.models.schemas import JobStatus, JobState, OutputFile


def make_image_bytes(fmt: str = "JPEG") -> bytes:
    img = Image.new("RGB", (50, 50), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


@pytest.fixture(autouse=True)
def clear_job_store():
    """Ensure job store is clean between tests."""
    job_store.clear()
    yield
    job_store.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["api_key_configured"] is True
        assert "model" in data

    def test_health_without_api_key(self, client):
        with patch("app.api.routes.settings") as mock_settings:
            mock_settings.google_api_key = ""
            mock_settings.gemini_model = "gemini-3.1-flash-lite-preview"
            response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["api_key_configured"] is False


class TestCreateJob:
    def test_upload_single_image_creates_job(self, client):
        image_bytes = make_image_bytes()
        with patch("app.api.routes.process_job") as mock_process:
            mock_process.return_value = None
            response = client.post(
                "/api/jobs",
                files=[("files", ("test.jpg", image_bytes, "image/jpeg"))],
            )
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["total"] == 1

    def test_upload_multiple_images(self, client):
        image_bytes = make_image_bytes()
        files = [("files", (f"img{i}.jpg", image_bytes, "image/jpeg")) for i in range(3)]
        with patch("app.api.routes.process_job"):
            response = client.post("/api/jobs", files=files)
        assert response.status_code == 202
        assert response.json()["total"] == 3

    def test_no_files_returns_400(self, client):
        response = client.post("/api/jobs", files=[])
        assert response.status_code in (400, 422)

    def test_unsupported_file_type_returns_400(self, client):
        response = client.post(
            "/api/jobs",
            files=[("files", ("doc.pdf", b"fake pdf content", "application/pdf"))],
        )
        assert response.status_code == 400

    def test_job_id_is_unique(self, client):
        image_bytes = make_image_bytes()
        ids = set()
        with patch("app.api.routes.process_job"):
            for _ in range(3):
                r = client.post(
                    "/api/jobs",
                    files=[("files", ("img.jpg", image_bytes, "image/jpeg"))],
                )
                ids.add(r.json()["job_id"])
        assert len(ids) == 3


class TestGetJob:
    def test_get_pending_job(self, client):
        image_bytes = make_image_bytes()
        with patch("app.api.routes.process_job"):
            create_resp = client.post(
                "/api/jobs",
                files=[("files", ("img.jpg", image_bytes, "image/jpeg"))],
            )
        job_id = create_resp.json()["job_id"]

        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert "status" in data
        assert "total" in data

    def test_missing_job_returns_404(self, client):
        response = client.get("/api/jobs/nonexistent-id")
        assert response.status_code == 404


class TestListFiles:
    def test_complete_job_returns_files(self, client):
        job_id = "test-job-123"
        job_store[job_id] = JobState(
            job_id=job_id,
            status=JobStatus.complete,
            total=1,
            processed=1,
            output_files=[
                OutputFile(
                    filename="20240101_cnic.csv",
                    category="cnic",
                    format="csv",
                    record_count=1,
                    path="/tmp/test.csv",
                )
            ],
        )
        response = client.get(f"/api/jobs/{job_id}/files")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["filename"] == "20240101_cnic.csv"

    def test_incomplete_job_returns_409(self, client):
        job_id = "pending-job"
        job_store[job_id] = JobState(
            job_id=job_id, status=JobStatus.processing, total=5
        )
        response = client.get(f"/api/jobs/{job_id}/files")
        assert response.status_code == 409

    def test_missing_job_returns_404(self, client):
        response = client.get("/api/jobs/no-such-job/files")
        assert response.status_code == 404
