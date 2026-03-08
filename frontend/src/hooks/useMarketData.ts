import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api';
import type { PriceTickSeriesResponse } from '@/types/api';

export function useMarketData(start?: string, end?: string) {
  return useQuery<PriceTickSeriesResponse>({
    queryKey: ['market-data', start, end],
    queryFn: async () => {
      const response = await apiClient.get('/market-data/history', {
        params: { start_date: start, end_date: end, limit: 500 },
      });
      const data = response.data as {
        items?: Array<{
          time: string;
          jet_fuel_spot: number;
          heating_oil_futures: number;
          brent_crude_futures?: number;
          wti_crude_futures?: number;
          brent_futures?: number;
          wti_futures?: number;
          crack_spread?: number;
          volatility_index?: number;
        }>;
        total?: number;
        start_date?: string;
        end_date?: string;
      };
      const items = data.items ?? [];
      const ticks = items.map((t) => ({
        id: '',
        time: typeof t.time === 'string' ? t.time : new Date(t.time).toISOString(),
        jet_fuel_spot: t.jet_fuel_spot,
        heating_oil_futures: t.heating_oil_futures ?? null,
        brent_futures: t.brent_futures ?? t.brent_crude_futures ?? null,
        wti_futures: t.wti_futures ?? t.wti_crude_futures ?? null,
        crack_spread: t.crack_spread ?? null,
        volatility_index: t.volatility_index ?? null,
        source: 'api',
        created_at: typeof t.time === 'string' ? t.time : new Date(t.time).toISOString(),
      }));
      return {
        ticks,
        start: data.start_date ?? start ?? '',
        end: data.end_date ?? end ?? '',
        count: data.total ?? ticks.length,
      };
    },
    staleTime: 60_000,
  });
}

export function useLatestPrice() {
  return useQuery<PriceTickSeriesResponse>({
    queryKey: ['market-data', 'latest'],
    queryFn: async () => {
      const response = await apiClient.get('/market-data/latest');
      return response.data;
    },
    refetchInterval: 60000, // Refetch every minute
  });
}
