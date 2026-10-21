"""
TraceHarbor API — Dataset & TestCase Pydantic Schemas
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TestCaseCreate(BaseModel):
    """Schema for adding an individual test case."""

    input: Any = Field(..., description="The prompt, query, or structured input given to the agent")
    expected_output: Any = Field(None, description="Optional golden answer or reference output")
    criteria: dict[str, Any] | None = Field(None, description="Evaluation criteria and thresholds")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Custom tags, difficulty, category")
    tags: list[str] = Field(default_factory=list, description="Categorization tags")


class TestCaseResponse(BaseModel):
    """Schema for returning a test case."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    input: Any
    expected_output: Any | None = None
    criteria: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TestCaseListResponse(BaseModel):
    """Paginated list of test cases."""

    items: list[TestCaseResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DatasetCreateRequest(BaseModel):
    """Schema for creating a new dataset with optional initial cases."""

    name: str = Field(..., min_length=1, max_length=100, description="Unique human-readable dataset name")
    description: str | None = Field(None, description="Optional description of dataset purpose")
    cases: list[TestCaseCreate] = Field(default_factory=list, description="Optional list of test cases")


class DatasetSummaryResponse(BaseModel):
    """Dataset summary including case and experiment counts."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None
    test_cases_count: int = 0
    experiments_count: int = 0
    created_at: datetime
    updated_at: datetime


class DatasetDetailResponse(BaseModel):
    """Dataset details with paginated test cases."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None
    test_cases_count: int
    test_cases: list[TestCaseResponse]
    created_at: datetime
    updated_at: datetime


class DatasetListResponse(BaseModel):
    """Paginated list of datasets."""

    items: list[DatasetSummaryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DatasetUploadResponse(BaseModel):
    """Response returned upon successful file import."""

    id: uuid.UUID
    name: str
    cases_imported: int
    message: str
