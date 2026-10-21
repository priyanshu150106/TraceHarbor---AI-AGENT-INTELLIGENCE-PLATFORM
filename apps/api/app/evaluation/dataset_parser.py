"""
TraceHarbor API — Dataset File Parser & Strict Validator

Parses and validates CSV and JSON datasets according to TraceHarbor security standards.
Enforces size limits, case limits, UTF-8 encoding, and prevents code/SQL execution.
"""

import csv
import io
import json
from typing import Any

from fastapi import HTTPException, status

from app.core.config import settings


def parse_and_validate_dataset_content(
    raw_bytes: bytes,
    filename: str,
) -> list[dict[str, Any]]:
    """
    Parse uploaded dataset file (JSON or CSV) and return validated list of test case dictionaries.

    Raises HTTPException with status 422 on validation or encoding errors,
    or 413 if the payload exceeds size or case count limits.
    """
    # 1. Enforce file size limit
    if len(raw_bytes) > settings.max_dataset_upload_size_bytes:
        max_mb = settings.max_dataset_upload_size_bytes / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {max_mb:.1f} MB.",
        )

    # 2. Decode UTF-8 (handling UTF-8 with BOM if present)
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid file encoding: must be valid UTF-8. Error at byte {e.start}: {e.reason}.",
        ) from e

    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="Uploaded file is empty.",
        )

    fname_lower = filename.lower()
    if fname_lower.endswith(".json") or text.strip().startswith("["):
        cases = _parse_json(text)
    elif fname_lower.endswith(".csv") or "," in text.splitlines()[0]:
        cases = _parse_csv(text)
    else:
        # Default try JSON then CSV
        try:
            cases = _parse_json(text)
        except HTTPException:
            cases = _parse_csv(text)

    # 3. Enforce maximum case count limit
    if len(cases) > settings.max_dataset_cases:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Dataset contains {len(cases)} test cases, which exceeds the maximum limit "
                f"of {settings.max_dataset_cases} cases per dataset."
            ),
        )

    if not cases:
        raise HTTPException(
            status_code=422,
            detail="Dataset must contain at least 1 valid test case.",
        )

    return cases


def _parse_json(text: str) -> list[dict[str, Any]]:
    """Parse JSON array of test cases."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Malformed JSON syntax at line {e.lineno}, col {e.colno}: {e.msg}.",
        ) from e

    if not isinstance(data, list):
        raise HTTPException(
            status_code=422,
            detail="JSON dataset root element must be a list/array of test case objects.",
        )

    validated_cases: list[dict[str, Any]] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise HTTPException(
                status_code=422,
                detail=f"Test case at index {idx} must be a JSON object with 'input' field.",
            )

        if "input" not in item or item["input"] is None or str(item["input"]).strip() == "":
            raise HTTPException(
                status_code=422,
                detail=f"Test case at index {idx} is missing required non-empty 'input' field.",
            )

        case_dict = {
            "input": item["input"],
            "expected_output": item.get("expected_output"),
            "criteria": item.get("criteria") if isinstance(item.get("criteria"), dict) else (
                {"required_keywords": [item["criteria"]]} if isinstance(item.get("criteria"), str) else None
            ),
            "metadata": item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
            "tags": item.get("tags") if isinstance(item.get("tags"), list) else (
                [t.strip() for t in str(item.get("tags")).split(",") if t.strip()] if item.get("tags") else []
            ),
        }
        validated_cases.append(case_dict)

    return validated_cases


def _parse_csv(text: str) -> list[dict[str, Any]]:
    """Parse CSV format with headers."""
    f = io.StringIO(text.strip())
    reader = csv.DictReader(f)

    if not reader.fieldnames:
        raise HTTPException(
            status_code=422,
            detail="CSV file must have header row with at least an 'input' column.",
        )

    headers_lower = {name.lower().strip(): name for name in reader.fieldnames if name}
    if "input" not in headers_lower:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required CSV header 'input'. Found headers: {list(reader.fieldnames)}.",
        )

    input_key = headers_lower["input"]
    expected_key = headers_lower.get("expected_output") or headers_lower.get("expected")
    criteria_key = headers_lower.get("criteria")
    metadata_key = headers_lower.get("metadata")
    tags_key = headers_lower.get("tags")

    validated_cases: list[dict[str, Any]] = []
    for row_idx, row in enumerate(reader, start=2):  # line 2 is first data row
        raw_input = row.get(input_key, "").strip() if row.get(input_key) else ""
        if not raw_input:
            raise HTTPException(
                status_code=422,
                detail=f"Row {row_idx}: 'input' column cannot be empty.",
            )

        # Expected output
        raw_expected = row.get(expected_key, "").strip() if expected_key and row.get(expected_key) else None
        if raw_expected:
            try:
                expected_val = json.loads(raw_expected)
            except Exception:
                expected_val = raw_expected
        else:
            expected_val = None

        # Criteria
        criteria_val: dict[str, Any] | None = None
        raw_criteria = row.get(criteria_key, "").strip() if criteria_key and row.get(criteria_key) else None
        if raw_criteria:
            try:
                criteria_val = json.loads(raw_criteria)
            except Exception:
                # If plain string, treat as required keywords
                criteria_val = {"required_keywords": [k.strip() for k in raw_criteria.split(",") if k.strip()]}

        # Metadata
        meta_val: dict[str, Any] = {}
        raw_meta = row.get(metadata_key, "").strip() if metadata_key and row.get(metadata_key) else None
        if raw_meta:
            try:
                meta_val = json.loads(raw_meta)
            except Exception:
                meta_val = {"category": raw_meta}

        # Tags
        tags_val: list[str] = []
        raw_tags = row.get(tags_key, "").strip() if tags_key and row.get(tags_key) else None
        if raw_tags:
            try:
                parsed_tags = json.loads(raw_tags)
                if isinstance(parsed_tags, list):
                    tags_val = [str(t) for t in parsed_tags]
            except Exception:
                tags_val = [t.strip() for t in raw_tags.split(",") if t.strip()]

        validated_cases.append({
            "input": raw_input,
            "expected_output": expected_val,
            "criteria": criteria_val,
            "metadata": meta_val,
            "tags": tags_val,
        })

    return validated_cases
