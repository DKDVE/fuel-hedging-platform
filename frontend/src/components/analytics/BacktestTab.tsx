import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { formatUSD, formatMillions, formatPct } from '@/lib/formatters';
import type { BacktestLatestResponse } from '@/hooks/useAnalytics';
import { useSeedBacktest } from '@/hooks/useAnalytics';
import { usePermissions } from '@/hooks/usePermissions';

interface BacktestTabProps {
  data: BacktestLatestResponse | undefined;
  isLoading: boolean;
}

function formatDateShort(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: '2-digit',
  });
}

function BacktestEmptyState() {
  const { hasPermission } = usePermissions();
  const seedBacktest = useSeedBacktest();
  const canGenerate = hasPermission('trigger:pipeline');

  return (
    <div className="card">
      <div className="flex flex-col items-center justify-center py-16 text-slate-500">
        <p className="text-lg font-medium mb-2">No backtest data yet</p>
        {canGenerate ? (
          <>
            <p className="text-sm text-center max-w-md mb-4">
              Generate backtest results (takes ~30 seconds)
            </p>
            <button
              type="button"
              onClick={() => seedBacktest.mutate()}
              disabled={seedBacktest.isPending}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg font-medium"
            >
              {seedBacktest.isPending ? 'Generating…' : 'Generate backtest data'}
            </button>
            {seedBacktest.isError && (
              <p className="text-red-400 text-sm mt-2">{String(seedBacktest.error)}</p>
            )}
          </>
        ) : (
          <p className="text-sm text-center max-w-md">
            Ask an admin or risk manager to generate backtest data (Analytics → Backtesting → Generate)
          </p>
        )}
      </div>
    </div>
  );
}

