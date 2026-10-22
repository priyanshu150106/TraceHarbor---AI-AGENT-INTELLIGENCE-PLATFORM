"""
TraceHarbor API — Safety Dataset Parser & Strict Schema Validator

Parses and validates safety red-teaming datasets (JSON and CSV).
Enforces encoding, size limits, case limits, and schema requirements.
"""

import csv
import io
import json
from typing import Any

from fastapi import HTTPException, status
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.safety import SafetyTestCaseCreate


def parse_and_validate_safety_dataset_content(
    raw_bytes: bytes,
    filename: str,
) -> list[dict[str, Any]]:
    """
    Parse uploaded safety dataset file (JSON or CSV) and return validated list of test case dictionaries.
    """
    # 1. Enforce file size limit
    if len(raw_bytes) > settings.max_dataset_upload_size_bytes:
        max_mb = settings.max_dataset_upload_size_bytes / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {max_mb:.1f} MB.",
        )

    # 2. Decode UTF-8
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
        cases = _parse_safety_json(text)
    elif fname_lower.endswith(".csv") or "," in text.splitlines()[0]:
        cases = _parse_safety_csv(text)
    else:
        try:
            cases = _parse_safety_json(text)
        except HTTPException:
            cases = _parse_safety_csv(text)

    # 3. Enforce case count limit
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
            detail="Safety dataset must contain at least 1 valid test case.",
        )

    return cases


def _parse_safety_json(text: str) -> list[dict[str, Any]]:
    """Parse JSON array of safety test cases."""
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
            detail="JSON dataset root element must be a list of safety test case objects.",
        )

    validated: list[dict[str, Any]] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise HTTPException(
                status_code=422,
                detail=f"Item at index {idx} is not a valid JSON object.",
            )

        # Support alias keys for convenience
        item_copy = dict(item)
        if "id" in item_copy and "test_case_id" not in item_copy:
            item_copy["test_case_id"] = str(item_copy["id"])
        if "input" in item_copy and "adversarial_input" not in item_copy:
            item_copy["adversarial_input"] = item_copy["input"]
        if "expected_output" in item_copy and "expected_safe_behavior" not in item_copy:
            item_copy["expected_safe_behavior"] = str(item_copy["expected_output"])

        try:
            tc = SafetyTestCaseCreate(**item_copy)
            validated.append(tc.model_dump())
        except ValidationError as e:
            err_msg = "; ".join([f"{err['loc']}: {err['msg']}" for err in e.errors()])
            raise HTTPException(
                status_code=422,
                detail=f"Validation failed for test case at index {idx}: {err_msg}",
            ) from e

    return validated


def _parse_safety_csv(text: str) -> list[dict[str, Any]]:
    """Parse CSV text with safety columns."""
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=422, detail="CSV file contains no header row.")

    # Normalize header names
    field_map = {name.strip().lower(): name for name in reader.fieldnames if name}

    # Find required columns
    def _find_field(*candidates: str) -> str | None:
        for c in candidates:
            if c in field_map:
                return field_map[c]
        return None

    id_col = _find_field("test_case_id", "id", "case_id")
    cat_col = _find_field("category", "threat_category")
    input_col = _find_field("adversarial_input", "input", "prompt", "query")
    behavior_col = _find_field("expected_safe_behavior", "expected_behavior", "expected_output")

    if not input_col or not behavior_col:
        raise HTTPException(
            status_code=422,
            detail="CSV header must contain 'adversarial_input' (or 'input') and 'expected_safe_behavior' columns.",
        )

    validated: list[dict[str, Any]] = []
    for row_num, row in enumerate(reader, start=2):
        if not any(row.values()):
            continue  # skip blank lines

        test_id = str(row.get(id_col) or f"SEC-CASE-{row_num:03d}").strip()
        category = str(row.get(cat_col) or "prompt_injection").strip()
        severity = str(row.get(_find_field("severity", "risk") or "") or "medium").strip()
        description = str(row.get(_find_field("description", "desc") or "") or f"Safety test case {test_id}").strip()
        raw_input = row.get(input_col, "").strip()
        expected_behavior = row.get(behavior_col, "").strip()

        # Try parsing JSON input or keep as string
        try:
            parsed_input = json.loads(raw_input)
        except Exception:
            parsed_input = raw_input

        # Try parsing tags if provided
        tags = []
        tags_col = _find_field("tags", "tag")
        if tags_col and row.get(tags_col):
            tags_str = row[tags_col].strip()
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]

        try:
            tc = SafetyTestCaseCreate(
                test_case_id=test_id,
                category=category,
                severity=severity,
                description=description,
                adversarial_input=parsed_input,
                expected_safe_behavior=expected_behavior,
                tags=tags,
            )
            validated.append(tc.model_dump())
        except ValidationError as e:
            err_msg = "; ".join([f"{err['loc']}: {err['msg']}" for err in e.errors()])
            raise HTTPException(
                status_code=422,
                detail=f"Validation failed on CSV row {row_num}: {err_msg}",
            ) from e

    return validated
