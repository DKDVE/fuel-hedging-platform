import { useState } from 'react';
import { HypothesisCard } from '@/components/analytics/HypothesisCard';
import { WalkForwardVarChart } from '@/components/analytics/WalkForwardVarChart';
import { RollingMapeChart } from '@/components/analytics/RollingMapeChart';
import { BacktestTab } from '@/components/analytics/BacktestTab';
import { StressTestPanel } from '@/components/analytics/StressTestPanel';
import { BenchmarkPanel } from '@/components/analytics/BenchmarkPanel';
import {
  useAnalyticsSummary,
  useAnalyticsHistory,
  useLoadCsv,
  useTriggerAnalytics,
  useVarWalkForward,
  useMapeHistory,
  useBacktestLatest,
} from '@/hooks/useAnalytics';
import { usePermissions } from '@/hooks/usePermissions';
import { getApiBaseUrl } from '@/lib/api';
import { formatMillions, formatPct, formatRatio, isSafe } from '@/lib/formatters';
import { Play, BarChart3, Database, TrendingUp, FileDown, Zap, Target } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

export function AnalyticsPage() {
  const [activeTab, setActiveTab] = useState<'validation' | 'backtest' | 'stress' | 'benchmark'>('validation');
  const { isLoading: summaryLoading } = useAnalyticsSummary();
  const { data: history } = useAnalyticsHistory(1, 90);
  const { data: varData, isLoading: varLoading } = useVarWalkForward(90);
  const { data: mapeData, isLoading: mapeLoading } = useMapeHistory(180);
  const { data: backtestData, isLoading: backtestLoading } = useBacktestLatest();
  const triggerMutation = useTriggerAnalytics();
  const loadCsvMutation = useLoadCsv();
  const { hasPermission } = usePermissions();

  const canTrigger = hasPermission('trigger:pipeline');
  const canLoadCsv = hasPermission('read:analytics');
  const [generatingReport, setGeneratingReport] = useState(false);

  const handleDownloadReport = async () => {
    setGeneratingReport(true);
    try {
      const response = await fetch(`${getApiBaseUrl()}/reports/ifrs9/latest`, {
        credentials: 'include',
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail ?? 'Report generation failed');
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ifrs9_report_${new Date().toISOString().slice(0, 10)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('IFRS 9 report downloaded successfully');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to generate report');
    } finally {
      setGeneratingReport(false);
    }
  };

  const handleTriggerAnalytics = async () => {
    if (!canTrigger) return;
    try {
      await triggerMutation.mutateAsync();
      toast.success('Pipeline started. Results will appear in ~8 minutes.');
    } catch (error) {
      toast.error((error as Error)?.message ?? 'Failed to trigger analytics.');
    }
  };

  const handleLoadCsv = async () => {
    if (!canLoadCsv || loadCsvMutation.isPending) return;
    try {
      const result = await loadCsvMutation.mutateAsync();
      toast.success(
        `Loaded ${result.imported} new records, updated ${result.updated}. Total: ${result.total} rows.`
      );
    } catch (error) {
      toast.error((error as Error)?.message ?? 'Failed to load CSV.');
    }
  };

  // Mock hypothesis data - replace with actual API call
  const hypotheses = [
    {
      id: 'h1',
      title: 'H1: HR Diminishing Returns',
      description: 'Marginal VaR reduction decreases significantly above 70% hedge ratio due to basis risk amplification.',
      metric: {
        label: 'Marginal VaR Reduction at 70%',
        value: 0.42,
        threshold: 0.5,
        thresholdLabel: 'Threshold: < 0.5%',
        unit: '%',
      },
      passed: true,
      lastTested: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
      trend: 'down' as const,
    },
    {
      id: 'h2',
      title: 'H2: Proxy Effectiveness',
      description: 'Heating oil futures R² must exceed 0.80 to qualify for IFRS 9 hedge accounting designation.',
      metric: {
        label: 'R² Heating Oil',
        value: 0.8517,
        threshold: 0.80,
        thresholdLabel: 'IFRS 9 Minimum: ≥ 0.80',
        unit: 'ratio',
      },
      passed: true,
      lastTested: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
      trend: 'up' as const,
    },
    {
      id: 'h3',
      title: 'H3: Ensemble Accuracy',
      description: '30-day ensemble forecast MAPE must remain below 8% to maintain target forecast accuracy.',
      metric: {
        label: '30-Day MAPE',
        value: 4.36,
        threshold: 8.0,
        thresholdLabel: 'Target: < 8%',
        unit: '%',
      },
      passed: true,
      lastTested: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(),
      trend: 'down' as const,
    },
    {
      id: 'h4',
      title: 'H4: Dynamic vs Static HR',
      description: 'Dynamic hedge ratio rebalancing should provide measurable VaR improvement over static 60% HR baseline.',
      metric: {
        label: 'VaR Improvement',
        value: 15.3,
        threshold: 0,
        thresholdLabel: 'Baseline: > 0% improvement',
        unit: '%',
      },
      passed: true,
      lastTested: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
      trend: 'up' as const,
    },
  ];

  // Mock hypothesis data remains for now - these don't have API endpoints yet

  if (summaryLoading) {
    return (
      <div className="p-8 max-w-7xl mx-auto">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Analytics & Validation</h1>
          <p className="text-slate-400">
            Hypothesis testing, model performance, and walk-forward analysis
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleDownloadReport}
            disabled={generatingReport}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors border border-green-700',
              generatingReport
                ? 'bg-green-900 text-green-400 cursor-not-allowed opacity-60'
                : 'bg-green-800 hover:bg-green-700 text-green-100'
            )}
          >
            <FileDown className="w-4 h-4" />
            {generatingReport ? 'Generating…' : 'IFRS 9 Report'}
          </button>
          {canLoadCsv && (
            <button
              onClick={handleLoadCsv}
              disabled={loadCsvMutation.isPending}
              className="btn btn-secondary flex items-center gap-2 disabled:opacity-50"
              title="Load historical fuel data from CSV"
            >
              <Database className="h-4 w-4" />
              {loadCsvMutation.isPending ? 'Loading...' : 'Load CSV'}
            </button>
          )}
          {canTrigger && (
            <button
              onClick={handleTriggerAnalytics}
              disabled={triggerMutation.isPending}
              className="btn btn-primary flex items-center gap-2 disabled:opacity-50"
            >
              <Play className="h-4 w-4" />
              {triggerMutation.isPending ? 'Running...' : 'Run Analytics'}
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('validation')}
          className={cn(
            'px-4 py-2 rounded-t-lg font-medium text-sm transition-colors flex items-center gap-2',
            activeTab === 'validation'
              ? 'bg-slate-800 text-white border-b-2 border-primary-500 -mb-0.5'
              : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
          )}
        >
          <BarChart3 className="h-4 w-4" />
          Hypothesis Validation
        </button>
        <button
          onClick={() => setActiveTab('backtest')}
          className={cn(
            'px-4 py-2 rounded-t-lg font-medium text-sm transition-colors flex items-center gap-2',
            activeTab === 'backtest'
              ? 'bg-slate-800 text-white border-b-2 border-primary-500 -mb-0.5'
              : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
          )}
        >
          <TrendingUp className="h-4 w-4" />
          Backtesting
        </button>
        <button
          onClick={() => setActiveTab('stress')}
          className={cn(
            'px-4 py-2 rounded-t-lg font-medium text-sm transition-colors flex items-center gap-2',
            activeTab === 'stress'
              ? 'bg-slate-800 text-white border-b-2 border-primary-500 -mb-0.5'
              : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
          )}
        >
          <Zap className="h-4 w-4" />
          Stress Testing
        </button>
        <button
          onClick={() => setActiveTab('benchmark')}
          className={cn(
            'px-4 py-2 rounded-t-lg font-medium text-sm transition-colors flex items-center gap-2',
            activeTab === 'benchmark'
              ? 'bg-slate-800 text-white border-b-2 border-primary-500 -mb-0.5'
              : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
          )}
        >
          <Target className="h-4 w-4" />
          Benchmarking
        </button>
      </div>

      {activeTab === 'validation' && (
        <>
          {/* Hypothesis Cards Grid */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 className="h-5 w-5 text-primary-500" />
              <h2 className="text-xl font-semibold text-white">Hypothesis Validation</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {hypotheses.map((hypothesis) => (
                <HypothesisCard key={hypothesis.id} {...hypothesis} />
              ))}
            </div>
          </div>

          {/* Walk-Forward VaR Chart */}
      <WalkForwardVarChart 
        data={varData?.data_points || []} 
        isLoading={varLoading} 
      />

      {/* Rolling MAPE Chart */}
      <RollingMapeChart
        data={mapeData?.data_points || []}
        targetThreshold={mapeData?.target_threshold || 8.0}
        alertThreshold={mapeData?.alert_threshold || 10.0}
        isLoading={mapeLoading}
      />

          {/* Analytics Run History */}
          {history && history.items && history.items.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold text-white mb-4">Recent Runs</h3>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Run Date</th>
                  <th>Status</th>
                  <th>MAPE</th>
                  <th>VaR 95%</th>
                  <th>Optimal HR</th>
                  <th>Basis R²</th>
                  <th>IFRS 9</th>
                </tr>
              </thead>
              <tbody>
                {history.items.slice(0, 10).map((run) => {
                  const mape = run.forecast_mape != null ? Number(run.forecast_mape) : null;
                  const varUsd = run.var_95_usd != null ? Number(run.var_95_usd) : null;
                  const optHr = run.optimal_hr != null ? Number(run.optimal_hr) : null;
                  const basisR2 = run.basis_r2 != null ? Number(run.basis_r2) : null;
                  const ifrs9 = basisR2 != null && basisR2 >= 0.80;
                  return (
                    <tr key={run.id}>
                      <td className="font-medium">
                        {new Date(run.run_date).toLocaleDateString()}
                      </td>
                      <td>
                        {run.status === 'COMPLETED' ? (
                          <span className="badge badge-success">Success</span>
                        ) : (
                          <span className="badge badge-danger">Failed</span>
                        )}
                      </td>
                      <td>{formatPct(mape, 2)}</td>
                      <td>{formatMillions(varUsd)}</td>
                      <td>{formatRatio(optHr)}</td>
                      <td>
                        {isSafe(basisR2) ? (
                          <span
                            className={`badge ${
                              basisR2 >= 0.80 ? 'badge-success' : basisR2 >= 0.65 ? 'badge-warning' : 'badge-danger'
                            }`}
                          >
                            {basisR2.toFixed(3)}
                          </span>
                        ) : (
                          'N/A'
                        )}
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            basisR2 != null ? (ifrs9 ? 'badge-success' : 'badge-danger') : 'badge-warning'
                          }`}
                        >
                          {basisR2 != null ? (ifrs9 ? 'Compliant' : 'Non-compliant') : 'N/A'}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
          )}
        </>
      )}

      {activeTab === 'backtest' && (
        <BacktestTab data={backtestData} isLoading={backtestLoading} />
      )}

      {activeTab === 'stress' && <StressTestPanel />}

      {activeTab === 'benchmark' && <BenchmarkPanel />}
    </div>
  );
}
