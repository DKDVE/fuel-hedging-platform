import { useState, useEffect } from 'react';
import { KPICard } from '@/components/dashboard/KPICard';
import { LivePriceTicker } from '@/components/dashboard/LivePriceTicker';
import { ForecastChart } from '@/components/dashboard/ForecastChart';
import { AgentStatusGrid } from '@/components/dashboard/AgentStatusGrid';
import { HedgeCostSimulator } from '@/components/dashboard/HedgeCostSimulator';
import { HedgeEffectivenessGauge } from '@/components/dashboard/HedgeEffectivenessGauge';
import { PeerBenchmarkStrip } from '@/components/dashboard/PeerBenchmarkStrip';
import { useAnalyticsSummary, useLoadCsv, useTriggerAnalytics } from '@/hooks/useAnalytics';
import { usePendingRecommendations } from '@/hooks/useRecommendations';
import { useLatestForecast } from '@/hooks/useForecast';
import { useLivePrices } from '@/hooks/useLivePrices';
import { usePermissions } from '@/hooks/usePermissions';
import { useAuth } from '@/contexts/AuthContext';
import apiClient from '@/lib/api';
import { Link } from 'react-router-dom';
import { formatInt, formatMillions, formatRatio, formatPct } from '@/lib/formatters';
import { TrendingDown, Shield, DollarSign, Target, Play, Database, Pencil, Check, X, Sparkles } from 'lucide-react';
import { toast } from 'sonner';

const VAR_LIMIT_USD = 5_000_000;
const INSTRUMENT_KEYS = ['futures', 'options', 'collars', 'swaps'] as const;

interface WhatIfResult {
  what_if: {
    hedge_ratio: number;
    instrument_mix: Record<string, number>;
    var_usd: number;
    collateral_usd: number;
    collateral_pct_of_reserves: number;
    solver_converged: boolean;
  };
  comparison: {
    original_var_hedged: number;
    what_if_var: number;
    var_difference: number;
    var_better: boolean;
    collateral_delta_usd: number;
    monthly_saving_vs_unhedged: number;
  };
  verdict: string;
  narrative?: string;
  source?: 'n8n_gpt' | 'fallback';
}

function buildMixFromSelection(instruments: Set<string>): Record<string, number> {
  const share = 1 / instruments.size;
  return Object.fromEntries(INSTRUMENT_KEYS.map((k) => [k, instruments.has(k) ? share : 0]));
}

function getInstrumentNote(instruments: Set<string>): string {
  const has = (i: string) => instruments.has(i);
  if (instruments.size === 1) {
    if (has('futures')) return 'Locks price today. Requires daily margin. Best for near-term.';
    if (has('options')) return 'Caps max cost. Pay premium upfront. Best when expecting volatility.';
    if (has('collars')) return 'Zero-cost structure. Caps upside, floors downside.';
    if (has('swaps')) return 'Monthly average settlement. No exchange margin needed.';
  }
  if (has('futures') && has('options') && instruments.size === 2) {
    return 'Core coverage via futures with spike protection via options.';
  }
  if (has('futures') && has('collars') && instruments.size === 2) {
    return 'Industry standard combination. IAG, Lufthansa pattern.';
  }
  if (instruments.size >= 3) {
    return 'Diversified portfolio approach. Maximises IFRS 9 flexibility.';
  }
  return 'Combined instrument strategy.';
}

