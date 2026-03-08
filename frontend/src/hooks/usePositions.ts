import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api';

export interface Position {
  id: string;
  instrument_type: string;
  proxy: string;
  notional_usd: number;
  hedge_ratio: number;
  entry_price: number;
  expiry_date: string;
  collateral_usd: number;
  ifrs9_r2: number;
  status: 'OPEN' | 'CLOSED' | 'EXPIRED';
  mtm_pnl_usd?: number;
  mtm_pnl_pct?: number;
  cash_savings_usd?: number;
  current_price?: number;
  price_change_usd?: number;
  is_profitable?: boolean;
}

export interface CollateralSummary {
  total_usd: number;
  reserves_usd: number;
  utilization_pct: number;
  limit_pct: number;
  available_capacity_usd: number;
}

export interface PortfolioPnl {
  total_mtm_pnl_usd: number;
  total_cash_savings_usd: number;
  avg_pnl_pct: number;
}

export interface PositionsResponse {
  items: Position[];
  collateral_summary: CollateralSummary;
  portfolio_pnl?: PortfolioPnl;
}

export function usePositions(includeClosed = true) {
  return useQuery<PositionsResponse>({
    queryKey: ['positions', includeClosed],
    queryFn: async () => {
      const response = await apiClient.get<PositionsResponse>('/positions', {
        params: { include_closed: includeClosed },
      });
      return response.data;
    },
    staleTime: 30_000,
  });
}
