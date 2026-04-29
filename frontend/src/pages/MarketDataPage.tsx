import { useState, useMemo } from 'react';
import { useLivePrices } from '@/hooks/useLivePrices';
import { useMarketData } from '@/hooks/useMarketData';
import { formatPrice } from '@/lib/formatters';
import { TrendingUp, TrendingDown, Minus, Activity } from 'lucide-react';

type DateRange = '7d' | '30d' | '90d' | '1y';

function getDateRange(range: DateRange): { start: string; end: string } {
  const end = new Date();
  const start = new Date();
  const days: Record<DateRange, number> = { '7d': 7, '30d': 30, '90d': 90, '1y': 365 };
  start.setDate(start.getDate() - days[range]);
  return { start: start.toISOString(), end: end.toISOString() };
}

interface CorrelationResult {
  label: string;
  r: number;
  interpretation: string;
}

function pearson(xs: number[], ys: number[]): number {
  const n = Math.min(xs.length, ys.length);
  if (n < 2) return 0;
  const mx = xs.slice(0, n).reduce((a, b) => a + b, 0) / n;
  const my = ys.slice(0, n).reduce((a, b) => a + b, 0) / n;
  let num = 0;
  let dx = 0;
  let dy = 0;
  for (let i = 0; i < n; i += 1) {
    const ex = (xs[i] ?? 0) - mx;
    const ey = (ys[i] ?? 0) - my;
    num += ex * ey;
    dx += ex * ex;
    dy += ey * ey;
  }
  return dx * dy === 0 ? 0 : num / Math.sqrt(dx * dy);
}