function getSeasonalMultiplier(): { multiplier: number; quarter: string; label: string } {
  const month = new Date().getMonth();
  const defaults = { q1: 0.85, q2: 0.90, q3: 1.10, q4: 1.15 };
  let stored = defaults;
  try {
    const raw = localStorage.getItem('aerohedge_seasonal');
    if (raw) {
      stored = { ...defaults, ...JSON.parse(raw) };
    }
  } catch {
    // use defaults
  }

  if (month <= 2) return { multiplier: stored.q1, quarter: 'Q1', label: 'Jan–Mar shoulder season' };
  if (month <= 5) return { multiplier: stored.q2, quarter: 'Q2', label: 'Apr–Jun shoulder season' };
  if (month <= 8) return { multiplier: stored.q3, quarter: 'Q3', label: 'Jul–Sep summer peak' };
  return { multiplier: stored.q4, quarter: 'Q4', label: 'Oct–Dec holiday peak' };
}

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
  const [safPct, setSafPct] = useState(0);
  const [targetHR, setTargetHR] = useState(60);
  const [selectedInstruments, setSelectedInstruments] = useState<Set<string>>(new Set(['futures']));
  const [aiResult, setAiResult] = useState<WhatIfResult | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
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

  const handleToggleInstrument = (instrument: string) => {
    if (!canEditConsumption) return;
    setSelectedInstruments((prev) => {
      const next = new Set(prev);
      if (next.has(instrument)) {
        if (next.size === 1) {
          toast.error('At least one instrument must remain selected.');
          return prev;
        }
        next.delete(instrument);
      } else {
        next.add(instrument);
      }
      return next;
    });
  };

  const handleGetAiRecommendation = async () => {
    if (aiLoading) return;
    setAiResult(null);
    setAiLoading(true);
    try {
      const response = await apiClient.post<WhatIfResult>('/analytics/demand-strategy', {
        hedge_ratio: targetHR / 100,
        consumption_bbl: consumption,
        instruments: Array.from(selectedInstruments),
        instrument_mix: buildMixFromSelection(selectedInstruments),
        original_var_hedged: summary?.current_var_usd ?? 0,
        original_var_unhedged: (summary?.current_var_usd ?? 0) * 1.42,
      });
      setAiResult(response.data);
    } catch {
      toast.error('Failed to get AI recommendation.');
    } finally {
      setAiLoading(false);
    }
  };

  // KPI values from summary (use formatters to avoid NaN/Infinity display)
  const varValue = summary?.current_var_usd ?? null;
  const hedgeRatio = summary?.current_hedge_ratio ?? null;
  const collateralPct = summary?.collateral_pct ?? null;
  const mapeValue = summary?.mape_pct ?? null;

  const varNum = typeof varValue === 'number' ? varValue : 0;
  const hrNum = typeof hedgeRatio === 'number' ? hedgeRatio : 0;
  const collNum = typeof collateralPct === 'number' ? collateralPct : 0;
  const mapeNum = typeof mapeValue === 'number' ? mapeValue : 0;
  const hedgeableBbl = Math.round(consumption * (1 - safPct / 100));
  const safBbl = consumption - hedgeableBbl;
  const hedgedBbl = Math.round(hedgeableBbl * (targetHR / 100));
  const unhedgedBbl = hedgeableBbl - hedgedBbl;
  const latestPrice = prices.length > 0 ? prices[prices.length - 1] : null;
  const currentPrice = latestPrice?.jet_fuel_spot ?? 9.52;
  const monthlyCostImpact = currentPrice * 42 * unhedgedBbl;

  useEffect(() => {
    if (hrNum > 0) setTargetHR(Math.round(hrNum * 100));
  }, [hrNum]);

  if (summaryLoading) {
    return (
      <div className="p-8">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      </div>
    );
  }

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

        <div className="col-span-2 md:col-span-4">
          <HedgeEffectivenessGauge />
        </div>
      </div>

      <PeerBenchmarkStrip ourHR={hrNum} />

      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-white uppercase tracking-wide">
              Hedge Strategy Builder
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Configure target ratio and instrument mix with live impact estimates
            </p>
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

        <div className="border-t border-slate-700 pt-4 space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-400">Adjust monthly uplift forecast</p>
            <span className="text-xs font-mono text-blue-300">{formatInt(consumption)} bbl</span>
          </div>
          <input
            type="range"
            min={10_000}
            max={500_000}
            step={5_000}
            value={consumption}
            onChange={(e) => canEditConsumption && setConsumption(Number(e.target.value))}
            disabled={!canEditConsumption}
            className="w-full h-2 rounded-lg appearance-none cursor-pointer bg-slate-700 accent-blue-500 disabled:opacity-60 disabled:cursor-not-allowed"
          />
          <div className="flex justify-between text-xs text-slate-600 mt-1">
            <span>10k</span>
            <span>250k</span>
            <span>500k</span>
          </div>

          {(() => {
            const s = getSeasonalMultiplier();
            const adjustedBbl = Math.round(consumption * s.multiplier);
            const diff = adjustedBbl - consumption;
            return (
              <div className="rounded-lg bg-slate-800/40 border border-slate-700 p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-slate-300 font-medium">
                      🗓 Seasonal Adjustment — {s.quarter} ({s.label})
                    </p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Seasonal multiplier: {(s.multiplier * 100).toFixed(0)}% of base
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-mono font-bold text-white">
                      {adjustedBbl.toLocaleString()} bbl
                    </p>
                    <p
                      className={`text-xs font-mono ${
                        diff > 0 ? 'text-amber-400' : diff < 0 ? 'text-blue-400' : 'text-slate-400'
                      }`}
                    >
                      {diff > 0 ? '+' : ''}{diff.toLocaleString()} vs base
                    </p>
                  </div>
                </div>
                {Math.abs(diff) > 5_000 && (
                  <p className="text-xs text-slate-500 mt-2 border-t border-slate-700 pt-2">
                    Consider adjusting your hedge volume to {adjustedBbl.toLocaleString()} bbl
                    to align with seasonal demand. Update base uplift in Settings.
                  </p>
                )}
              </div>
            );
          })()}

          {canEditConsumption && (
            <div className="flex items-center justify-between py-2 border-t border-slate-700">
              <div>
                <p className="text-xs text-slate-300 font-medium">SAF Component</p>
                <p className="text-xs text-slate-500">
                  SAF volumes are not hedgeable via standard instruments
                </p>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min={0}
                  max={30}
                  step={5}
                  value={safPct}
                  onChange={(e) => setSafPct(Number(e.target.value))}
                  className="w-24 h-2 rounded-lg appearance-none cursor-pointer bg-slate-700 accent-green-500"
                />
                <span className="text-xs font-mono text-green-400 w-8">{safPct}%</span>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between pt-2 border-t border-slate-700">
            <div>
              <p className="text-xs text-slate-300 font-medium">Target Hedge Ratio</p>
              <p className="text-xs text-slate-500 mt-0.5">(System recommends: {formatRatio(hedgeRatio)})</p>
            </div>
            <span className="text-xs font-mono text-blue-300">{targetHR}%</span>
          </div>
          <input
            type="range"
            min={30}
            max={80}
            step={1}
            value={targetHR}
            onChange={(e) => canEditConsumption && setTargetHR(Number(e.target.value))}
            disabled={!canEditConsumption}
            className="w-full h-2 rounded-lg appearance-none cursor-pointer bg-slate-700 accent-blue-500 disabled:opacity-60 disabled:cursor-not-allowed"
          />
        </div>

        <div className="border-t border-slate-700 pt-4">
          <p className="text-xs text-slate-300 font-medium mb-2">Instrument Selection</p>
          <div className="flex flex-wrap gap-2">
            {INSTRUMENT_KEYS.map((instrument) => {
              const active = selectedInstruments.has(instrument);
              const label = instrument.charAt(0).toUpperCase() + instrument.slice(1);
              return (
                <button
                  key={instrument}
                  type="button"
                  disabled={!canEditConsumption}
                  onClick={() => handleToggleInstrument(instrument)}
                  className={`px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors disabled:opacity-60 disabled:cursor-not-allowed ${
                    active
                      ? 'border-blue-500 bg-blue-950 text-blue-300'
                      : 'border-slate-600 bg-slate-900 text-slate-400 hover:border-slate-400'
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
          <p className="text-xs text-slate-500 mt-2">{getInstrumentNote(selectedInstruments)}</p>
          {safPct > 0 && (
            <span className="inline-block text-xs bg-green-900/40 text-green-400 border border-green-800/40 rounded-full px-2 py-0.5 mt-2">
              🌿 {safPct}% SAF — not hedged via derivatives
            </span>
          )}
        </div>

        <div className="border-t border-slate-700 pt-4 mt-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="bg-slate-800/60 rounded-xl p-4 border border-slate-700">
              <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Monthly Uplift</p>
              <p className="text-2xl font-bold text-white">
                {formatInt(consumption)}
                <span className="text-sm font-normal text-slate-400 ml-1">bbl</span>
              </p>
              {canEditConsumption && (
                <p className="text-xs text-blue-400 mt-1 flex items-center gap-1">
                  <Pencil className="h-3 w-3" />
                  Adjust above
                </p>
              )}
            </div>
            <div className="bg-green-950/30 rounded-xl p-4 border border-green-800/40">
              <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Hedgeable Volume</p>
              <p className="text-2xl font-bold text-green-400">
                {formatInt(hedgeableBbl)}
                <span className="text-sm font-normal text-slate-400 ml-1">bbl</span>
              </p>
              <p className="text-xs text-green-600 mt-1">{safPct > 0 ? `(excl. ${formatInt(safBbl)} bbl SAF)` : ''}</p>
            </div>
            <div className="bg-blue-950/20 rounded-xl p-4 border border-blue-800/30">
              <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Hedged Volume</p>
              <p className="text-2xl font-bold text-blue-300">
                {formatInt(hedgedBbl)}
                <span className="text-sm font-normal text-slate-400 ml-1">bbl</span>
              </p>
              <p className="text-xs text-blue-500 mt-1">{targetHR}% of hedgeable volume</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
            <div className="bg-amber-950/20 rounded-xl p-4 border border-amber-800/30">
              <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Unhedged Volume</p>
              <p className="text-2xl font-bold text-amber-400">
                {formatInt(unhedgedBbl)}
                <span className="text-sm font-normal text-slate-400 ml-1">bbl</span>
              </p>
              <p className="text-xs text-amber-600 mt-1">(remaining)</p>
            </div>
            <div className="bg-red-950/20 rounded-xl p-4 border border-red-800/30">
              <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Monthly Cost Impact</p>
              <p className="text-2xl font-bold text-red-300">{formatMillions(monthlyCostImpact)}/month</p>
              <p className="text-xs text-red-500 mt-1">Unhedged exposure/month at current price</p>
            </div>
          </div>

          <div className="mb-3">
            <div className="flex justify-between text-xs text-slate-500 mb-1.5">
              <span>0 bbl</span>
              <span className="text-slate-300 font-medium">{targetHR}% target hedged</span>
              <span>{formatInt(hedgeableBbl)} bbl</span>
            </div>
            <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-green-600 to-green-400 rounded-full transition-all duration-300"
                style={{ width: `${Math.min(targetHR, 100)}%` }}
              />
            </div>
            {targetHR !== Math.round(hrNum * 100) && (
              <p className="text-xs text-amber-400 mt-1">
                ⚠ Your target ({targetHR}%) differs from system recommendation ({formatRatio(hedgeRatio)})
              </p>
            )}
          </div>

          {targetHR > 65 && (
            <div className={`rounded-lg p-3 border mt-3 ${targetHR >= 75 ? 'bg-red-950/30 border-red-800/50' : 'bg-amber-950/20 border-amber-800/30'}`}>
              <p className={`text-xs font-semibold mb-1 ${targetHR >= 75 ? 'text-red-400' : 'text-amber-400'}`}>
                {targetHR >= 75 ? '⚠ Over-Hedge Risk' : '◈ Approaching Optimal Ceiling'}
              </p>
              <p className="text-xs text-slate-400 leading-relaxed">
                {targetHR >= 75
                  ? `At ${targetHR}% hedge ratio, if actual fuel demand falls 20% below forecast, you may be over-hedged by ~${formatInt(Math.round(consumption * (targetHR / 100) * 0.2))} bbl — creating mark-to-market losses. Southwest Airlines faced this in 2020 (COVID demand collapse).`
                  : `At ${targetHR}%, you are approaching the 70% inflection point where marginal VaR reduction drops below 2% per 10% HR increase (H1 validated). Additional collateral cost may outweigh the incremental hedge benefit.`}
              </p>
            </div>
          )}
        </div>

        {canEditConsumption && (
          <button
            type="button"
            onClick={handleGetAiRecommendation}
            disabled={aiLoading}
            className="w-full mt-4 inline-flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-60 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Sparkles className="h-4 w-4" />
            {aiLoading ? 'Analyzing...' : 'Get AI Recommendation'}
          </button>
        )}

        {aiResult && (
          <div className="mt-4 rounded-xl border border-blue-800/50 bg-blue-950/20 p-4">
            <p className="text-xs text-blue-400 uppercase tracking-wide mb-3">AI Strategy Analysis</p>
            <div className="grid grid-cols-2 gap-3 mb-3 text-sm">
              <div>
                <p className="text-slate-400 text-xs">Your Strategy VaR</p>
                <p className="text-white font-bold font-mono">{formatMillions(aiResult.what_if.var_usd)}</p>
              </div>
              <div>
                <p className="text-slate-400 text-xs">vs. System Recommendation</p>
                <p className={`font-bold font-mono ${aiResult.comparison.var_better ? 'text-green-400' : 'text-amber-400'}`}>
                  {aiResult.comparison.var_better ? '▼ Lower risk' : '▲ Higher risk'} by{' '}
                  {formatMillions(Math.abs(aiResult.comparison.var_difference))}
                </p>
              </div>
              <div>
                <p className="text-slate-400 text-xs">Collateral Required</p>
                <p className="text-white font-mono text-sm">
                  {formatMillions(aiResult.what_if.collateral_usd)} ({formatPct(aiResult.what_if.collateral_pct_of_reserves, 1)} of reserves)
                </p>
              </div>
              <div>
                <p className="text-slate-400 text-xs">Monthly saving vs. unhedged</p>
                <p className="text-green-400 font-mono text-sm">
                  {formatMillions(aiResult.comparison.monthly_saving_vs_unhedged)}
                </p>
              </div>
            </div>
            <p className="text-sm text-slate-300 leading-relaxed border-t border-slate-700 pt-3">{aiResult.verdict}</p>
            {aiResult.source && (
              <p className="text-xs text-slate-600 mt-2 text-right">
                {aiResult.source === 'n8n_gpt'
                  ? '✦ Generated by GPT-4o-mini via n8n'
                  : '○ Fallback template (n8n unavailable)'}
              </p>
            )}
          </div>
        )}
      </div>

      {canEditConsumption && (
        <HedgeCostSimulator
          currentPrice={currentPrice}
          consumption={consumption}
          hedgeRatioPct={targetHR}
          selectedInstruments={selectedInstruments}
        />
      )}
 
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
