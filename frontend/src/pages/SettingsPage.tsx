import { useState } from 'react';
import { AlertTriangle, CheckCircle, XCircle, Save, RefreshCw } from 'lucide-react';
import { usePermissions } from '@/hooks/usePermissions';

interface APIHealthStatus {
  source: string;
  status: 'OK' | 'DEGRADED' | 'DOWN';
  last_fetch: string;
  latency_ms: number;
  http_status: number;
}

export function SettingsPage() {
  const { hasPermission } = usePermissions();
  const canEdit = hasPermission('edit:config');

  // Mock constraint values
  const [constraints, setConstraints] = useState({
    hr_hard_cap: 0.80,
    hr_soft_warn: 0.70,
    collateral_limit: 0.15,
    mape_alert_threshold: 10.0,
    var_reduction_target: 0.40,
  });

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

  const handleChange = (field: keyof typeof constraints, value: number) => {
    setConstraints({ ...constraints, [field]: value });
    setIsDirty(true);
  };

  const handleSave = async () => {
    if (!canEdit) return;
    setIsSaving(true);
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setIsSaving(false);
    setIsDirty(false);
    console.log('Saving constraints:', constraints);
  };

  const handleReset = () => {
    setConstraints({
      hr_hard_cap: 0.80,
      hr_soft_warn: 0.70,
      collateral_limit: 0.15,
      mape_alert_threshold: 10.0,
      var_reduction_target: 0.40,
    });
    setIsDirty(false);
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
