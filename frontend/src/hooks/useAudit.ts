import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api';

export interface ApprovalRecord {
  id: string;
  recommendation_id: string;
  date: string | null;
  approver: string;
  role: string;
  decision: string;
  reason: string | null;
  response_time_mins: number;
}

export interface ApprovalsResponse {
  items: ApprovalRecord[];
}

export function useApprovals(days = 30) {
  return useQuery<ApprovalsResponse>({
    queryKey: ['audit', 'approvals', days],
    queryFn: async () => {
      const response = await apiClient.get<ApprovalsResponse>('/audit/approvals', {
        params: { days },
      });
      return response.data;
    },
    staleTime: 60_000,
  });
}
