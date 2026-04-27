import io
import pytest
from PIL import Image
from unittest.mock import MagicMock, AsyncMock


def make_test_image_bytes(width: int = 100, height: int = 100, fmt: str = "JPEG") -> bytes:
    """Create a minimal valid image in memory."""
    img = Image.new("RGB", (width, height), color=(200, 150, 100))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


@pytest.fixture
def test_image_bytes():
    return make_test_image_bytes()


@pytest.fixture
def mock_gemini_classify_response():
    """Mock Gemini response for classification."""
    mock = MagicMock()
    mock.text = '{"category": "cnic"}'
    return mock


@pytest.fixture
def mock_gemini_extract_response():
    """Mock Gemini response for CNIC extraction."""
    mock = MagicMock()
    mock.text = """{
        "name": "John Doe",
        "cnic_number": "12345-1234567-1",
        "date_of_birth": "1990-01-15",
        "gender": "Male",
        "issue_date": "2020-03-01",
        "expiry_date": "2030-03-01"
    }"""
    return mock
