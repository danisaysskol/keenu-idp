import csv
import io
import json
import pytest
from pathlib import Path
from unittest.mock import patch
from PIL import Image

from app.services.output_generator import generate_outputs, read_output_file


def _img() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (60, 80), color=(180, 120, 90)).save(buf, format="JPEG")
    return buf.getvalue()


def _result(filename, category, fields):
    """Build a result dict as processor.py now produces it."""
    return {
        "filename": filename,
        "category": category,
        "fields": fields,
        "image_bytes": _img(),
        "mime_type": "image/jpeg",
    }


@pytest.fixture
def tmp_output_dir(tmp_path):
    with patch("app.services.output_generator.settings") as mock_settings:
        mock_settings.output_dir = str(tmp_path)
        yield tmp_path


class TestGenerateOutputs:
    def test_generates_csv_json_and_pdf_per_category(self, tmp_output_dir):
        results = [
            _result("a.jpg", "cnic", {"name": "Alice", "cnic_number": "12345-1234567-1"}),
            _result("b.jpg", "cnic", {"name": "Bob", "date_of_birth": "1990-01-01"}),
        ]
        output_files = generate_outputs("job1", results)

        formats = {f.format for f in output_files}
        assert "csv" in formats
        assert "json" in formats
        assert "pdf" in formats

    def test_csv_has_correct_headers(self, tmp_output_dir):
        results = [
            _result("a.jpg", "invoices", {"vendor_name": "Acme", "total_amount": 500.0}),
        ]
        output_files = generate_outputs("job2", results)
        csv_file = next(f for f in output_files if f.format == "csv")

        with open(csv_file.path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            rows = list(reader)

        assert "_source_file" in headers
        assert "vendor_name" in headers
        assert "total_amount" in headers
        assert len(rows) == 1
        assert rows[0]["vendor_name"] == "Acme"

    def test_json_is_valid(self, tmp_output_dir):
        results = [_result("r1.jpg", "resumes", {"name": "Eve", "email": "eve@test.com"})]
        output_files = generate_outputs("job3", results)
        json_file = next(f for f in output_files if f.format == "json")

        with open(json_file.path, encoding="utf-8") as f:
            data = json.load(f)

        assert isinstance(data, list)
        assert data[0]["name"] == "Eve"

    def test_merged_schema_fills_nulls(self, tmp_output_dir):
        results = [
            _result("a.jpg", "cnic", {"name": "Alice", "cnic_number": "12345-1234567-1"}),
            _result("b.jpg", "cnic", {"name": "Bob", "date_of_birth": "1990-01-01"}),
        ]
        output_files = generate_outputs("job4", results)
        json_file = next(f for f in output_files if f.format == "json")

        with open(json_file.path, encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == 2
        alice = next(r for r in data if r.get("name") == "Alice")
        assert alice.get("date_of_birth") is None
        bob = next(r for r in data if r.get("name") == "Bob")
        assert bob.get("cnic_number") is None

    def test_csv_utf8_sig_encoding(self, tmp_output_dir):
        results = [_result("f.jpg", "forms", {"field": "Urdu: اردو"})]
        output_files = generate_outputs("job5", results)
        csv_file = next(f for f in output_files if f.format == "csv")

        with open(csv_file.path, "rb") as f:
            header = f.read(3)
        assert header == b"\xef\xbb\xbf", "CSV should start with UTF-8 BOM"

    def test_empty_results_returns_no_files(self, tmp_output_dir):
        assert generate_outputs("job6", []) == []

    def test_record_count_is_correct(self, tmp_output_dir):
        results = [
            _result(f"f{i}.jpg", "receipt", {"total_amount": i * 10})
            for i in range(5)
        ]
        output_files = generate_outputs("job7", results)
        csv_files = [f for f in output_files if f.format == "csv"]
        assert all(f.record_count == 5 for f in csv_files)

    def test_pdf_page_count_matches_images(self, tmp_output_dir):
        results = [
            _result("a.jpg", "invoices", {"vendor_name": "A"}),
            _result("b.jpg", "invoices", {"vendor_name": "B"}),
            _result("c.jpg", "invoices", {"vendor_name": "C"}),
        ]
        output_files = generate_outputs("job8", results)
        pdf_file = next((f for f in output_files if f.format == "pdf"), None)
        assert pdf_file is not None
        assert pdf_file.record_count == 3  # 3 pages

    def test_pdf_file_is_valid_pdf(self, tmp_output_dir):
        results = [_result("x.jpg", "cnic", {"name": "Test"})]
        output_files = generate_outputs("job9", results)
        pdf_file = next((f for f in output_files if f.format == "pdf"), None)
        assert pdf_file is not None

        with open(pdf_file.path, "rb") as f:
            magic = f.read(4)
        assert magic == b"%PDF", "File should start with PDF magic bytes"

    def test_multiple_categories_produce_separate_pdfs(self, tmp_output_dir):
        results = [
            _result("a.jpg", "cnic", {"name": "Alice"}),
            _result("b.jpg", "resumes", {"name": "Bob"}),
        ]
        output_files = generate_outputs("job10", results)
        pdf_files = [f for f in output_files if f.format == "pdf"]
        pdf_categories = {f.category for f in pdf_files}
        assert "cnic" in pdf_categories
        assert "resumes" in pdf_categories
        assert len(pdf_files) == 2

    def test_missing_image_bytes_skips_pdf_gracefully(self, tmp_output_dir):
        # Results without image_bytes should still produce CSV/JSON, just no PDF
        results = [{"filename": "a.jpg", "category": "forms", "fields": {"key": "val"}}]
        output_files = generate_outputs("job11", results)
        formats = {f.format for f in output_files}
        assert "csv" in formats
        assert "json" in formats
        # PDF may or may not exist — no crash is the requirement


class TestReadOutputFile:
    def test_reads_json_file(self, tmp_path):
        data = [{"name": "Alice", "amount": 100}]
        path = tmp_path / "test.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        result, columns = read_output_file(str(path), "json")
        assert result == data
        assert "name" in columns

    def test_reads_csv_file(self, tmp_path):
        path = tmp_path / "test.csv"
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "amount"])
            writer.writeheader()
            writer.writerow({"name": "Bob", "amount": "200"})

        result, columns = read_output_file(str(path), "csv")
        assert len(result) == 1
        assert result[0]["name"] == "Bob"

    def test_missing_file_returns_empty(self, tmp_path):
        result, columns = read_output_file(str(tmp_path / "nonexistent.json"), "json")
        assert result == []
        assert columns == []
