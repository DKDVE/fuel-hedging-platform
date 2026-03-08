import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api';
import type {
  HedgeRecommendationWithDetailsResponse,
  PaginatedHedgeRecommendationsResponse,
  RecommendationApproveRequest,
  RecommendationRejectRequest,
  RecommendationDeferRequest,
} from '@/types/api';

export function useRecommendations(page: number = 1, limit: number = 10) {
  return useQuery<PaginatedHedgeRecommendationsResponse>({
    queryKey: ['recommendations', page, limit],
    queryFn: async () => {
      const response = await apiClient.get('/recommendations', {
        params: { page, limit },
      });
      return response.data;
    },
  });
}

export function usePendingRecommendations() {
  return useQuery<HedgeRecommendationWithDetailsResponse[]>({
    queryKey: ['recommendations', 'pending'],
    queryFn: async () => {
      const response = await apiClient.get('/recommendations/pending');
      return response.data;
    },
    staleTime: 30_000,
    retry: false,
  });
}

export function useRecommendation(id: string) {
  return useQuery<HedgeRecommendationWithDetailsResponse>({
    queryKey: ['recommendation', id],
    queryFn: async () => {
      const response = await apiClient.get(`/recommendations/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useApproveRecommendation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string;
      data: RecommendationApproveRequest;
    }) => {
      const response = await apiClient.post(
        `/recommendations/${id}/approve`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
    },
  });
}

export function useRejectRecommendation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string;
      data: RecommendationRejectRequest;
    }) => {
      const response = await apiClient.post(
        `/recommendations/${id}/reject`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
    },
  });
}

export function useDeferRecommendation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string;
      data: RecommendationDeferRequest;
    }) => {
      const response = await apiClient.post(
        `/recommendations/${id}/defer`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
    },
  });
}
