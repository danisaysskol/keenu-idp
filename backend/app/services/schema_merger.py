import re


def normalize_key(key: str) -> str:
    """Lowercase, strip, replace spaces/hyphens with underscores."""
    key = str(key).strip().lower()
    key = re.sub(r"[\s\-]+", "_", key)
    key = re.sub(r"[^\w]", "", key)
    return key


def merge_schemas(records: list[dict]) -> list[dict]:
    """
    Union all keys across records, normalize key names, fill missing with None.
    Preserves insertion order (first-seen key ordering).
    """
    if not records:
        return []

    # Build ordered union of all keys
    all_keys: list[str] = []
    seen: set[str] = set()
    normalized_records: list[dict] = []

    for record in records:
        normalized = {normalize_key(k): v for k, v in record.items()}
        normalized_records.append(normalized)
        for k in normalized:
            if k not in seen:
                all_keys.append(k)
                seen.add(k)

    # Fill missing keys with None
    return [{k: rec.get(k) for k in all_keys} for rec in normalized_records]
