import { useState, useEffect } from 'react';
import { KPICard } from '@/components/dashboard/KPICard';
import { LivePriceTicker } from '@/components/dashboard/LivePriceTicker';
import { ForecastChart } from '@/components/dashboard/ForecastChart';
import { AgentStatusGrid } from '@/components/dashboard/AgentStatusGrid';
import { useAnalyticsSummary, useLoadCsv, useTriggerAnalytics } from '@/hooks/useAnalytics';
import { usePendingRecommendations } from '@/hooks/useRecommendations';
import { useLatestForecast } from '@/hooks/useForecast';
import { useLivePrices } from '@/hooks/useLivePrices';
import { usePermissions } from '@/hooks/usePermissions';
import { useAuth } from '@/contexts/AuthContext';
import apiClient from '@/lib/api';
import { Link } from 'react-router-dom';
import { formatInt, formatMillions, formatRatio, formatPct } from '@/lib/formatters';
import { TrendingDown, Shield, DollarSign, Target, Play, Database, Pencil, Check, X, Fuel } from 'lucide-react';
import { toast } from 'sonner';

const VAR_LIMIT_USD = 5_000_000;

export function DashboardPage() {
  const { data: summary, isLoading: summaryLoading } = useAnalyticsSummary();
  const { data: pendingRecs, isLoading: _recoLoading } = usePendingRecommendations();
  const { data: forecastResponse, isLoading: forecastLoading } = useLatestForecast();
  const { user } = useAuth();
  const forecastData = forecastResponse?.data_points ?? [];
  const forecastMape = forecastResponse?.mape ?? null;
  const { prices, isConnected } = useLivePrices();
  const { hasPermission } = usePermissions();
  const triggerPipeline = useTriggerAnalytics();

  const canTriggerPipeline = hasPermission('trigger:pipeline');
  const canLoadCsv = hasPermission('read:analytics');
  const loadCsv = useLoadCsv();
  const [consumption, setConsumption] = useState(100_000);
  const [savedConsumption, setSavedConsumption] = useState(100_000);
  const consumptionChanged = consumption !== savedConsumption;
  const userRole = (user?.role as string | undefined)?.toLowerCase();
  const canEditConsumption =
    userRole === 'cfo' ||
    userRole === 'risk_manager' ||
    userRole === 'admin';

  useEffect(() => {
    apiClient.get('/analytics/config')
      .then((res: { data: Record<string, unknown> }) => {
        const val = res.data?.monthly_consumption_bbl;
        if (typeof val === 'number' && val > 0) {
          setConsumption(val);
          setSavedConsumption(val);
        }
      })
      .catch(() => {});
  }, []);

  const handleSaveConsumption = async () => {
    try {
      await apiClient.patch('/analytics/config', {
        key: 'monthly_consumption_bbl',
        value: consumption,
      });
      setSavedConsumption(consumption);
      toast.success('Monthly uplift saved');
    } catch {
      toast.error('Failed to save');
    }
  };

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
      {(userRole === 'cfo' || userRole === 'risk_manager') && (
        <div className="card border-l-4 border-blue-500 bg-blue-950/20 mb-2">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-blue-400 uppercase tracking-wide mb-1">
                Today's Position
              </p>
              <p className="text-base font-semibold text-white">
                {pendingRecs && pendingRecs.length > 0
                  ? `${pendingRecs.length} recommendation${pendingRecs.length > 1 ? 's' : ''} awaiting your approval`
                  : 'No pending decisions — portfolio is current'}
              </p>
              {hrNum > 0 && (
                <p className="text-sm text-slate-400 mt-0.5">
                  Currently hedging {formatRatio(hedgeRatio)} of fuel exposure
                  {mapeNum > 0 && ` · Forecast MAPE ${formatPct(mapeNum, 1)} vs 8% target`}
                </p>
              )}
            </div>
            {pendingRecs && pendingRecs.length > 0 && (
              <Link to="/recommendations" className="btn btn-primary text-sm shrink-0 ml-4">
                Review Now →
              </Link>
            )}
          </div>
        </div>
      )}

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
          trendValue={`${formatPct((collNum / 15) * 100, 0)} of limit used`}
          threshold={{
            value: 15.0,
            current: collNum,
            display: `${formatPct(collateralPct)} / ${formatPct(15)}`,
            type: collNum > 15 ? 'danger' : collNum > 12 ? 'warning' : 'success',
          }}
          icon={<DollarSign className="h-5 w-5" />}
          glowColor="from-amber-600"
        />

        <div title="Forecast MAPE target is <8%.">
          <KPICard
            title="Forecast MAPE"
            value={formatPct(mapeValue, 2)}
            trend={mapeNum < 8 ? 'down' : 'up'}
            trendValue={mapeNum < 8 ? `${formatPct(mapeNum, 1)} vs 8% industry avg` : 'Above target'}
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
      </div>

      <div className="card">
        {/* Header row */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Fuel className="h-5 w-5 text-blue-400" />
            <div>
              <h3 className="text-sm font-semibold text-white uppercase tracking-wide">
                Demand & Coverage
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Monthly fuel uplift vs. hedged position
              </p>
            </div>
          </div>
          {consumptionChanged && canEditConsumption && (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setConsumption(savedConsumption)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs rounded-lg font-medium transition-colors"
                title="Discard changes"
              >
                <X className="h-3.5 w-3.5" />
                Revert
              </button>
              <button
                onClick={handleSaveConsumption}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded-lg font-medium transition-colors"
              >
                <Check className="h-3.5 w-3.5" />
                Save
              </button>
            </div>
          )}
        </div>

        {/* Three KPI columns */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
          {/* Monthly Uplift */}
          <div className="bg-slate-800/60 rounded-xl p-4 border border-slate-700">
            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
              Monthly Uplift
            </p>
            <p className="text-2xl font-bold text-white">
              {formatInt(consumption)}
              <span className="text-sm font-normal text-slate-400 ml-1">bbl</span>
            </p>
            {canEditConsumption && (
              <p className="text-xs text-blue-400 mt-1 flex items-center gap-1">
                <Pencil className="h-3 w-3" />
                Adjust below
              </p>
            )}
          </div>

          {/* Hedged Volume */}
          <div className="bg-green-950/30 rounded-xl p-4 border border-green-800/40">
            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
              Hedged Volume
            </p>
            <p className="text-2xl font-bold text-green-400">
              {formatInt(Math.round(consumption * hrNum))}
              <span className="text-sm font-normal text-slate-400 ml-1">bbl</span>
            </p>
            <p className="text-xs text-green-600 mt-1">
              {formatRatio(hedgeRatio)} of uplift
            </p>
          </div>

          {/* Unhedged Volume */}
          <div className="bg-amber-950/20 rounded-xl p-4 border border-amber-800/30">
            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
              Unhedged Volume
            </p>
            <p className="text-2xl font-bold text-amber-400">
              {formatInt(Math.round(consumption * (1 - hrNum)))}
              <span className="text-sm font-normal text-slate-400 ml-1">bbl</span>
            </p>
            <p className="text-xs text-amber-600 mt-1">
              {formatRatio(typeof hedgeRatio === 'number' ? 1 - hrNum : null)} exposed
            </p>
          </div>
        </div>

        {/* Coverage bar */}
        <div className="mb-5">
          <div className="flex justify-between text-xs text-slate-500 mb-1.5">
            <span>0 bbl</span>
            <span className="text-slate-300 font-medium">
              {formatRatio(hedgeRatio)} hedged
            </span>
            <span>{formatInt(consumption)} bbl</span>
          </div>
          <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-green-600 to-green-400 rounded-full transition-all duration-300"
              style={{ width: `${Math.min(hrNum * 100, 100)}%` }}
            />
          </div>
        </div>

        {/* Slider — CFO/Risk Manager/Admin only */}
        {canEditConsumption && (
          <div className="border-t border-slate-700 pt-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-slate-400">
                Adjust monthly uplift forecast
              </p>
              <span className="text-xs font-mono text-blue-300">
                {formatInt(consumption)} bbl
              </span>
            </div>
            <input
              type="range"
              min={10_000}
              max={500_000}
              step={5_000}
              value={consumption}
              onChange={(e) => setConsumption(Number(e.target.value))}
              className="w-full h-2 rounded-lg appearance-none cursor-pointer bg-slate-700 accent-blue-500"
            />
            <div className="flex justify-between text-xs text-slate-600 mt-1">
              <span>10k</span>
              <span>250k</span>
              <span>500k</span>
            </div>
          </div>
        )}
      </div>
 
      {/* Forecast Chart */}
      <ForecastChart
        data={forecastData || []}
        isLoading={forecastLoading}
        fromAnalytics={(forecastData?.length ?? 0) > 0}
        mapeFromApi={forecastMape}
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
