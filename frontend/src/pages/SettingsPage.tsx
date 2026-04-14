import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle, XCircle, Save, RefreshCw } from 'lucide-react';
import { usePermissions } from '@/hooks/usePermissions';
import apiClient from '@/lib/api';
import { toast } from 'sonner';

interface APIHealthStatus {
  source: string;
  status: 'OK' | 'DEGRADED' | 'DOWN';
  last_fetch: string;
  latency_ms: number;
  http_status: number;
}

type InstrumentPreference =
  | 'optimiser_decides'
  | 'favour_futures'
  | 'favour_options'
  | 'favour_collars'
  | 'favour_swaps';

interface ConstraintsState {
  hr_hard_cap: number;
  hr_soft_warn: number;
  collateral_limit: number;
  mape_alert_threshold: number;
  var_reduction_target: number;
  monthly_consumption_bbl: number;
  hr_band_min: number;
  instrument_preference: InstrumentPreference;
}

interface PlatformConfigResponse {
  hr_cap?: number;
  collateral_limit?: number;
  mape_target?: number;
  var_reduction_target?: number;
  monthly_consumption_bbl?: number;
  hr_band_min?: number;
  instrument_preference?: string;
}

interface ConfigPatchPayload {
  key: string;
  value: number | string;
}

const DEFAULT_CONSTRAINTS: ConstraintsState = {
  hr_hard_cap: 0.80,
  hr_soft_warn: 70,
  collateral_limit: 15,
  mape_alert_threshold: 10.0,
  var_reduction_target: 0.40,
  monthly_consumption_bbl: 100000,
  hr_band_min: 40,
  instrument_preference: 'optimiser_decides',
};

