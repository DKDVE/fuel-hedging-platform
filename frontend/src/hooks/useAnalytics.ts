import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient, { apiPost } from '@/lib/api';
import type {
  AnalyticsRunResponse,
  DashboardSummaryResponse,
  LoadCsvResponse,
  PaginatedAnalyticsRunsResponse,
  TriggerAnalyticsResponse,
} from '@/types/api';

interface VarDataPoint {
  date: string;
  dynamic_var: number;
  static_var: number;
  retraining_date?: boolean;
}

interface MapeDataPoint {
  date: string;
  mape: number;
}

interface VarWalkForwardResponse {
  data_points: VarDataPoint[];
  summary: {
    avg_dynamic_var: number;
    avg_static_var: number;
    improvement_pct: number;
  };
}

interface MapeHistoryResponse {
  data_points: MapeDataPoint[];
  target_threshold: number;
  alert_threshold: number;
  summary: {
    avg_mape: number;
    min_mape: number;
    max_mape: number;
    within_target_pct: number;
    violations: number;
  };
}

interface ForecastDataPoint {
  date: string;
  actual: number | null;
  forecast: number | null;
  lower_bound: number | null;
  upper_bound: number | null;
}

interface ForecastResponse {
  forecast_values: ForecastDataPoint[];
  model_type: string;
  forecast_mape: number;
  generated_at: string;
}

export function useAnalyticsSummary() {
  return useQuery<DashboardSummaryResponse>({
    queryKey: ['analytics', 'summary'],
    queryFn: async () => {
      const response = await apiClient.get('/analytics/summary');
      return response.data;
    },
    staleTime: 60_000,
    retry: 2,
  });
}

export function useAnalyticsHistory(page: number = 1, limit: number = 20) {
  return useQuery<PaginatedAnalyticsRunsResponse>({
    queryKey: ['analytics', 'history', page, limit],
    queryFn: async () => {
      const response = await apiClient.get('/analytics', {
        params: { page, limit },
      });
      return response.data;
    },
    staleTime: 60_000,
  });
}

export function useAnalyticsRun(runId: string) {
  return useQuery<AnalyticsRunResponse>({
    queryKey: ['analytics', 'run', runId],
    queryFn: async () => {
      const response = await apiClient.get(`/analytics/${runId}`);
      return response.data;
    },
    enabled: !!runId,
    staleTime: 60_000,
  });
}

export function useTriggerAnalytics() {
  const queryClient = useQueryClient();

  return useMutation<TriggerAnalyticsResponse, Error, void>({
    mutationFn: async () => {
      const data = await apiPost<TriggerAnalyticsResponse>('/analytics/trigger', {});
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
    },
  });
}

export function useLoadCsv() {
  const queryClient = useQueryClient();

  return useMutation<LoadCsvResponse, Error, void>({
    mutationFn: async () => {
      const data = await apiPost<LoadCsvResponse>('/analytics/load-csv');
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
      queryClient.invalidateQueries({ queryKey: ['forecast'] });
    },
  });
}

export function useVarWalkForward(days: number = 90) {
  return useQuery<VarWalkForwardResponse>({
    queryKey: ['analytics', 'var-walk-forward', days],
    queryFn: async () => {
      const response = await apiClient.get('/analytics/var-walk-forward', {
        params: { days },
      });
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useMapeHistory(days: number = 180) {
  return useQuery<MapeHistoryResponse>({
    queryKey: ['analytics', 'mape-history', days],
    queryFn: async () => {
      const response = await apiClient.get('/analytics/mape-history', {
        params: { days },
      });
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useLatestForecast() {
  return useQuery<ForecastResponse>({
    queryKey: ['analytics', 'forecast', 'latest'],
    queryFn: async () => {
      const response = await apiClient.get('/analytics/forecast/latest');
      return response.data;
    },
    staleTime: 10 * 60 * 1000, // 10 minutes - forecast doesn't change often
  });
}

export interface BacktestSummary {
  total_weeks: number;
  profitable_weeks: number;
  total_savings_usd: number;
  avg_weekly_savings_usd: number;
  max_weekly_savings_usd: number;
  max_weekly_loss_usd: number;
  savings_volatility: number;
  sharpe_ratio: number;
  avg_mape: number;
  avg_r2_heating_oil: number;
  var_reduction_achieved: number;
  h1_validated: boolean;
  h4_validated: boolean;
}

export interface WeeklyBacktestResult {
  week_date: string;
  optimal_hr: number;
  jet_fuel_spot: number;
  hedged_cost_per_bbl: number;
  unhedged_cost_per_bbl: number;
  weekly_savings_usd: number;
  cumulative_savings_usd: number;
  mape_at_date: number;
  r2_at_date: number;
  hedge_effectiveness: string;
}

export interface BacktestLatestResponse {
  summary: BacktestSummary | null;
  weekly_results: WeeklyBacktestResult[];
  computed_at: string | null;
  notional_usd: number | null;
}

export function useBacktestLatest() {
  return useQuery<BacktestLatestResponse>({
    queryKey: ['analytics', 'backtest', 'latest'],
    queryFn: async () => {
      const response = await apiClient.get('/analytics/backtest/latest');
      return response.data;
    },
    staleTime: 10 * 60 * 1000,
  });
}
