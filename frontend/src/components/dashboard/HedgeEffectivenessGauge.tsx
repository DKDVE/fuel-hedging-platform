import { useEffect, useMemo, useState } from 'react';
import apiClient from '@/lib/api';
import { formatBenchmarkValue } from '@/lib/formatters';

interface BasisRiskLatestResponse {
  r2_heating_oil: number;
  r2_brent: number;
  crack_spread_zscore: number;
  crack_spread_current: number;
}

const R2_MIN = 0.8;
const R2_WARN = 0.82;

export function HedgeEffectivenessGauge() {
  const [data, setData] = useState<BasisRiskLatestResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let isMounted = true;

    const fetchBasis = async () => {
      try {
        const response = await apiClient.get<BasisRiskLatestResponse>('/analytics/basis-risk/latest');
        if (isMounted) {
          setData(response.data);
          setError(false);
        }
      } catch {
        if (isMounted) {
          setError(true);
        }
      }
    };

    fetchBasis();
    const interval = window.setInterval(fetchBasis, 60_000);

    return () => {
      isMounted = false;
      window.clearInterval(interval);
    };
  }, []);

  const r2 = data?.r2_heating_oil ?? 0;
  const zScore = data?.crack_spread_zscore ?? 0;
  const r2Color = r2 >= R2_WARN ? '#22c55e' : r2 >= R2_MIN ? '#f59e0b' : '#ef4444';

  const r2Status = useMemo(() => {
    if (r2 >= R2_WARN) {
      return (
        <span className="bg-green-900 text-green-300 px-2 py-0.5 rounded-full text-xs">
          IFRS 9 Compliant
        </span>
      );
    }
    if (r2 >= R2_MIN) {
      return (
        <span className="bg-amber-900 text-amber-300 px-2 py-0.5 rounded-full text-xs">
          Warning - Monitor
        </span>
      );
    }
    return (
      <span className="bg-red-900 text-red-300 px-2 py-0.5 rounded-full text-xs">
        ⚠ Below IFRS 9 Minimum
      </span>
    );
  }, [r2]);

  const zNorm = Math.min(Math.max((zScore + 3) / 6, 0), 1);
  const zSignal = useMemo(() => {
    if (zScore > 1.5) {
      return {
        fill: 'bg-red-500',
        text: 'High basis risk: near-term hedging urgent',
      };
    }
    if (zScore > 0.5) {
      return {
        fill: 'bg-amber-500',
        text: 'Elevated basis risk: monitor closely',
      };
    }
    if (zScore < -0.5) {
      return {
        fill: 'bg-blue-500',
        text: 'Low basis risk: favourable hedging conditions',
      };
    }
    return {
      fill: 'bg-green-500',
      text: 'Normal basis risk conditions',
    };
  }, [zScore]);

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-white uppercase tracking-wide">
            Hedge Effectiveness Monitor
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">Live proxy quality and basis-risk signal</p>
        </div>
        {error && (
          <span className="text-xs text-red-400 border border-red-800/40 rounded-full px-2 py-0.5">
            Data unavailable
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-3">R² Gauge (Heating Oil Proxy)</p>
          <div className="flex items-center gap-4">
            <svg viewBox="0 0 120 70" className="w-36 h-20">
              <path d="M 10 60 A 50 50 0 0 1 110 60" fill="none" stroke="#334155" strokeWidth="10" />
              <path
                d="M 10 60 A 50 50 0 0 1 110 60"
                fill="none"
                stroke={r2Color}
                strokeWidth="10"
                strokeDasharray={`${Math.max(Math.min((r2 / 1) * 157, 157), 0)} 157`}
                strokeLinecap="round"
              />
            </svg>
            <div>
              <p className="text-3xl font-bold font-mono" style={{ color: r2Color }}>
                {formatBenchmarkValue(r2, 'ratio')}
              </p>
              <div className="mt-1">{r2Status}</div>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-3">Crack Spread Z-Score Signal</p>
          <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
            <span>-3</span>
            <span className="font-mono text-slate-300">{formatBenchmarkValue(zScore, 'ratio')}</span>
            <span>+3</span>
          </div>
          <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
            <div className={`h-full ${zSignal.fill} rounded-full`} style={{ width: `${zNorm * 100}%` }} />
          </div>
          <p className="text-xs text-slate-400 mt-2">{zSignal.text}</p>
        </div>
      </div>

      <p className="text-xs text-slate-500 mt-4">
        R² updated each pipeline run (~daily). Z-score from live price feed. R² ≥ 0.80 required for IFRS 9
        hedge accounting designation.
      </p>
    </div>
  );
}
