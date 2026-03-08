/**
 * API Types - Must match backend Pydantic schemas exactly
 */

// ============================================================
// Common Types
// ============================================================

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface TimeRange {
  start: string; // ISO 8601
  end: string; // ISO 8601
}

export interface MessageResponse {
  message: string;
  detail?: Record<string, unknown>;
}

export interface ErrorResponse {
  detail: string;
  error_code: string;
  context?: Record<string, unknown>;
}

// ============================================================
// Auth Types
// ============================================================

export enum UserRole {
  ANALYST = 'ANALYST',
  RISK_MANAGER = 'RISK_MANAGER',
  CFO = 'CFO',
  ADMIN = 'ADMIN',
}

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AccessTokenResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

export interface UserCreateRequest {
  email: string;
  password: string;
  full_name: string;
  role: UserRole;
}

// ============================================================
// Market Data Types
// ============================================================

export interface PriceTickResponse {
  id: string;
  time: string;
  jet_fuel_spot: number;
  heating_oil_futures: number | null;
  brent_futures: number | null;  // Match backend: brent_futures not brent_crude_futures
  wti_futures: number | null;     // Match backend: wti_futures not wti_crude_futures
  crack_spread: number | null;
  volatility_index: number | null;
  source: string;
  created_at: string;
}

export interface PriceTickSeriesResponse {
  ticks: PriceTickResponse[];
  start: string;
  end: string;
  count: number;
}

// ============================================================
// Recommendation Types
// ============================================================

export enum RecommendationStatus {
  PENDING = 'PENDING',
  APPROVED = 'APPROVED',
  REJECTED = 'REJECTED',
  DEFERRED = 'DEFERRED',
  EXPIRED = 'EXPIRED',
  CONSTRAINT_VIOLATED = 'CONSTRAINT_VIOLATED',
}

export enum DecisionType {
  APPROVE = 'APPROVE',
  REJECT = 'REJECT',
  DEFER = 'DEFER',
}

export interface AgentOutput {
  agent_id: string;
  risk_level: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  recommendation: string;
  metrics: Record<string, number>;
  constraints_satisfied: boolean;
  action_required: boolean;
  ifrs9_eligible: boolean | null;
  generated_at: string;
}

export interface HedgeRecommendationResponse {
  id: string;
  run_id: string;
  status: RecommendationStatus;
  optimal_hedge_ratio: number;
  instrument_mix: Record<string, number>;
  expected_var_reduction: number;
  hedge_effectiveness_r2: number;
  collateral_impact: number;
  ifrs9_eligible: boolean;
  risk_level: string;
  recommendation_text: string;
  constraints_satisfied: boolean;
  action_required: boolean;
  created_at: string;
  updated_at: string;
  agent_outputs?: AgentOutput[];  // Optional for now for backwards compatibility
}

export interface ApprovalResponse {
  id: string;
  recommendation_id: string;
  approver_id: string;
  decision: DecisionType;
  comments: string | null;
  created_at: string;
}

export interface HedgeRecommendationWithDetailsResponse
  extends HedgeRecommendationResponse {
  approvals: ApprovalResponse[];
}

export interface PaginatedHedgeRecommendationsResponse
  extends PaginatedResponse<HedgeRecommendationWithDetailsResponse> {}

export interface RecommendationApproveRequest {
  comments?: string;
}

export interface RecommendationRejectRequest {
  reason: string;
}

export interface RecommendationDeferRequest {
  reason: string;
}

// ============================================================
// Analytics Types
// ============================================================

export interface AnalyticsRunResponse {
  id: string;
  run_date: string;
  status: string;
  forecast_mape: number | string | null;
  var_95_usd: number | string | null;
  optimal_hr: number | string | null;
  basis_r2: number | string | null;
  pipeline_start_time: string | null;
  pipeline_end_time: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface AnalyticsRunSummaryResponse {
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
  avg_mape: number;
  avg_var: number;
  latest_run: AnalyticsRunResponse | null;
}

export interface DashboardSummaryResponse {
  current_var_usd: number;
  current_hedge_ratio: number;
  collateral_pct: number;
  mape_pct: number;
  var_reduction_pct: number;
  ifrs9_compliance_status: string;
  last_updated: string;
  agent_outputs?: AgentOutput[];
  r2_heating_oil?: number | null;
  total_notional_usd?: number | null;
}

export interface PaginatedAnalyticsRunsResponse
  extends PaginatedResponse<AnalyticsRunResponse> {}

export interface RunAnalyticsRequest {
  force_retrain?: boolean;
}

export interface TriggerAnalyticsResponse {
  status: string;
  message: string;
  run_id: string;
  triggered_at: string;
  note?: string;
}

export interface LoadCsvResponse {
  imported: number;
  updated: number;
  skipped: number;
  total: number;
}

// ============================================================
// Live Feed Types (SSE)
// ============================================================

export interface LivePriceFeedEvent {
  time: string;
  jet_fuel_spot: number;
  heating_oil_futures: number | null;
  brent_futures: number | null;  // Match backend
  wti_futures: number | null;     // Match backend
  crack_spread: number | null;
  volatility_index: number | null;
}
