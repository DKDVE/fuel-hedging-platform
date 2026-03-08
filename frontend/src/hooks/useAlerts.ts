import { useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api';

export interface Alert {
  id: string;
  alert_type: string;
  severity: string;
  title: string;
  message: string;
  metric_value: number | null;
  threshold_value: number | null;
  is_acknowledged: boolean;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  created_at: string;
}

export function useAlerts() {
  const queryClient = useQueryClient();

  const { data: alerts = [] } = useQuery<Alert[]>({
    queryKey: ['alerts', 'active'],
    queryFn: async () => {
      const response = await apiClient.get('/alerts?status=active&limit=20');
      return response.data;
    },
    refetchInterval: 60_000,
    staleTime: 30_000,
  });

  // Listen for new alerts via SSE (price stream also delivers alert events)
  useEffect(() => {
    const es = new EventSource('/api/v1/stream/prices', { withCredentials: true });
    const handler = () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    };
    es.addEventListener('alert', handler);
    return () => {
      es.removeEventListener('alert', handler);
      es.close();
    };
  }, [queryClient]);

  const unreadCount = alerts.filter((a) => !a.is_acknowledged).length;

  const acknowledgeMutation = useMutation({
    mutationFn: (id: string) => apiClient.patch(`/alerts/${id}/acknowledge`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  const acknowledge = (id: string) => acknowledgeMutation.mutate(id);

  return {
    alerts,
    unreadCount,
    acknowledge,
  };
}