export function BacktestTab({ data, isLoading }: BacktestTabProps) {
  if (isLoading) {
    return (
      <div className="card">
        <div className="animate-pulse">
          <div className="h-6 bg-slate-800 rounded w-1/3 mb-4" />
          <div className="h-[350px] bg-slate-800 rounded" />
        </div>
      </div>
    );
  }

  const summary = data?.summary;
  const weeklyResults = data?.weekly_results ?? [];

  if (!summary || weeklyResults.length === 0) {
    return (
      <BacktestEmptyState />
    );
  }

  // Equity curve data
  const equityData = weeklyResults.map((r) => ({
    date: r.week_date,
    cumulative: r.cumulative_savings_usd,
    weekly: r.weekly_savings_usd,
  }));

  // Monthly attribution: aggregate weekly savings by month
  const monthlyMap = new Map<string, number>();
  for (const r of weeklyResults) {
    const monthKey = r.week_date.slice(0, 7); // YYYY-MM
    monthlyMap.set(monthKey, (monthlyMap.get(monthKey) ?? 0) + r.weekly_savings_usd);
  }
  const monthlyData = Array.from(monthlyMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, savings]) => ({
      month,
      label: new Date(month + '-01').toLocaleDateString('en-US', {
        month: 'short',
        year: '2-digit',
      }),
      savings,
    }));

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card">
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
            Total Savings
          </p>
          <p
            className={`text-2xl font-bold ${
              summary.total_savings_usd >= 0 ? 'text-green-400' : 'text-red-400'
            }`}
          >
            {formatUSD(summary.total_savings_usd)}
          </p>
          <p className="text-xs text-slate-500 mt-1">vs unhedged</p>
        </div>
        <div className="card">
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
            Avg Weekly Saving
          </p>
          <p className="text-2xl font-bold text-white">
            {formatUSD(summary.avg_weekly_savings_usd)}/week
          </p>
          <p className="text-xs text-slate-500 mt-1">weekly average</p>
        </div>
        <div className="card">
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
            Sharpe Ratio
          </p>
          <p className="text-2xl font-bold text-white">
            {summary.sharpe_ratio.toFixed(2)}
          </p>
          <p className="text-xs text-slate-500 mt-1">annualised</p>
        </div>
        <div className="card">
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
            VaR Reduction
          </p>
          <p className="text-2xl font-bold text-green-400">
            {formatPct(summary.var_reduction_achieved * 100, 1)} {summary.h4_validated ? '✅' : ''}
          </p>
          <p className="text-xs text-slate-500 mt-1">target: 40%</p>
        </div>
      </div>

      {/* Equity Curve */}
      <div className="card">
        <h3 className="text-lg font-semibold text-white mb-2">Equity Curve</h3>
        <p className="text-sm text-slate-400 mb-4">
          Cumulative savings over time (green above zero, red below)
        </p>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={equityData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
            <defs>
              <linearGradient id="equityGain" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#22c55e" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#22c55e" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="equityLoss" x1="0" y1="1" x2="0" y2="0">
                <stop offset="0%" stopColor="#ef4444" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={formatDateShort}
              stroke="#64748b"
              tick={{ fill: '#94a3b8', fontSize: 10 }}
            />
            <YAxis
              tickFormatter={(v) => formatMillions(v)}
              stroke="#64748b"
              tick={{ fill: '#94a3b8', fontSize: 10 }}
              width={70}
            />
            <ReferenceLine y={0} stroke="#64748b" strokeDasharray="3 3" />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload?.[0]) {
                  const d = payload[0].payload as { date: string; cumulative: number; weekly: number };
                  return (
                    <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 shadow-xl">
                      <p className="text-xs text-slate-400 font-semibold mb-1">
                        Week of {formatDateShort(d.date)}
                      </p>
                      <p className="text-sm">
                        Saved: {formatUSD(d.weekly)} | Total: {formatUSD(d.cumulative)}
                      </p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Area
              type="monotone"
              dataKey="cumulative"
              stroke={summary.total_savings_usd >= 0 ? '#22c55e' : '#ef4444'}
              fill={summary.total_savings_usd >= 0 ? 'url(#equityGain)' : 'url(#equityLoss)'}
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Monthly Attribution */}
      <div className="card">
        <h3 className="text-lg font-semibold text-white mb-2">Monthly Attribution</h3>
        <p className="text-sm text-slate-400 mb-4">
          Monthly savings (green = hedging helped, red = hedging hurt)
        </p>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={monthlyData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis
              dataKey="label"
              stroke="#64748b"
              tick={{ fill: '#94a3b8', fontSize: 10 }}
            />
            <YAxis
              tickFormatter={(v) => formatMillions(v)}
              stroke="#64748b"
              tick={{ fill: '#94a3b8', fontSize: 10 }}
              width={70}
            />
            <ReferenceLine y={0} stroke="#64748b" strokeDasharray="3 3" />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload?.[0]) {
                  const d = payload[0].payload as { month: string; savings: number };
                  return (
                    <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 shadow-xl">
                      <p className="text-xs text-slate-400 font-semibold mb-1">
                        {new Date(d.month + '-01').toLocaleDateString('en-US', {
                          month: 'long',
                          year: 'numeric',
                        })}
                      </p>
                      <p
                        className={`text-sm font-semibold ${
                          d.savings >= 0 ? 'text-green-400' : 'text-red-400'
                        }`}
                      >
                        {formatUSD(d.savings)}
                      </p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar dataKey="savings" radius={[2, 2, 0, 0]}>
              {monthlyData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.savings >= 0 ? '#22c55e' : '#ef4444'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Key Stats Footer */}
      <div className="card bg-slate-800/50">
        <div className="flex flex-wrap gap-6 text-sm">
          <span className="text-slate-400">
            Profitable weeks: <strong className="text-white">{formatPct((summary.profitable_weeks / summary.total_weeks) * 100, 0)}</strong> ({summary.profitable_weeks}/{summary.total_weeks})
          </span>
          <span className="text-slate-400">
            Best week: <strong className="text-green-400">{formatUSD(summary.max_weekly_savings_usd)}</strong>
          </span>
          <span className="text-slate-400">
            Worst week: <strong className="text-red-400">{formatUSD(summary.max_weekly_loss_usd)}</strong>
          </span>
          <span className="text-slate-400">
            Forecast MAPE: <strong className="text-white">{formatPct(summary.avg_mape, 1)}</strong>
          </span>
          <span className="text-slate-400">
            R² Heating Oil: <strong className="text-white">{summary.avg_r2_heating_oil.toFixed(3)}</strong>
          </span>
          <span className="text-slate-400">
            All IFRS 9 tests: <strong className="text-green-400">{summary.h4_validated ? 'PASSED' : '—'}</strong>
          </span>
        </div>
      </div>
    </div>
  );
}