export function MarketDataPage() {
  const [dateRange, setDateRange] = useState<DateRange>('30d');
  const { prices, isConnected, latestTick } = useLivePrices();
  const { start, end } = getDateRange(dateRange);
  const { data: marketData, isLoading } = useMarketData(start, end);

  const latest = latestTick ?? (prices.length > 0 ? prices[prices.length - 1] : null);
  const prev = prices.length > 1 ? prices[prices.length - 2] : null;

  const priceTiles = latest ? [
    {
      label: 'Jet Fuel',
      value: latest.jet_fuel_spot,
      prev: prev?.jet_fuel_spot,
      note: 'Primary exposure',
      color: 'text-blue-400',
    },
    {
      label: 'Brent Crude',
      value: latest.brent_futures,
      prev: prev?.brent_futures,
      note: 'Macro signal',
      color: 'text-slate-300',
    },
    {
      label: 'WTI Crude',
      value: latest.wti_futures,
      prev: prev?.wti_futures,
      note: 'Macro signal',
      color: 'text-slate-300',
    },
    {
      label: 'Heating Oil (Proxy)',
      value: latest.heating_oil_futures,
      prev: prev?.heating_oil_futures,
      note: 'IFRS 9 hedge proxy',
      color: 'text-green-400',
    },
    {
      label: 'Crack Spread',
      value: latest.crack_spread,
      prev: prev?.crack_spread,
      note: 'Refinery margin',
      color: 'text-amber-400',
    },
  ] : [];

  const correlations = useMemo<CorrelationResult[]>(() => {
    const ticks = marketData?.ticks ?? prices;
    if (ticks.length < 10) return [];
    const toNum = (value: number | null | undefined): number => value ?? 0;
    const jf = ticks.map((t) => t.jet_fuel_spot);
    const ho = ticks.map((t) => toNum(t.heating_oil_futures));
    const br = ticks.map((t) => toNum(t.brent_futures));
    const wt = ticks.map((t) => toNum(t.wti_futures));

    const interpret = (r: number) => (
      Math.abs(r) >= 0.90 ? 'Very strong'
        : Math.abs(r) >= 0.80 ? 'Strong'
          : Math.abs(r) >= 0.65 ? 'Moderate' : 'Weak'
    );

    const jfHo = pearson(jf, ho);
    const jfBr = pearson(jf, br);
    const jfWt = pearson(jf, wt);

    return [
      { label: 'Jet Fuel ↔ Heating Oil', r: jfHo, interpretation: interpret(jfHo) },
      { label: 'Jet Fuel ↔ Brent Crude', r: jfBr, interpretation: interpret(jfBr) },
      { label: 'Jet Fuel ↔ WTI Crude', r: jfWt, interpretation: interpret(jfWt) },
    ];
  }, [marketData, prices]);

  const crackZscore = useMemo(() => {
    const ticks = marketData?.ticks ?? prices;
    if (ticks.length < 5) return null;
    const spreads = ticks.map((t) => t.crack_spread ?? 0);
    const mean = spreads.reduce((a, b) => a + b, 0) / spreads.length;
    const std = Math.sqrt(
      spreads.reduce((a, b) => a + (b - mean) ** 2, 0) / spreads.length
    );
    const latestSpread = spreads[spreads.length - 1] ?? 0;
    return std > 0 ? (latestSpread - mean) / std : 0;
  }, [marketData, prices]);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Market Data</h1>
          <p className="text-slate-400">
            Live fuel prices, correlations, and basis risk signals
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
          <span className="text-xs text-slate-400">
            {isConnected ? 'Live feed connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {latest && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {priceTiles.map((tile) => {
            const chg = tile.prev ? ((tile.value - tile.prev) / tile.prev) * 100 : null;
            return (
              <div key={tile.label} className="card p-4">
                <p className="text-xs text-slate-400 mb-1">{tile.label}</p>
                <p className={`text-2xl font-bold font-mono ${tile.color}`}>
                  {formatPrice(tile.value)}
                </p>
                <div className="flex items-center gap-1 mt-1">
                  {chg !== null ? (
                    <>
                      {chg > 0
                        ? <TrendingUp className="h-3 w-3 text-green-400" />
                        : chg < 0
                          ? <TrendingDown className="h-3 w-3 text-red-400" />
                          : <Minus className="h-3 w-3 text-slate-400" />}
                      <span
                        className={`text-xs font-mono ${
                          chg > 0 ? 'text-green-400' : chg < 0 ? 'text-red-400' : 'text-slate-400'
                        }`}
                      >
                        {chg > 0 ? '+' : ''}{chg.toFixed(2)}%
                      </span>
                    </>
                  ) : null}
                  <span className="text-xs text-slate-600 ml-1">{tile.note}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {correlations.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="h-5 w-5 text-blue-400" />
            <div>
              <h3 className="text-sm font-semibold text-white uppercase tracking-wide">
                Correlation Analysis
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Why heating oil is the designated IFRS 9 proxy — live Pearson R
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {correlations.map((c) => {
              const barColor = Math.abs(c.r) >= 0.80 ? 'bg-green-500'
                : Math.abs(c.r) >= 0.65 ? 'bg-amber-500' : 'bg-red-500';
              const ifrs9 = c.label.includes('Heating Oil') && Math.abs(c.r) >= 0.80;
              return (
                <div key={c.label}>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-slate-300">{c.label}</span>
                      {ifrs9 && (
                        <span className="text-xs bg-green-900 text-green-300 px-2 py-0.5 rounded-full">
                          ✓ IFRS 9 qualified
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500">{c.interpretation}</span>
                      <span className="text-sm font-mono font-bold text-white">
                        R = {c.r.toFixed(4)}
                      </span>
                    </div>
                  </div>
                  <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${barColor} transition-all duration-500`}
                      style={{ width: `${Math.abs(c.r) * 100}%` }}
                    />
                  </div>
                  {c.label.includes('Heating Oil') && (
                    <p className="text-xs text-slate-600 mt-1">
                      IFRS 9 minimum R² = 0.80 (para 6.4.1(c)).
                      {Math.abs(c.r) >= 0.80
                        ? ` Current R = ${c.r.toFixed(4)} qualifies.`
                        : ` Current R = ${c.r.toFixed(4)} is below threshold — review proxy selection.`}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {crackZscore !== null && (
        <div
          className={`card border ${
            crackZscore > 1.5 ? 'border-red-800/50 bg-red-950/10'
              : crackZscore > 0.5 ? 'border-amber-800/40 bg-amber-950/10'
                : 'border-slate-700'
          }`}
        >
          <h3 className="text-sm font-semibold text-white uppercase tracking-wide mb-3">
            Crack Spread Volatility Signal
          </h3>
          <div className="flex items-center gap-6">
            <div>
              <p className="text-3xl font-bold font-mono text-white">
                {crackZscore > 0 ? '+' : ''}{crackZscore.toFixed(2)}σ
              </p>
              <p className="text-xs text-slate-500 mt-1">
                vs. {dateRange} rolling average
              </p>
            </div>
            <div className="flex-1">
              <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    crackZscore > 1.5 ? 'bg-red-500'
                      : crackZscore > 0.5 ? 'bg-amber-500'
                        : crackZscore < -0.5 ? 'bg-blue-500' : 'bg-green-500'
                  }`}
                  style={{ width: `${Math.min(Math.max(((crackZscore + 3) / 6) * 100, 2), 100)}%` }}
                />
              </div>
              <p
                className={`text-sm mt-2 ${
                  crackZscore > 1.5 ? 'text-red-400'
                    : crackZscore > 0.5 ? 'text-amber-400'
                      : crackZscore < -0.5 ? 'text-blue-400' : 'text-green-400'
                }`}
              >
                {crackZscore > 1.5 ? '⚠ High basis risk — near-term hedging urgent'
                  : crackZscore > 0.5 ? '◈ Elevated basis risk — monitor closely'
                    : crackZscore < -0.5 ? '↓ Low basis risk — favourable hedging conditions'
                      : '✓ Normal basis risk conditions'}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white uppercase tracking-wide">
            Historical Prices
          </h3>
          <div className="flex gap-1">
            {(['7d', '30d', '90d', '1y'] as const).map((r) => (
              <button
                key={r}
                onClick={() => setDateRange(r)}
                className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-colors ${
                  dateRange === r
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'
                }`}
              >
                {r.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
          </div>
        ) : marketData && marketData.ticks.length > 0 ? (
          <div className="h-64 flex items-end gap-px overflow-hidden rounded-lg bg-slate-900/50 p-3">
            {(() => {
              const ticks = marketData.ticks.slice(-120);
              const values = ticks.map((t) => t.jet_fuel_spot);
              const min = Math.min(...values);
              const max = Math.max(...values);
              const range = max - min || 1;
              return ticks.map((t, i) => {
                const h = ((t.jet_fuel_spot - min) / range) * 100;
                const isLatest = i === ticks.length - 1;
                return (
                  <div
                    key={t.time}
                    className={`flex-1 rounded-t-sm transition-all ${
                      isLatest ? 'bg-blue-400' : 'bg-blue-600/60'
                    }`}
                    style={{ height: `${Math.max(h, 2)}%` }}
                    title={`${t.time}: $${t.jet_fuel_spot?.toFixed(2)}`}
                  />
                );
              });
            })()}
          </div>
        ) : (
          <div className="flex items-center justify-center h-64 text-slate-500">
            No data available for selected range. Load CSV to populate historical data.
          </div>
        )}

        {marketData && (
          <div className="flex justify-between text-xs text-slate-600 mt-2">
            <span>Jet Fuel spot price — last {dateRange}</span>
            <span>{marketData.ticks.length} data points</span>
          </div>
        )}
      </div>
    </div>
  );
}
