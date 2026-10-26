"""
TraceHarbor API — Failure Intelligence Schemas

Pydantic schemas for failure events, semantic clusters, status transitions,
similarity search, and clustering jobs.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FailureEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    source_type: str
    source_id: uuid.UUID
    run_id: uuid.UUID | None = None
    trace_id: str | None = None
    agent_name: str | None = None
    agent_version: str | None = None
    model_name: str | None = None
    model_provider: str | None = None
    failure_category: str
    severity: str
    error_summary: str
    normalized_text: str
    embedding_status: str
    cluster_id: uuid.UUID | None = None
    occurred_at: datetime
    created_at: datetime
    failure_metadata: dict[str, Any] = Field(default_factory=dict)


class FailureEventListResponse(BaseModel):
    items: list[FailureEventResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ClusterStatusChangeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cluster_id: uuid.UUID
    previous_status: str
    new_status: str
    resolution_notes: str | None = None
    changed_at: datetime


class FailureClusterSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str | None = None
    dominant_category: str
    severity_distribution: dict[str, int] = Field(default_factory=dict)
    event_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    representative_summary: str | None = None
    affected_agents: list[str] = Field(default_factory=list)
    affected_models: list[str] = Field(default_factory=list)
    representative_traces: list[dict[str, Any]] = Field(default_factory=list)
    status: str
    resolution_notes: str | None = None
    algorithm_version: str
    similarity_threshold: float | None = None
    created_at: datetime
    updated_at: datetime


class FailureClusterDetailResponse(FailureClusterSummaryResponse):
    recent_events: list[FailureEventResponse] = Field(default_factory=list)
    status_history: list[ClusterStatusChangeResponse] = Field(default_factory=list)


class FailureClusterListResponse(BaseModel):
    items: list[FailureClusterSummaryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ClusterStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Target status: new, investigating, resolved, or ignored")
    resolution_notes: str | None = Field(None, description="Optional developer resolution rationale")


class SimilarFailureSearchRequest(BaseModel):
    query_text: str | None = Field(None, description="Raw or normalized error message to query")
    event_id: uuid.UUID | None = Field(None, description="Existing failure event ID to find matches for")
    threshold: float = Field(0.70, ge=0.0, le=1.0, description="Minimum similarity score [0.0, 1.0]")
    limit: int = Field(20, ge=1, le=100, description="Maximum candidate matches to return")


class SimilarFailureItem(BaseModel):
    event_id: uuid.UUID
    error_summary: str
    failure_category: str
    severity: str
    agent_name: str | None = None
    agent_version: str | None = None
    model_name: str | None = None
    similarity_score: float
    cluster_id: uuid.UUID | None = None
    occurred_at: str


class SimilarFailureSearchResponse(BaseModel):
    results: list[SimilarFailureItem]
    total: int
    search_method: str  # 'vector_similarity' or 'lexical_fallback'
    threshold: float


class ClusteringJobRequest(BaseModel):
    similarity_threshold: float | None = Field(None, ge=0.5, le=1.0)
    min_cluster_size: int | None = Field(None, ge=1, le=100)
    max_candidates: int | None = Field(None, ge=10, le=5000)
    run_in_background: bool = Field(False, description="Run clustering as an asynchronous background task")


class ClusteringJobResponse(BaseModel):
    status: str
    clusters_created: int = 0
    clusters_updated: int = 0
    events_assigned: int = 0
    events_unassigned: int = 0
    algorithm_version: str
    task_id: str | None = None


class FailureSyncRequest(BaseModel):
    auto_embed: bool = Field(True, description="Whether to automatically compute embeddings for synced events")
    run_in_background: bool = Field(False, description="Run sync as an asynchronous background task")


class FailureSyncResponse(BaseModel):
    scanned: int = 0
    created: int = 0
    skipped: int = 0
    status: str
    task_id: str | None = None


class FailureOverviewMetricsResponse(BaseModel):
    total_failure_events: int
    total_clusters: int
    clusters_by_status: dict[str, int]
    events_by_severity: dict[str, int]
    top_failure_categories: list[dict[str, Any]]
    top_affected_agents: list[dict[str, Any]]
    embedding_provider: str
    vector_search_available: bool
