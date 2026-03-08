import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api';

export interface StressScenario {
  id: string;
  name: string;
  description: string;
  price_shock_pct: number;
  vol_multiplier: number;
  duration_days: number;
  historical_reference: string;
  color: string;
}

export interface ScenarioRunResult {
  scenario_id: string;
  scenario_name: string;
  current_price: number;
  stressed_price: number;
  price_change_pct: number;
  optimizer_result: {
    optimal_hr: number;
    instrument_mix: Record<string, number>;
    collateral_usd: number;
    collateral_pct_of_reserves: number;
    solver_converged: boolean;
  };
  var_impact: {
    stressed_var_usd: number | null;
    normal_var_usd: number | null;
  };
  risk_narrative: string;
  constraints_satisfied: boolean;
}

export function useStressScenarios() {
  const queryClient = useQueryClient();
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);

  const { data: scenarios = [] } = useQuery<StressScenario[]>({
    queryKey: ['analytics', 'scenarios'],
    queryFn: async () => {
      const response = await apiClient.get('/analytics/scenarios');
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
  });

  const runMutation = useMutation({
    mutationFn: async (scenarioId: string) => {
      const response = await apiClient.post(`/analytics/scenarios/${scenarioId}/run`);
      return response.data as ScenarioRunResult;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analytics', 'scenarios'] });
    },
  });

  const runScenario = (scenarioId: string) => runMutation.mutateAsync(scenarioId);

  const selectedScenarioData = scenarios.find((s) => s.id === selectedScenario);

  // Clear stale result when user switches to a different scenario
  useEffect(() => {
    runMutation.reset();
  }, [selectedScenario, runMutation]);

  return {
    scenarios,
    selectedScenario,
    setSelectedScenario,
    selectedScenarioData,
    runScenario,
    result: runMutation.data,
    isRunning: runMutation.isPending,
    error: runMutation.error,
  };
}
