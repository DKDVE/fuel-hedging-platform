import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api';

export interface ForecastDataPoint {
  date: string;
  actual: number | null;
  forecast: number;
  lower_bound: number;
  upper_bound: number;
}

export interface LatestForecastResponse {
  forecast_date?: string;
  model_version?: string;
  mape?: number;
  data_points: ForecastDataPoint[];
}

export function useLatestForecast() {
  return useQuery<LatestForecastResponse | null>({
    queryKey: ['forecast', 'latest'],
    queryFn: async () => {
      try {
        const response = await apiClient.get<LatestForecastResponse>('/analytics/forecast/latest');
        const data = response.data;
        if (!data?.data_points?.length) return null;
        return {
          data_points: data.data_points,
          mape: typeof data.mape === 'number' ? data.mape : undefined,
        };
      } catch {
        return null;
      }
    },
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}

export function useForecastHistory(days: number = 30) {
  return useQuery<ForecastDataPoint[]>({
    queryKey: ['forecast', 'history', days],
    queryFn: async () => {
      const response = await apiClient.get<LatestForecastResponse>('/analytics/forecast/history', {
        params: { days },
      });
      return response.data.data_points || [];
    },
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });
}
