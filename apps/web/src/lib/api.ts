/**
 * TraceHarbor Frontend API Client
 * Connects to the FastAPI backend with error handling and typed responses.
 */

import {
  AnalyticsOverview,
  ApprovedAgent,
  DatasetDetail,
  DatasetListResponse,
  DatasetUploadResponse,
  ExperimentComparison,
  ExperimentDetail,
  ExperimentListResponse,
  ExperimentSummary,
  HealthStatus,
  Project,
  RunDetail,
  RunListResponse,
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";


class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      cache: "no-store",
    });

    if (!res.ok) {
      let errorMsg = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const errorJson = await res.json();
        if (errorJson.detail) {
          errorMsg = typeof errorJson.detail === "string" ? errorJson.detail : JSON.stringify(errorJson.detail);
        }
      } catch {
        // Fall back to HTTP status message
      }
      throw new ApiError(errorMsg, res.status);
    }

    return (await res.json()) as T;
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(
      `Unable to connect to TraceHarbor API at ${API_BASE_URL}. Ensure the backend server is running.`,
      0
    );
  }
}

export async function fetchHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/health");
}

export async function fetchAnalyticsOverview(projectId?: string): Promise<AnalyticsOverview> {
  const query = projectId ? `?project_id=${projectId}` : "";
  return request<AnalyticsOverview>(`/v1/analytics/overview${query}`);
}

export async function fetchRuns(params: {
  status?: string;
  search?: string;
  page?: number;
  pageSize?: number;
  projectId?: string;
} = {}): Promise<RunListResponse> {
  const queryParts: string[] = [];
  if (params.status && params.status !== "all") {
    queryParts.push(`status=${encodeURIComponent(params.status)}`);
  }
  if (params.search) {
    queryParts.push(`search=${encodeURIComponent(params.search)}`);
  }
  if (params.page) {
    queryParts.push(`page=${params.page}`);
  }
  if (params.pageSize) {
    queryParts.push(`page_size=${params.pageSize}`);
  }
  if (params.projectId) {
    queryParts.push(`project_id=${encodeURIComponent(params.projectId)}`);
  }

  const query = queryParts.length > 0 ? `?${queryParts.join("&")}` : "";
  return request<RunListResponse>(`/v1/runs${query}`);
}

export async function fetchRunDetail(runId: string): Promise<RunDetail> {
  return request<RunDetail>(`/v1/runs/${runId}`);
}

export async function fetchProjects(): Promise<Project[]> {
  return request<Project[]>("/v1/projects");
}

// ------------------- Phase 3: Datasets -------------------

export async function fetchDatasets(params: {
  page?: number;
  pageSize?: number;
  search?: string;
  projectId?: string;
} = {}): Promise<DatasetListResponse> {
  const queryParts: string[] = [];
  if (params.page) queryParts.push(`page=${params.page}`);
  if (params.pageSize) queryParts.push(`page_size=${params.pageSize}`);
  if (params.search) queryParts.push(`search=${encodeURIComponent(params.search)}`);
  if (params.projectId) queryParts.push(`project_id=${encodeURIComponent(params.projectId)}`);

  const query = queryParts.length > 0 ? `?${queryParts.join("&")}` : "";
  return request<DatasetListResponse>(`/v1/datasets${query}`);
}

export async function fetchDatasetDetail(
  datasetId: string,
  page: number = 1,
  pageSize: number = 50
): Promise<DatasetDetail> {
  return request<DatasetDetail>(`/v1/datasets/${datasetId}?page=${page}&page_size=${pageSize}`);
}

export async function createDataset(payload: {
  name: string;
  description?: string;
  cases?: any[];
}): Promise<DatasetDetail> {
  return request<DatasetDetail>("/v1/datasets", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function uploadDataset(formData: FormData): Promise<DatasetUploadResponse> {
  const url = `${API_BASE_URL}/v1/datasets/upload`;
  const res = await fetch(url, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    let errorMsg = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const errorJson = await res.json();
      if (errorJson.detail) {
        errorMsg = typeof errorJson.detail === "string" ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return (await res.json()) as DatasetUploadResponse;
}

export async function deleteDataset(datasetId: string): Promise<{ status: string; message: string }> {
  return request<{ status: string; message: string }>(`/v1/datasets/${datasetId}`, {
    method: "DELETE",
  });
}

// ------------------- Phase 3: Experiments -------------------

export async function fetchApprovedAgents(): Promise<ApprovedAgent[]> {
  return request<ApprovedAgent[]>("/v1/experiments/agents");
}

export async function fetchExperiments(params: {
  page?: number;
  pageSize?: number;
  status?: string;
  search?: string;
  datasetId?: string;
} = {}): Promise<ExperimentListResponse> {
  const queryParts: string[] = [];
  if (params.page) queryParts.push(`page=${params.page}`);
  if (params.pageSize) queryParts.push(`page_size=${params.pageSize}`);
  if (params.status && params.status !== "all") queryParts.push(`status=${encodeURIComponent(params.status)}`);
  if (params.search) queryParts.push(`search=${encodeURIComponent(params.search)}`);
  if (params.datasetId) queryParts.push(`dataset_id=${encodeURIComponent(params.datasetId)}`);

  const query = queryParts.length > 0 ? `?${queryParts.join("&")}` : "";
  return request<ExperimentListResponse>(`/v1/experiments${query}`);
}

export async function fetchExperimentDetail(experimentId: string): Promise<ExperimentDetail> {
  return request<ExperimentDetail>(`/v1/experiments/${experimentId}`);
}

export async function createExperiment(payload: {
  name: string;
  dataset_id: string;
  agent_name: string;
  agent_version: string;
  description?: string;
  config?: Record<string, any>;
}): Promise<ExperimentSummary> {
  return request<ExperimentSummary>("/v1/experiments", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function compareExperiments(aId: string, bId: string): Promise<ExperimentComparison> {
  return request<ExperimentComparison>(`/v1/experiments/compare?a=${aId}&b=${bId}`);
}
