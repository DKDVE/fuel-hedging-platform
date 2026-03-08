import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/api';

export interface ComplianceLimit {
  limit_name: string;
  current_value: number;
  limit_value: number;
  utilisation_pct: number;
  status: 'COMPLIANT' | 'WARNING' | 'BREACH' | 'NO_DATA';
  unit: string;
  display_current: string;
  display_limit: string;
}

export interface Ifrs9Position {
  position_id: string;
  instrument: string;
  proxy: string;
  notional_usd: number;
  hedge_ratio: number;
  r2_30d: number;
  r2_90d: number;
  retrospective_ratio: number;
  effectiveness_status: 'EFFECTIVE' | 'MONITOR' | 'INEFFECTIVE';
  designation_date: string;
  expiry_date: string;
}

export interface Ifrs9Section {
  overall_status: 'EFFECTIVE' | 'MONITOR' | 'INEFFECTIVE';
  positions_tested: number;
  positions_effective: number;
  last_test_date: string;
  next_test_due: string;
  days_until_next_test: number;
  positions: Ifrs9Position[];
}

export interface TradeReportingItem {
  requirement: string;
  description: string;
  status: string;
  last_reported?: string;
  next_due?: string;
  last_reconciled?: string;
  current_notional_usd?: number;
  threshold_usd?: number;
  open_disputes?: number;
  reference: string;
}

export interface ComplianceSummary {
  ifrs9: Ifrs9Section;
  internal_limits: {
    overall_status: 'COMPLIANT' | 'WARNING' | 'BREACH';
    limits: ComplianceLimit[];
  };
  trade_reporting: {
    framework: string;
    disclaimer: string;
    checklist: TradeReportingItem[];
  };
}

export function useComplianceSummary() {
  return useQuery<ComplianceSummary>({
    queryKey: ['compliance', 'summary'],
    queryFn: () => apiGet<ComplianceSummary>('/compliance/summary'),
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });
}
