import { KPICard } from '@/components/dashboard/KPICard';
import { LivePriceTicker } from '@/components/dashboard/LivePriceTicker';
import { ForecastChart } from '@/components/dashboard/ForecastChart';
import { AgentStatusGrid } from '@/components/dashboard/AgentStatusGrid';
import { useAnalyticsSummary, useLoadCsv, useTriggerAnalytics } from '@/hooks/useAnalytics';
import { usePendingRecommendations } from '@/hooks/useRecommendations';
import { useLatestForecast } from '@/hooks/useForecast';
import { useLivePrices } from '@/hooks/useLivePrices';
import { usePermissions } from '@/hooks/usePermissions';
import { Link } from 'react-router-dom';
import { formatMillions, formatRatio, formatPct } from '@/lib/formatters';
import { TrendingDown, Shield, DollarSign, Target, Play, Database } from 'lucide-react';
import { toast } from 'sonner';

const VAR_LIMIT_USD = 5_000_000;

export function DashboardPage() {
  const { data: summary, isLoading: summaryLoading } = useAnalyticsSummary();
  const { data: pendingRecs, isLoading: _recoLoading } = usePendingRecommendations();
  const { data: forecastData, isLoading: forecastLoading } = useLatestForecast();
  const { prices, isConnected } = useLivePrices();
  const { hasPermission } = usePermissions();
  const triggerPipeline = useTriggerAnalytics();

  const canTriggerPipeline = hasPermission('trigger:pipeline');
  const canLoadCsv = hasPermission('read:analytics');
  const loadCsv = useLoadCsv();

  const handleLoadCsv = async () => {
    if (loadCsv.isPending) return;
    try {
      const result = await loadCsv.mutateAsync();
      toast.success(
        `Loaded ${result.imported} new records, updated ${result.updated}. Total: ${result.total} rows.`
      );
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      const msg =
        (err.response?.data as { detail?: string })?.detail ||
        (err as Error)?.message ||
        'Failed to load CSV.';
      toast.error(msg);
    }
  };

  const handleRunPipeline = async () => {
    if (triggerPipeline.isPending) return;
    try {
      await triggerPipeline.mutateAsync();
      toast.success(
        'Pipeline started. Wait ~8 minutes for analytics to complete, then refresh the page to see charts and KPIs.'
      );
      setTimeout(() => {
        triggerPipeline.reset();
      }, 500);
    } catch (error: unknown) {
      const err = error as { response?: { status?: number; data?: { detail?: string } } };
      if (err.response?.status === 403) {
        toast.error('You do not have permission to trigger the pipeline.');
      } else if (err.response?.status === 409) {
        toast.error('Pipeline is already running. Please wait.');
      } else {
        const msg =
          (err.response?.data as { detail?: string })?.detail ||
          (err as Error)?.message ||
          'Failed to start pipeline. Check the logs.';
        toast.error(msg);
      }
    }
  };

  if (summaryLoading) {
    return (
      <div className="p-8">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      </div>
    );
  }

  // KPI values from summary (use formatters to avoid NaN/Infinity display)
  const varValue = summary?.current_var_usd ?? null;
  const hedgeRatio = summary?.current_hedge_ratio ?? null;
  const collateralPct = summary?.collateral_pct ?? null;
  const mapeValue = summary?.mape_pct ?? null;

  const varNum = typeof varValue === 'number' ? varValue : 0;
  const hrNum = typeof hedgeRatio === 'number' ? hedgeRatio : 0;
  const collNum = typeof collateralPct === 'number' ? collateralPct : 0;
  const mapeNum = typeof mapeValue === 'number' ? mapeValue : 0;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Dashboard</h1>
          <p className="text-slate-400">
            Real-time fuel hedging analytics and risk monitoring
          </p>
        </div>
        <div className="flex items-center gap-2">
          {canLoadCsv && (
            <button
              className="btn btn-secondary flex items-center gap-2"
              title="Load historical fuel data from CSV"
              onClick={handleLoadCsv}
              disabled={loadCsv.isPending}
            >
              <Database className="h-4 w-4" />
              {loadCsv.isPending ? 'Loading...' : 'Load CSV'}
            </button>
          )}
          {canTriggerPipeline && (
            <button
              className="btn btn-primary flex items-center gap-2"
              title="Trigger optimization pipeline"
              onClick={handleRunPipeline}
              disabled={triggerPipeline.isPending}
            >
              <Play className="h-4 w-4" />
              {triggerPipeline.isPending ? 'Running...' : 'Run Pipeline'}
            </button>
          )}
        </div>
      </div>

      {/* Live Price Ticker */}
      <LivePriceTicker prices={prices} isConnected={isConnected} />

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        <KPICard
          title="Value at Risk"
          value={formatMillions(varValue)}
          trend={varNum < VAR_LIMIT_USD ? 'down' : 'up'}
          trendValue={`${formatMillions(varValue)} / ${formatMillions(VAR_LIMIT_USD)} limit`}
          threshold={{
            value: VAR_LIMIT_USD,
            current: varNum,
            display: `${formatMillions(varValue)} / ${formatMillions(VAR_LIMIT_USD)} limit`,
            type: varNum > VAR_LIMIT_USD ? 'danger' : varNum > 4_000_000 ? 'warning' : 'success',
          }}
          icon={<TrendingDown className="h-5 w-5" />}
          glowColor="from-red-600"
        />

        <KPICard
          title="Hedge Ratio"
          value={formatRatio(hedgeRatio)}
          trend={hrNum > 0.70 ? 'up' : 'neutral'}
          trendValue={hrNum > 0.70 ? 'Approaching cap' : 'Within range'}
          threshold={{
            value: 0.80,
            current: hrNum,
            display: `${formatRatio(hedgeRatio)} / ${formatRatio(0.80)}`,
            type: hrNum > 0.80 ? 'danger' : hrNum > 0.70 ? 'warning' : 'success',
          }}
          icon={<Shield className="h-5 w-5" />}
          glowColor="from-amber-600"
        />

        <KPICard
          title="Collateral"
          value={formatPct(collateralPct)}
          trend={collNum > 12 ? 'up' : 'neutral'}
          trendValue={`${formatPct((collNum / 15) * 100, 0)} of reserves`}
          threshold={{
            value: 15.0,
            current: collNum,
            display: `${formatPct(collateralPct)} / ${formatPct(15)}`,
            type: collNum > 15 ? 'danger' : collNum > 12 ? 'warning' : 'success',
          }}
          icon={<DollarSign className="h-5 w-5" />}
          glowColor="from-amber-600"
        />

        <KPICard
          title="Forecast Accuracy"
          value={formatPct(mapeValue, 2)}
          trend={mapeNum < 8 ? 'down' : 'up'}
          trendValue={mapeNum < 8 ? 'On target' : 'Above target'}
          threshold={{
            value: 8.0,
            current: mapeNum,
            display: `${formatPct(mapeValue, 2)} / ${formatPct(8)}`,
            type: mapeNum > 10 ? 'danger' : mapeNum > 8 ? 'warning' : 'success',
          }}
          icon={<Target className="h-5 w-5" />}
          glowColor="from-green-600"
        />
      </div>

      {/* Forecast Chart */}
      <ForecastChart
          data={forecastData || []}
          isLoading={forecastLoading}
          fromAnalytics={(forecastData?.length ?? 0) > 0}
        />

      {/* Agent Status Grid */}
      <AgentStatusGrid agents={summary?.agent_outputs || []} isLoading={summaryLoading} />

      {/* Pending Recommendations Alert */}
      {pendingRecs && pendingRecs.length > 0 && (
        <div className="card border-amber-600 bg-amber-950/20">
          <div className="flex items-start gap-4">
            <div className="p-2 bg-amber-600 rounded-lg">
              <Shield className="h-5 w-5 text-white" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-white mb-1">
                {pendingRecs.length} Pending Recommendation{pendingRecs.length > 1 ? 's' : ''}
              </h3>
              <p className="text-slate-400 mb-4">
                Review and approve hedge strategies to manage fuel price risk.
              </p>
              <Link
                to="/recommendations"
                className="btn btn-secondary inline-block"
              >
                Review Recommendations →
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
