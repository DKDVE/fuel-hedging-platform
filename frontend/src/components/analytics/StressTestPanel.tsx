import { useEffect } from 'react';
import { useStressScenarios, type ScenarioRunResult } from '@/hooks/useStressScenarios';
import { formatMillions, formatPct, formatPrice } from '@/lib/formatters';
import { toast } from 'sonner';

function getPrimaryInstrument(instrumentMix: Record<string, number>): string {
  if (!instrumentMix || Object.keys(instrumentMix).length === 0) return '—';
  const entries = Object.entries(instrumentMix);
  const primary = entries.reduce((a, b) => (a[1] > b[1] ? a : b));
  const label = primary[0].charAt(0).toUpperCase() + primary[0].slice(1);
  return `${label} (${formatPct(primary[1] * 100, 0)})`;
}

export function StressTestPanel() {
  const {
    scenarios,
    selectedScenario,
    setSelectedScenario,
    selectedScenarioData,
    runScenario,
    result,
    isRunning,
    error,
  } = useStressScenarios();

  // Auto-select first scenario when scenarios load
  useEffect(() => {
    const first = scenarios[0];
    if (first && !selectedScenario) {
      setSelectedScenario(first.id);
    }
  }, [scenarios, selectedScenario, setSelectedScenario]);

  const handleRunScenario = async () => {
    if (!selectedScenario) return;
    try {
      await runScenario(selectedScenario);
      toast.success('Stress test completed');
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'response' in e
          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Stress test failed'
          : e instanceof Error
            ? e.message
            : 'Stress test failed';
      toast.error(String(msg));
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-white mb-4">Stress Test Scenarios</h2>
        <p className="text-sm text-slate-400 mb-4">
          Simulate hedge strategy response under historical and hypothetical market stress.
        </p>

        {/* Scenario selector grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
          {scenarios.map((scenario) => (
            <button
              key={scenario.id}
              onClick={() => setSelectedScenario(scenario.id)}
              className={`p-3 rounded-lg border text-left transition-all ${
                selectedScenario === scenario.id
                  ? 'border-blue-500 bg-blue-950 ring-1 ring-blue-500'
                  : 'border-gray-700 bg-gray-900 hover:border-gray-500'
              }`}
            >
              <div
                className="w-2 h-2 rounded-full mb-2"
                style={{ backgroundColor: scenario.color }}
              />
              <p className="text-sm font-medium text-white leading-tight">{scenario.name}</p>
              <p className="text-xs text-gray-400 mt-1">
                {scenario.price_shock_pct >= 0 ? '+' : ''}
                {(scenario.price_shock_pct * 100).toFixed(0)}% price
              </p>
              <p className="text-xs text-gray-500">{scenario.historical_reference}</p>
            </button>
          ))}
        </div>

        {selectedScenarioData && (
          <p className="text-sm text-gray-400 mb-4 italic">{selectedScenarioData.description}</p>
        )}

        {error && (
          <p className="text-red-400 text-sm mb-3">
            {error instanceof Error
              ? error.message
              : typeof error === 'object' && error !== null && 'response' in error
                ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Stress test failed'
                : 'Stress test failed. Check console.'}
          </p>
        )}
        <button
          onClick={handleRunScenario}
          disabled={!selectedScenario || isRunning}
          className="px-6 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium"
        >
          {isRunning ? (
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Simulating…
            </span>
          ) : (
            'Simulate Scenario'
          )}
        </button>
      </div>

      {/* Results panel - only show when result matches selected scenario */}
      {result &&
        result.scenario_id === selectedScenario && (
          <ScenarioResults result={result} />
        )}
    </div>
  );
}

function ScenarioResults({ result }: { result: ScenarioRunResult }) {
  const opt = result.optimizer_result;
  const varImpact = result.var_impact;

  return (
    <div className="mt-6 p-5 bg-gray-900 rounded-xl border border-gray-700">
      <h3 className="font-semibold text-white mb-1">SCENARIO: {result.scenario_name}</h3>

      {/* Price impact */}
      <div className="flex items-center gap-3 mb-4">
        <span className="text-gray-400 text-sm">Stressed Price:</span>
        <span className="text-white font-mono">{formatPrice(result.stressed_price)}/bbl</span>
        <span className="text-gray-500 text-sm">
          (current: {formatPrice(result.current_price)}, shock:{' '}
          {result.price_change_pct >= 0 ? '+' : ''}
          {result.price_change_pct}%)
        </span>
      </div>

      {/* Two-column results */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-gray-800 rounded-lg p-4">
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Optimizer Response</p>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Recommended HR</span>
              <span className="text-white font-medium">
                {formatPct(opt.optimal_hr * 100)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Primary Instrument</span>
              <span className="text-white">{getPrimaryInstrument(opt.instrument_mix)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Collateral Required</span>
              <span
                className={
                  opt.collateral_pct_of_reserves > 0.13 ? 'text-amber-400' : 'text-green-400'
                }
              >
                {formatPct(opt.collateral_pct_of_reserves * 100)}
                {opt.collateral_pct_of_reserves > 0.13 && ' ⚠️'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Constraints</span>
              <span
                className={
                  result.constraints_satisfied ? 'text-green-400' : 'text-red-400'
                }
              >
                {result.constraints_satisfied ? '✅ All satisfied' : '❌ Violations'}
              </span>
            </div>
          </div>
        </div>

        {varImpact?.stressed_var_usd != null && (
          <div className="bg-gray-800 rounded-lg p-4">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">VaR Impact</p>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Stressed VaR</span>
                <span className="text-red-400 font-medium">
                  {formatMillions(varImpact.stressed_var_usd)}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Narrative */}
      <div className="bg-gray-800 rounded-lg p-4">
        <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Risk Assessment</p>
        <p className="text-sm text-gray-300 leading-relaxed">{result.risk_narrative}</p>
      </div>
    </div>
  );
}
