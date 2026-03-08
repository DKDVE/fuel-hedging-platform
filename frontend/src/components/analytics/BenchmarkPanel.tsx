import { useAnalyticsSummary } from '@/hooks/useAnalytics';
import {
  BENCHMARK_METRICS,
  AIRLINE_PROFILES,
  type BenchmarkMetric,
} from '@/data/industryBenchmarks';
import { formatBenchmarkValue } from '@/lib/formatters';

function MetricComparisonRow({
  metric,
  ourLiveValue,
}: {
  metric: BenchmarkMetric;
  ourLiveValue?: number;
}) {
  const ourValue = ourLiveValue ?? metric.ourValue ?? 0;

  const isGood = metric.higherIsBetter
    ? ourValue >= metric.industryAvg
    : ourValue <= metric.industryAvg;

  const isBestInClass = metric.higherIsBetter
    ? ourValue >= metric.bestInClass * 0.95
    : ourValue <= metric.bestInClass * 1.05;

  const maxVal = metric.higherIsBetter
    ? Math.max(metric.bestInClass * 1.1, ourValue * 1.1)
    : Math.max(metric.industryAvg * 1.5, ourValue * 1.5);
  const barPctForVal = (val: number) =>
    metric.higherIsBetter ? (val / maxVal) * 100 : ((maxVal - val) / maxVal) * 100 + 10;

  return (
    <div className="py-4 border-b border-slate-800 last:border-0">
      <div className="flex justify-between items-start mb-2">
        <div>
          <p className="font-medium text-white text-sm">{metric.label}</p>
          <p className="text-xs text-slate-500">{metric.description}</p>
        </div>
        <div className="flex items-center gap-2 text-right">
          {isBestInClass && (
            <span className="text-xs bg-blue-900 text-blue-300 px-2 py-0.5 rounded-full font-medium">
              Best-in-class
            </span>
          )}
          <span
            className={`font-bold text-sm ${isGood ? 'text-green-400' : 'text-amber-400'}`}
          >
            {formatBenchmarkValue(ourValue, metric.unit)}
          </span>
        </div>
      </div>

      <div className="space-y-1">
        {[
          { label: 'This Platform', value: ourValue, color: 'bg-blue-500' },
          { label: 'Industry Avg', value: metric.industryAvg, color: 'bg-slate-500' },
          {
            label: metric.bestInClassLabel.split(' (')[0],
            value: metric.bestInClass,
            color: 'bg-green-600',
          },
        ].map(({ label, value, color }) => {
          const barPct = Math.min(barPctForVal(value), 100);
          return (
            <div key={label} className="flex items-center gap-3">
              <span className="text-xs text-slate-500 w-28 shrink-0">{label}</span>
              <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className={`h-full ${color} rounded-full transition-all duration-700`}
                  style={{ width: `${barPct}%` }}
                />
              </div>
              <span className="text-xs font-mono text-slate-400 w-16 text-right shrink-0">
                {formatBenchmarkValue(value, metric.unit)}
              </span>
            </div>
          );
        })}
      </div>

      <p className="text-[10px] text-slate-600 mt-1">Source: {metric.industrySource}</p>
    </div>
  );
}

export function BenchmarkPanel() {
  const { data: summary } = useAnalyticsSummary();

  const totalNotional = summary?.total_notional_usd ?? 14_500_000;
  const collateralUsd = summary?.collateral_pct
    ? (summary.collateral_pct / 100) * 10_000_000
    : 2_000_000;
  const liveValues: Record<string, number> = {
    hedge_ratio: (summary?.current_hedge_ratio ?? 0) * 100,
    mape: summary?.mape_pct ?? 0,
    r2_heating_oil: summary?.r2_heating_oil ?? 0.85,
    collateral_efficiency: totalNotional / Math.max(collateralUsd, 1),
  };

  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-lg font-semibold text-white mb-2">
          Performance Metrics Comparison
        </h3>
        <p className="text-sm text-slate-400 mb-4">
          Compare platform performance against industry benchmarks
        </p>
        <div className="card">
          {BENCHMARK_METRICS.map((metric) => (
            <MetricComparisonRow
              key={metric.id}
              metric={metric}
              ourLiveValue={metric.ourValueKey ? liveValues[metric.ourValueKey] : undefined}
            />
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-white mb-2">
          Airline Hedging Strategy Profiles
        </h3>
        <p className="text-sm text-slate-400 mb-4">
          How leading airlines approach fuel hedging
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {AIRLINE_PROFILES.map((airline) => (
            <div
              key={airline.iataCode}
              className={`p-4 rounded-xl border ${
                airline.iataCode === '—'
                  ? 'border-blue-600 bg-blue-950/20'
                  : 'border-slate-700 bg-slate-900'
              }`}
            >
              <div className="flex justify-between items-start mb-2">
                <div>
                  <p className="font-semibold text-white text-sm">{airline.name}</p>
                  {airline.iataCode !== '—' && (
                    <span className="text-xs font-mono text-slate-500">{airline.iataCode}</span>
                  )}
                </div>
                <span className="text-xs text-slate-400 bg-slate-800 px-2 py-1 rounded">
                  {airline.typicalCoverage}
                </span>
              </div>
              <p className="text-xs text-slate-400 mb-2">{airline.hedgingPhilosophy}</p>
              <div className="flex flex-wrap gap-1">
                {airline.primaryInstruments.map((inst) => (
                  <span
                    key={inst}
                    className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded"
                  >
                    {inst}
                  </span>
                ))}
              </div>
              <p className="text-[10px] text-slate-500 mt-2 italic">{airline.notableApproach}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