export function SettingsPage() {
  const { hasPermission } = usePermissions();
  const canEdit = hasPermission('edit:config');

  const [constraints, setConstraints] = useState<ConstraintsState>(DEFAULT_CONSTRAINTS);
  const [initialConstraints, setInitialConstraints] = useState<ConstraintsState>(DEFAULT_CONSTRAINTS);

  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Mock API health data
  const apiHealth: APIHealthStatus[] = [
    {
      source: 'EIA (Energy Information Administration)',
      status: 'OK',
      last_fetch: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
      latency_ms: 245,
      http_status: 200,
    },
    {
      source: 'CME (Chicago Mercantile Exchange)',
      status: 'OK',
      last_fetch: new Date(Date.now() - 3 * 60 * 1000).toISOString(),
      latency_ms: 180,
      http_status: 200,
    },
    {
      source: 'ICE (Intercontinental Exchange)',
      status: 'DEGRADED',
      last_fetch: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
      latency_ms: 1250,
      http_status: 200,
    },
    {
      source: 'n8n Workflow Engine',
      status: 'OK',
      last_fetch: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
      latency_ms: 95,
      http_status: 200,
    },
  ];

  const handleChange = (field: keyof ConstraintsState, value: number | string) => {
    setConstraints({ ...constraints, [field]: value });
    setIsDirty(true);
  };

  const buildConfigPayloads = (state: ConstraintsState): ConfigPatchPayload[] => {
    return [
      { key: 'monthly_consumption_bbl', value: state.monthly_consumption_bbl },
      { key: 'hr_band_min', value: state.hr_soft_warn / 100 },
      { key: 'instrument_preference', value: state.instrument_preference },
      { key: 'hr_cap', value: state.hr_hard_cap },
      { key: 'collateral_limit', value: state.collateral_limit / 100 },
      { key: 'mape_target', value: state.mape_alert_threshold },
      { key: 'var_reduction_target', value: state.var_reduction_target },
    ];
  };

  const loadConfig = async (): Promise<void> => {
    try {
      const { data } = await apiClient.get<PlatformConfigResponse>('/analytics/config');
      const next: ConstraintsState = {
        hr_hard_cap: typeof data.hr_cap === 'number' ? data.hr_cap : DEFAULT_CONSTRAINTS.hr_hard_cap,
        hr_soft_warn:
          typeof data.hr_band_min === 'number'
            ? data.hr_band_min * 100
            : DEFAULT_CONSTRAINTS.hr_soft_warn,
        collateral_limit:
          typeof data.collateral_limit === 'number'
            ? data.collateral_limit * 100
            : DEFAULT_CONSTRAINTS.collateral_limit,
        mape_alert_threshold:
          typeof data.mape_target === 'number'
            ? data.mape_target
            : DEFAULT_CONSTRAINTS.mape_alert_threshold,
        var_reduction_target:
          typeof data.var_reduction_target === 'number'
            ? data.var_reduction_target
            : DEFAULT_CONSTRAINTS.var_reduction_target,
        monthly_consumption_bbl:
          typeof data.monthly_consumption_bbl === 'number'
            ? data.monthly_consumption_bbl
            : DEFAULT_CONSTRAINTS.monthly_consumption_bbl,
        hr_band_min:
          typeof data.hr_band_min === 'number'
            ? data.hr_band_min * 100
            : DEFAULT_CONSTRAINTS.hr_band_min,
        instrument_preference:
          data.instrument_preference === 'favour_futures' ||
          data.instrument_preference === 'favour_options' ||
          data.instrument_preference === 'favour_collars' ||
          data.instrument_preference === 'favour_swaps' ||
          data.instrument_preference === 'optimiser_decides'
            ? data.instrument_preference
            : DEFAULT_CONSTRAINTS.instrument_preference,
      };

      setConstraints(next);
      setInitialConstraints(next);
      setIsDirty(false);
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : 'Failed to load settings';
      toast.error(message);
    }
  };

  useEffect(() => {
    void loadConfig();
  }, []);

  const handleSave = async () => {
    if (!canEdit) return;
    setIsSaving(true);
    try {
      const currentPayloads = buildConfigPayloads(constraints);
      const baselineMap = new Map(
        buildConfigPayloads(initialConstraints).map((item) => [item.key, item.value])
      );
      const changedPayloads = currentPayloads.filter(
        (item) => baselineMap.get(item.key) !== item.value
      );

      for (const payload of changedPayloads) {
        await apiClient.patch('/analytics/config', payload);
      }

      setInitialConstraints(constraints);
      setIsDirty(false);
      toast.success('Settings saved');
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : 'Failed to save settings';
      toast.error(message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = async () => {
    await loadConfig();
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'OK':
        return (
          <span className="flex items-center gap-1 text-green-400 text-sm font-semibold">
            <CheckCircle className="h-4 w-4" />
            Operational
          </span>
        );
      case 'DEGRADED':
        return (
          <span className="flex items-center gap-1 text-amber-400 text-sm font-semibold">
            <AlertTriangle className="h-4 w-4" />
            Degraded
          </span>
        );
      case 'DOWN':
        return (
          <span className="flex items-center gap-1 text-red-400 text-sm font-semibold">
            <XCircle className="h-4 w-4" />
            Down
          </span>
        );
      default:
        return status;
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    return `${diffHours}h ago`;
  };

  if (!canEdit) {
    return (
      <div className="p-8 max-w-7xl mx-auto">
        <div className="card">
          <div className="flex items-center gap-3 text-amber-400 mb-4">
            <AlertTriangle className="h-6 w-6" />
            <h2 className="text-xl font-semibold">Access Restricted</h2>
          </div>
          <p className="text-slate-400">
            You don't have permission to modify platform settings. Only Admin users
            can access this page.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Settings</h1>
        <p className="text-slate-400">
          Configure platform constraints and monitor system health
        </p>
      </div>

      {/* Constraint Editor */}
      <div className="card">
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-1">
            Demand &amp; Strategy Policy
          </h3>
          <p className="text-sm text-slate-400">
            Configure demand volume and instrument-selection guidance
          </p>
        </div>

        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Monthly Fuel Uplift (barrels)
            </label>
            <div className="flex items-center gap-4">
              <input
                type="number"
                min="10000"
                max="10000000"
                step="1000"
                value={constraints.monthly_consumption_bbl}
                onChange={(e) =>
                  handleChange('monthly_consumption_bbl', parseFloat(e.target.value))
                }
                className="input w-48"
              />
            </div>
            <p className="text-sm text-slate-400 mt-2">
              Total fuel consumed per month across all routes. Used to calculate hedged vs.
              unhedged volume in recommendations.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Minimum Hedge Band (%)
            </label>
            <div className="flex items-center gap-4">
              <input
                type="number"
                min="0"
                max="70"
                step="1"
                value={constraints.hr_band_min}
                onChange={(e) => handleChange('hr_band_min', parseFloat(e.target.value))}
                className="input w-32"
              />
            </div>
            <p className="text-sm text-slate-400 mt-2">
              System will never recommend below this ratio. Industry range: 30-70%.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Instrument Preference
            </label>
            <select
              value={constraints.instrument_preference}
              onChange={(e) => handleChange('instrument_preference', e.target.value)}
              className="input w-64"
            >
              <option value="optimiser_decides">Optimiser decides</option>
              <option value="favour_futures">Favour Futures</option>
              <option value="favour_options">Favour Options</option>
              <option value="favour_collars">Favour Collars</option>
              <option value="favour_swaps">Favour Swaps</option>
            </select>
            <p className="text-sm text-slate-400 mt-2">
              Guide the optimiser toward a preferred instrument type. &apos;Optimiser decides&apos; uses pure VaR
              minimisation.
            </p>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-white mb-1">
              Risk Constraints
            </h3>
            <p className="text-sm text-slate-400">
              Global limits for hedging operations
            </p>
          </div>
          {isDirty && (
            <span className="text-xs text-amber-400 flex items-center gap-1">
              <AlertTriangle className="h-3 w-3" />
              Unsaved changes
            </span>
          )}
        </div>

        <div className="space-y-6">
          {/* HR Hard Cap */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Hedge Ratio Hard Cap
            </label>
            <div className="flex items-center gap-4">
              <input
                type="number"
                min="0.50"
                max="0.80"
                step="0.01"
                value={constraints.hr_hard_cap}
                onChange={(e) =>
                  handleChange('hr_hard_cap', parseFloat(e.target.value))
                }
                className="input w-32"
              />
              <span className="text-sm text-slate-400">
                Maximum allowed hedge ratio (0.50 - 0.80)
              </span>
            </div>
            {constraints.hr_hard_cap > 0.70 && (
              <div className="mt-2 flex items-start gap-2 p-3 bg-amber-950/30 border border-amber-800 rounded-lg text-amber-400 text-sm">
                <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <span>
                  HR above 70% — diminishing returns per H1 hypothesis. Consider
                  reviewing basis risk impact.
                </span>
              </div>
            )}
          </div>

          {/* HR Soft Warning */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Hedge Ratio Soft Warning
            </label>
            <div className="flex items-center gap-4">
              <input
                type="number"
                min="0.50"
                max="0.80"
                step="0.01"
                value={constraints.hr_soft_warn}
                onChange={(e) =>
                  handleChange('hr_soft_warn', parseFloat(e.target.value))
                }
                className="input w-32"
              />
              <span className="text-sm text-slate-400">
                Threshold for HR warning alerts
              </span>
            </div>
          </div>

          {/* Collateral Limit */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Collateral Reserve Limit
            </label>
            <div className="flex items-center gap-4">
              <input
                type="number"
                min="0.05"
                max="0.20"
                step="0.01"
                value={constraints.collateral_limit}
                onChange={(e) =>
                  handleChange('collateral_limit', parseFloat(e.target.value))
                }
                className="input w-32"
              />
              <span className="text-sm text-slate-400">
                Maximum % of cash reserves (0.05 - 0.20)
              </span>
            </div>
          </div>

          {/* MAPE Alert */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              MAPE Alert Threshold (%)
            </label>
            <div className="flex items-center gap-4">
              <input
                type="number"
                min="5.0"
                max="15.0"
                step="0.1"
                value={constraints.mape_alert_threshold}
                onChange={(e) =>
                  handleChange('mape_alert_threshold', parseFloat(e.target.value))
                }
                className="input w-32"
              />
              <span className="text-sm text-slate-400">
                Forecast accuracy alert level (5.0 - 15.0)
              </span>
            </div>
          </div>

          {/* VaR Reduction Target */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              VaR Reduction Target (%)
            </label>
            <div className="flex items-center gap-4">
              <input
                type="number"
                min="0.20"
                max="0.60"
                step="0.01"
                value={constraints.var_reduction_target}
                onChange={(e) =>
                  handleChange('var_reduction_target', parseFloat(e.target.value))
                }
                className="input w-32"
              />
              <span className="text-sm text-slate-400">
                Minimum expected VaR improvement (0.20 - 0.60)
              </span>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3 mt-8 pt-6 border-t border-slate-800">
          <button
            onClick={handleSave}
            disabled={!isDirty || isSaving}
            className="btn btn-primary flex items-center gap-2 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {isSaving ? 'Saving...' : 'Save Changes'}
          </button>
          <button
            onClick={handleReset}
            disabled={!isDirty}
            className="btn btn-secondary flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw className="h-4 w-4" />
            Reset
          </button>
        </div>
      </div>

      {/* API Health Status */}
      <div className="card">
        <h3 className="text-lg font-semibold text-white mb-4">API Health Status</h3>
        <div className="space-y-3">
          {apiHealth.map((api, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-4 bg-slate-900/50 rounded-lg border border-slate-800"
            >
              <div className="flex-1">
                <h4 className="text-sm font-semibold text-white mb-1">{api.source}</h4>
                <div className="flex items-center gap-4 text-xs text-slate-400">
                  <span>Last fetch: {formatTimestamp(api.last_fetch)}</span>
                  <span>•</span>
                  <span>Latency: {api.latency_ms}ms</span>
                  <span>•</span>
                  <span>HTTP {api.http_status}</span>
                </div>
              </div>
              <div>{getStatusBadge(api.status)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
