import pytest
from app.utils.validators import (
    validate_cnic,
    validate_date,
    validate_amount,
    validate_email,
    validate_phone,
    validate_fields,
)


class TestValidateCnic:
    def test_valid_cnic(self):
        assert validate_cnic("12345-1234567-1") == "12345-1234567-1"

    def test_valid_cnic_with_whitespace(self):
        assert validate_cnic("  12345-1234567-1  ") == "12345-1234567-1"

    def test_invalid_too_short(self):
        assert validate_cnic("1234-12345-1") is None

    def test_invalid_no_dashes(self):
        assert validate_cnic("1234512345671") is None

    def test_invalid_wrong_segment_lengths(self):
        assert validate_cnic("123456-123456-1") is None

    def test_none_input(self):
        assert validate_cnic(None) is None

    def test_empty_string(self):
        assert validate_cnic("") is None

    def test_letters_in_cnic(self):
        assert validate_cnic("ABCDE-1234567-1") is None


class TestValidateDate:
    def test_valid_date(self):
        assert validate_date("2024-01-15") == "2024-01-15"

    def test_invalid_format_slash(self):
        assert validate_date("15/01/2024") is None

    def test_invalid_format_dot(self):
        assert validate_date("15.01.2024") is None

    def test_invalid_format_ddmmyyyy(self):
        assert validate_date("01-15-2024") is None

    def test_none_input(self):
        assert validate_date(None) is None

    def test_empty_string(self):
        assert validate_date("") is None

    def test_invalid_date_values(self):
        assert validate_date("2024-13-01") is None  # month 13

    def test_valid_leap_year(self):
        assert validate_date("2024-02-29") == "2024-02-29"


class TestValidateAmount:
    def test_plain_number(self):
        assert validate_amount("1234.56") == 1234.56

    def test_comma_separated(self):
        assert validate_amount("1,234.56") == 1234.56

    def test_with_currency_symbol(self):
        assert validate_amount("PKR 1,234") == 1234.0

    def test_integer(self):
        assert validate_amount(1000) == 1000.0

    def test_float_passthrough(self):
        assert validate_amount(99.99) == 99.99

    def test_none_input(self):
        assert validate_amount(None) is None

    def test_empty_string(self):
        assert validate_amount("") is None

    def test_non_numeric_string(self):
        assert validate_amount("N/A") is None

    def test_zero(self):
        assert validate_amount("0") == 0.0


class TestValidateEmail:
    def test_valid_email(self):
        assert validate_email("user@example.com") == "user@example.com"

    def test_valid_email_subdomain(self):
        assert validate_email("user@mail.example.co.uk") == "user@mail.example.co.uk"

    def test_missing_at(self):
        assert validate_email("userexample.com") is None

    def test_missing_domain(self):
        assert validate_email("user@") is None

    def test_none_input(self):
        assert validate_email(None) is None

    def test_empty_string(self):
        assert validate_email("") is None


class TestValidatePhone:
    def test_valid_local(self):
        assert validate_phone("0300-1234567") == "0300-1234567"

    def test_valid_international(self):
        assert validate_phone("+92-300-1234567") == "+92-300-1234567"

    def test_too_short(self):
        assert validate_phone("123456") is None

    def test_too_long(self):
        assert validate_phone("1234567890123456") is None

    def test_none_input(self):
        assert validate_phone(None) is None

    def test_empty_string(self):
        assert validate_phone("") is None


class TestValidateFields:
    def test_cnic_validates_relevant_fields(self):
        fields = {
            "name": "John Doe",
            "cnic_number": "12345-1234567-1",
            "date_of_birth": "1990-01-15",
        }
        result = validate_fields(fields, "cnic")
        assert result["cnic_number"] == "12345-1234567-1"
        assert result["date_of_birth"] == "1990-01-15"
        assert result["name"] == "John Doe"  # untouched

    def test_cnic_invalidates_bad_cnic(self):
        fields = {"cnic_number": "BAD-NUMBER"}
        result = validate_fields(fields, "cnic")
        assert result["cnic_number"] is None

    def test_invoice_validates_amount(self):
        fields = {"total_amount": "PKR 5,500.00", "date": "2024-03-15"}
        result = validate_fields(fields, "invoices")
        assert result["total_amount"] == 5500.0
        assert result["date"] == "2024-03-15"

    def test_resume_validates_email(self):
        fields = {"email": "bad-email", "phone": "0300-1234567"}
        result = validate_fields(fields, "resumes")
        assert result["email"] is None
        assert result["phone"] == "0300-1234567"

    def test_unknown_category_returns_fields_unchanged(self):
        fields = {"random_key": "random_value"}
        result = validate_fields(fields, "other")
        assert result["random_key"] == "random_value"

    def test_empty_fields_returns_empty(self):
        assert validate_fields({}, "cnic") == {}
