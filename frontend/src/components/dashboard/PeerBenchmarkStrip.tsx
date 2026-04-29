import { AIRLINE_PROFILES } from '@/data/industryBenchmarks';
import { formatPct } from '@/lib/formatters';

interface PeerBenchmarkStripProps {
  ourHR: number;
}

function parseCoverageMidpoint(coverage: string): number {
  const match = coverage.match(/(\d+)[–-](\d+)/);
  if (match?.[1] && match?.[2]) {
    return (parseInt(match[1], 10) + parseInt(match[2], 10)) / 2;
  }
  const single = coverage.match(/(\d+)%/);
  if (single?.[1]) return parseInt(single[1], 10);
  return 0;
}

function abbreviateAirlineName(name: string): string {
  return name
    .replace(' Airlines', '')
    .replace(' Air Lines', '')
    .replace(' Platform (Demo)', 'Platform')
    .trim();
}

export function PeerBenchmarkStrip({ ourHR }: PeerBenchmarkStripProps) {
  const peers = AIRLINE_PROFILES.slice(0, 5).map((airline) => {
    const coveragePct =
      airline.name === 'This Platform (Demo)'
        ? Math.max(Math.min(ourHR * 100, 100), 0)
        : parseCoverageMidpoint(airline.typicalCoverage);
    return {
      name: airline.name,
      displayName: abbreviateAirlineName(airline.name),
      coveragePct,
      isPlatform: airline.name === 'This Platform (Demo)',
    };
  });

  return (
    <div className="card">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-white uppercase tracking-wide">
          Industry Benchmark
        </h3>
        <p className="text-xs text-slate-500 mt-0.5">
          Where your hedge ratio stands vs. named carriers
        </p>
      </div>

      <div className="relative rounded-xl border border-slate-700 bg-slate-900/50 p-4 overflow-x-auto">
        <div className="absolute inset-x-4 top-[32%] border-t border-dashed border-slate-600 pointer-events-none" />
        <div className="absolute inset-x-4 top-[48%] border-t border-dashed border-slate-600 pointer-events-none" />
        <div className="absolute right-2 top-[30%] text-[10px] text-slate-500 pointer-events-none">80%</div>
        <div className="absolute right-2 top-[46%] text-[10px] text-slate-500 pointer-events-none">60%</div>
        <div className="absolute right-2 top-[38%] text-[10px] text-slate-500 pointer-events-none">
          Optimal zone 60-80%
        </div>

        <div className="flex items-end gap-6 min-w-[520px] h-48">
          {peers.map((peer) => (
            <div key={peer.name} className="flex flex-col items-center w-20">
              <div className="h-32 flex items-end mb-2">
                <div
                  className={`w-8 rounded-t-md ${peer.isPlatform ? 'bg-blue-500' : 'bg-slate-600'}`}
                  style={{ height: `${Math.max(Math.min(peer.coveragePct, 100), 4)}%` }}
                />
              </div>
              <p className="text-xs text-slate-300 text-center leading-tight">{peer.displayName}</p>
              <p className={`text-xs font-mono ${peer.isPlatform ? 'text-blue-300' : 'text-slate-400'}`}>
                {formatPct(peer.coveragePct, 0)}
              </p>
            </div>
          ))}
        </div>
      </div>

      <p className="text-xs text-slate-500 mt-3">
        Source: Public airline annual reports & Reuters (March 2026). Peer values are typical ranges, not
        point-in-time figures.
      </p>
    </div>
  );
}
