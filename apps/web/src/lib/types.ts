/**
 * TraceHarbor Frontend Type Definitions
 * Matches backend schemas from apps/api/app/schemas/runs.py
 */

export interface Span {
  id: string;
  run_id: string;
  parent_span_id: string | null;
  name: string;
  span_type: "llm" | "tool" | "retrieval" | "chain" | "agent" | "custom" | string;
  status: "running" | "completed" | "error" | string;
  input: Record<string, any> | null;
  output: Record<string, any> | null;
  error: string | null;
  model: string | null;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number | string;
  duration_ms: number | null;
  started_at: string;
  ended_at: string | null;
  metadata: Record<string, any>;
}

export interface RunSummary {
  id: string;
  project_id: string;
  name: string | null;
  status: "running" | "completed" | "error" | string;
  total_tokens: number;
  total_cost_usd: number | string;
  duration_ms: number | null;
  started_at: string;
  ended_at: string | null;
  tags: string[];
  metadata: Record<string, any>;
}

export interface RunDetail extends RunSummary {
  input: Record<string, any> | null;
  output: Record<string, any> | null;
  error: string | null;
  spans: Span[];
}

export interface RunListResponse {
  items: RunSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AnalyticsOverview {
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
  error_rate: number;
  p50_duration_ms?: number;
  avg_duration_ms: number;
  p95_duration_ms: number;
  total_tokens: number;
  total_cost_usd: number;
  cost_reported_runs?: number;
  unmetered_runs?: number;
  eval_pass_rate?: number | null;
  regression_count?: number;
  time_range?: string;
  recent_runs: RunSummary[];
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  runs_count: number;
}

export interface HealthStatus {
  status: string;
  app: string;
  version: string;
  timestamp?: string;
}

// ------------------- Phase 3: Datasets -------------------

export interface TestCase {
  id: string;
  dataset_id: string;
  input: any;
  expected_output: any | null;
  criteria: Record<string, any> | null;
  metadata: Record<string, any>;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface DatasetSummary {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  test_cases_count: number;
  experiments_count: number;
  created_at: string;
  updated_at: string;
}

export interface DatasetDetail {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  test_cases_count: number;
  test_cases: TestCase[];
  created_at: string;
  updated_at: string;
}

export interface DatasetListResponse {
  items: DatasetSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DatasetUploadResponse {
  id: string;
  name: string;
  cases_imported: number;
  message: string;
}

// ------------------- Phase 3: Experiments -------------------

export interface ApprovedAgent {
  agent_name: string;
  agent_version: string;
  description: string;
}

export interface EvaluationDetail {
  evaluator_name: string;
  evaluator_version: string;
  passed: boolean;
  outcome: "pass" | "fail" | "error";
  score: number;
  explanation: string;
  expected_value: any;
  actual_value: any;
  timestamp: string;
}

export interface ExperimentResult {
  id: string;
  experiment_id: string;
  test_case_id: string;
  run_id: string | null;
  test_input: any;
  expected_output: any | null;
  actual_output: any | null;
  scores: Record<string, number>;
  passed: boolean | null;
  status: "pass" | "fail" | "error" | "pending" | string;
  error: string | null;
  duration_ms: number | null;
  evaluation_details: EvaluationDetail[];
  created_at: string;
}

export interface ExperimentSummary {
  id: string;
  project_id: string;
  dataset_id: string;
  dataset_name?: string | null;
  name: string;
  description: string | null;
  status: "pending" | "running" | "completed" | "error" | "cancelled" | string;
  agent_name: string;
  agent_version: string;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  errored_cases: number;
  score: number | null;
  pass_rate: number | null;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
}

export interface ExperimentDetail extends ExperimentSummary {
  config: Record<string, any>;
  summary: Record<string, any> | null;
  results: ExperimentResult[];
}

export interface ExperimentListResponse {
  items: ExperimentSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ComparedCaseItem {
  test_case_id: string;
  input: any;
  expected_output: any | null;
  category: "regression" | "improvement" | "unchanged" | "error" | "missing" | string;
  missing_in?: string;
  a: {
    id: string;
    run_id: string | null;
    passed: boolean | null;
    status: string;
    scores: Record<string, number>;
    actual_output: any;
    duration_ms: number | null;
    error: string | null;
    evaluation_details: EvaluationDetail[];
  } | null;
  b: {
    id: string;
    run_id: string | null;
    passed: boolean | null;
    status: string;
    scores: Record<string, number>;
    actual_output: any;
    duration_ms: number | null;
    error: string | null;
    evaluation_details: EvaluationDetail[];
  } | null;
}

export interface ExperimentComparison {
  experiment_a: ExperimentSummary;
  experiment_b: ExperimentSummary;
  summary: {
    total_compared: number;
    regressions_count: number;
    improvements_count: number;
    unchanged_count: number;
    errors_count: number;
    missing_count: number;
    pass_rate_delta: number;
    score_delta: number;
  };
  regressions: ComparedCaseItem[];
  improvements: ComparedCaseItem[];
  unchanged: ComparedCaseItem[];
  errors: ComparedCaseItem[];
  missing: ComparedCaseItem[];
  all_cases: ComparedCaseItem[];
}

// ------------------- Phase 4: Advanced Analytics -------------------

export interface TimeseriesPoint {
  timestamp: string;
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
  error_rate: number;
  p50_duration_ms: number;
  p95_duration_ms: number;
  total_tokens: number;
  total_cost_usd: number;
  eval_pass_rate?: number | null;
}

export interface AnalyticsTimeseries {
  time_range: string;
  interval: string;
  points: TimeseriesPoint[];
  total_points: number;
}

export interface ModelUsageItem {
  model: string;
  call_count: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
}

export interface ModelsAnalytics {
  items: ModelUsageItem[];
  total_models: number;
}

export interface AgentUsageItem {
  agent_name: string;
  agent_version: string;
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
  error_rate: number;
  avg_duration_ms: number;
  p95_duration_ms: number;
  total_tokens: number;
  total_cost_usd: number;
  eval_pass_rate?: number | null;
}

export interface AgentsAnalytics {
  items: AgentUsageItem[];
  total_agents: number;
}

export interface CostBreakdownItem {
  date: string;
  agent_name: string;
  model: string;
  cost_usd: number;
  token_count: number;
}

export interface CostBreakdown {
  total_cost_usd: number;
  cost_reported_runs: number;
  unmetered_runs: number;
  by_agent: Record<string, number>;
  by_model: Record<string, number>;
  daily_breakdown: CostBreakdownItem[];
}

// ------------------- Phase 4: Alerting -------------------

export interface AlertRule {
  id: string;
  project_id: string;
  name: string;
  metric: string;
  operator: string;
  threshold: number;
  window_minutes: number;
  is_active: boolean;
  channel: string;
  webhook_url?: string | null;
  has_webhook_secret: boolean;
  cooldown_minutes: number;
  last_triggered_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AlertRuleCreate {
  name: string;
  metric: string;
  operator?: string;
  threshold: number;
  window_minutes?: number;
  channel?: string;
  webhook_url?: string;
  webhook_secret?: string;
  cooldown_minutes?: number;
}

export interface AlertRuleUpdate {
  name?: string;
  metric?: string;
  operator?: string;
  threshold?: number;
  window_minutes?: number;
  is_active?: boolean;
  channel?: string;
  webhook_url?: string;
  webhook_secret?: string;
  cooldown_minutes?: number;
}

export interface AlertHistory {
  id: string;
  rule_id: string;
  rule_name?: string | null;
  project_id: string;
  metric: string;
  metric_value: number;
  threshold: number;
  operator: string;
  message: string;
  status: string;
  notification_status: string;
  notification_error?: string | null;
  acknowledged: boolean;
  fired_at: string;
  created_at: string;
}

export interface AlertHistoryList {
  items: AlertHistory[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AlertEvaluationResult {
  rule_id: string;
  rule_name: string;
  metric: string;
  observed_value: number;
  threshold: number;
  operator: string;
  triggered: boolean;
  cooldown_active: boolean;
  notification_status?: string | null;
  message: string;
}

export interface AlertEvaluationBatch {
  rules_evaluated: number;
  alerts_triggered: number;
  cooldown_suppressed: number;
  results: AlertEvaluationResult[];
}

