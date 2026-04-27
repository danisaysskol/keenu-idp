import pytest
from app.services.schema_merger import normalize_key, merge_schemas


class TestNormalizeKey:
    def test_lowercase(self):
        assert normalize_key("Name") == "name"

    def test_spaces_to_underscores(self):
        assert normalize_key("Date of Birth") == "date_of_birth"

    def test_hyphens_to_underscores(self):
        assert normalize_key("issue-date") == "issue_date"

    def test_strips_special_chars(self):
        assert normalize_key("total_amount$") == "total_amount"

    def test_multiple_spaces(self):
        # Multiple consecutive spaces collapse into a single underscore
        assert normalize_key("  vendor  name  ") == "vendor_name"

    def test_already_normalized(self):
        assert normalize_key("cnic_number") == "cnic_number"


class TestMergeSchemas:
    def test_single_record_passthrough(self):
        records = [{"name": "John", "cnic_number": "12345-1234567-1"}]
        result = merge_schemas(records)
        assert len(result) == 1
        assert result[0]["name"] == "John"

    def test_two_records_different_keys_merged(self):
        records = [
            {"name": "John", "cnic_number": "12345-1234567-1"},
            {"name": "Jane", "date_of_birth": "1995-05-20"},
        ]
        result = merge_schemas(records)
        assert len(result) == 2
        # All keys present in both
        assert "name" in result[0]
        assert "cnic_number" in result[0]
        assert "date_of_birth" in result[0]
        # Missing key filled with None
        assert result[0]["date_of_birth"] is None
        assert result[1]["cnic_number"] is None

    def test_key_normalization_merges_duplicates(self):
        records = [
            {"Date of Birth": "1990-01-01"},
            {"date_of_birth": "1995-05-20"},
        ]
        result = merge_schemas(records)
        # Both should normalize to "date_of_birth"
        assert len(result) == 2
        assert "date_of_birth" in result[0]
        assert "date_of_birth" in result[1]

    def test_empty_list_returns_empty(self):
        assert merge_schemas([]) == []

    def test_null_values_preserved(self):
        records = [{"name": None, "amount": 100}]
        result = merge_schemas(records)
        assert result[0]["name"] is None
        assert result[0]["amount"] == 100

    def test_key_order_preserved(self):
        records = [
            {"name": "A", "email": "a@b.com", "phone": "123"},
            {"name": "B", "age": 30},
        ]
        result = merge_schemas(records)
        keys = list(result[0].keys())
        # name should appear before email, email before phone
        assert keys.index("name") < keys.index("email")
        assert keys.index("email") < keys.index("phone")

    def test_three_records_diverse_schemas(self):
        records = [
            {"a": 1},
            {"b": 2},
            {"c": 3},
        ]
        result = merge_schemas(records)
        assert len(result) == 3
        for row in result:
            assert set(row.keys()) == {"a", "b", "c"}
        assert result[0] == {"a": 1, "b": None, "c": None}
        assert result[1] == {"a": None, "b": 2, "c": None}
        assert result[2] == {"a": None, "b": None, "c": 3}
