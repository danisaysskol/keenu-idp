import json
import pytest
from unittest.mock import patch, MagicMock

from app.services.gemini_service import (
    _strip_markdown_json,
    classify_document,
    extract_fields,
    CATEGORIES,
)
from tests.conftest import make_test_image_bytes


class TestStripMarkdownJson:
    def test_clean_json_passthrough(self):
        raw = '{"category": "cnic"}'
        assert _strip_markdown_json(raw) == raw

    def test_strips_json_fences(self):
        raw = '```json\n{"category": "cnic"}\n```'
        result = _strip_markdown_json(raw)
        assert result == '{"category": "cnic"}'

    def test_strips_plain_fences(self):
        raw = '```\n{"key": "value"}\n```'
        result = _strip_markdown_json(raw)
        assert result == '{"key": "value"}'

    def test_strips_whitespace(self):
        raw = '  \n{"key": "value"}\n  '
        result = _strip_markdown_json(raw)
        assert result == '{"key": "value"}'

    def test_handles_uppercase_json_fence(self):
        raw = '```JSON\n{"a": 1}\n```'
        result = _strip_markdown_json(raw)
        assert result == '{"a": 1}'


class TestClassifyDocument:
    @pytest.mark.asyncio
    async def test_returns_valid_category(self):
        image_bytes = make_test_image_bytes()
        mock_response = MagicMock()
        mock_response.text = '{"category": "cnic"}'

        with patch("app.services.gemini_service._get_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_fn.return_value = mock_client

            result = await classify_document(image_bytes, "image/jpeg")

        assert result == "cnic"
        assert result in CATEGORIES

    @pytest.mark.asyncio
    async def test_falls_back_to_other_on_unknown_category(self):
        image_bytes = make_test_image_bytes()
        mock_response = MagicMock()
        mock_response.text = '{"category": "passport"}'

        with patch("app.services.gemini_service._get_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_fn.return_value = mock_client

            result = await classify_document(image_bytes, "image/jpeg")

        assert result == "other"

    @pytest.mark.asyncio
    async def test_handles_markdown_wrapped_response(self):
        image_bytes = make_test_image_bytes()
        mock_response = MagicMock()
        mock_response.text = '```json\n{"category": "invoices"}\n```'

        with patch("app.services.gemini_service._get_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_fn.return_value = mock_client

            result = await classify_document(image_bytes, "image/jpeg")

        assert result == "invoices"

    @pytest.mark.asyncio
    async def test_returns_other_on_json_decode_error(self):
        image_bytes = make_test_image_bytes()
        mock_response = MagicMock()
        mock_response.text = "not valid json at all"

        with patch("app.services.gemini_service._get_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_fn.return_value = mock_client

            result = await classify_document(image_bytes, "image/jpeg")

        assert result == "other"

    @pytest.mark.asyncio
    async def test_returns_other_on_empty_response(self):
        image_bytes = make_test_image_bytes()
        mock_response = MagicMock()
        mock_response.text = ""

        with patch("app.services.gemini_service._get_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_fn.return_value = mock_client

            result = await classify_document(image_bytes, "image/jpeg")

        assert result == "other"


class TestExtractFields:
    @pytest.mark.asyncio
    async def test_extracts_cnic_fields(self):
        image_bytes = make_test_image_bytes()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "name": "John Doe",
            "cnic_number": "12345-1234567-1",
            "date_of_birth": "1990-01-15",
        })

        with patch("app.services.gemini_service._get_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_fn.return_value = mock_client

            result = await extract_fields(image_bytes, "image/jpeg", "cnic")

        assert result["name"] == "John Doe"
        assert result["cnic_number"] == "12345-1234567-1"

    @pytest.mark.asyncio
    async def test_returns_empty_dict_on_empty_response(self):
        image_bytes = make_test_image_bytes()
        mock_response = MagicMock()
        mock_response.text = ""

        with patch("app.services.gemini_service._get_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_fn.return_value = mock_client

            result = await extract_fields(image_bytes, "image/jpeg", "cnic")

        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_dict_on_invalid_json(self):
        image_bytes = make_test_image_bytes()
        mock_response = MagicMock()
        mock_response.text = "invalid json {"

        with patch("app.services.gemini_service._get_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_fn.return_value = mock_client

            result = await extract_fields(image_bytes, "image/jpeg", "cnic")

        assert result == {}

    @pytest.mark.asyncio
    async def test_handles_markdown_wrapped_extraction(self):
        image_bytes = make_test_image_bytes()
        mock_response = MagicMock()
        mock_response.text = '```json\n{"vendor_name": "ABC Corp", "total_amount": 1000}\n```'

        with patch("app.services.gemini_service._get_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_fn.return_value = mock_client

            result = await extract_fields(image_bytes, "image/jpeg", "invoices")

        assert result["vendor_name"] == "ABC Corp"
        assert result["total_amount"] == 1000
