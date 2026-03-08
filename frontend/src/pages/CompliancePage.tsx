import { useComplianceSummary } from '@/hooks/useComplianceSummary';
import { CheckCircle2, AlertTriangle, XCircle, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

function StatusBadge({ status }: { status: string }) {
  const config = {
    COMPLIANT: { icon: CheckCircle2, className: 'text-green-400 bg-green-900/30', label: 'COMPLIANT' },
    WARNING: { icon: AlertTriangle, className: 'text-amber-400 bg-amber-900/30', label: 'WARNING' },
    BREACH: { icon: XCircle, className: 'text-red-400 bg-red-900/30', label: 'BREACH' },
    NO_DATA: { icon: Info, className: 'text-gray-400 bg-gray-800', label: 'NO DATA' },
    EFFECTIVE: { icon: CheckCircle2, className: 'text-green-400 bg-green-900/30', label: 'EFFECTIVE' },
    MONITOR: { icon: AlertTriangle, className: 'text-amber-400 bg-amber-900/30', label: 'MONITOR' },
    INEFFECTIVE: { icon: XCircle, className: 'text-red-400 bg-red-900/30', label: 'INEFFECTIVE' },
  };
  const c = config[status as keyof typeof config] ?? config.NO_DATA;
  const Icon = c.icon;
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium', c.className)}>
      <Icon className="w-3.5 h-3.5" />
      {c.label}
    </span>
  );
}

function StatusIcon({ status }: { status: string }) {
  if (status === 'COMPLIANT') return <CheckCircle2 className="w-5 h-5 text-green-400" />;
  if (status === 'WARNING') return <AlertTriangle className="w-5 h-5 text-amber-400" />;
  return <XCircle className="w-5 h-5 text-red-400" />;
}

export function CompliancePage() {
  const { data, isLoading, error } = useComplianceSummary();

  if (isLoading) {
    return (
      <div className="p-8 max-w-7xl mx-auto">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 max-w-7xl mx-auto">
        <div className="card border-red-900/50">
          <p className="text-red-400">Failed to load compliance data. Please try again.</p>
        </div>
      </div>
    );
  }

  const { ifrs9, internal_limits, trade_reporting } = data;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-10">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Regulatory Compliance</h1>
        <p className="text-slate-400">
          IFRS 9 hedge accounting, internal risk limits, and trade reporting status
        </p>
      </div>

      {/* Section 1 — IFRS 9 Status */}
      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h2 className="text-xl font-semibold text-white">IFRS 9 Hedge Accounting</h2>
          <StatusBadge status={ifrs9.overall_status} />
        </div>
        <p className="text-sm text-slate-400">
          Last tested: {ifrs9.last_test_date} | Next due: {ifrs9.next_test_due}{' '}
          ({ifrs9.days_until_next_test} days)
        </p>

        <div className="overflow-x-auto rounded-xl border border-slate-700">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 bg-slate-900/50">
                <th className="text-left py-3 px-4 text-slate-300 font-medium">Position</th>
                <th className="text-left py-3 px-4 text-slate-300 font-medium">Instrument</th>
                <th className="text-left py-3 px-4 text-slate-300 font-medium">Proxy</th>
                <th className="text-right py-3 px-4 text-slate-300 font-medium">R² (30d)</th>
                <th className="text-right py-3 px-4 text-slate-300 font-medium">R² (90d)</th>
                <th className="text-right py-3 px-4 text-slate-300 font-medium">Retro Ratio</th>
                <th className="text-left py-3 px-4 text-slate-300 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {ifrs9.positions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    No open hedge positions to test
                  </td>
                </tr>
              ) : (
                ifrs9.positions.map((pos) => (
                  <tr
                    key={pos.position_id}
                    className={cn(
                      'border-b border-slate-800 transition-colors',
                      pos.effectiveness_status === 'EFFECTIVE' && 'border-l-4 border-l-green-600',
                      pos.effectiveness_status === 'MONITOR' && 'border-l-4 border-l-amber-600',
                      pos.effectiveness_status === 'INEFFECTIVE' && 'border-l-4 border-l-red-600'
                    )}
                  >
                    <td className="py-3 px-4 font-mono text-slate-300">#{pos.position_id}</td>
                    <td className="py-3 px-4 text-slate-300">{pos.instrument}</td>
                    <td className="py-3 px-4 text-slate-300">{pos.proxy}</td>
                    <td className="py-3 px-4 text-right font-mono text-slate-300">{pos.r2_30d.toFixed(4)}</td>
                    <td className="py-3 px-4 text-right font-mono text-slate-300">{pos.r2_90d.toFixed(4)}</td>
                    <td className="py-3 px-4 text-right font-mono text-slate-300">
                      {(pos.retrospective_ratio * 100).toFixed(1)}%
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={pos.effectiveness_status} />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <p className="text-xs text-slate-500 flex items-start gap-2">
          <Info className="w-4 h-4 flex-shrink-0 mt-0.5" />
          IFRS 9 para 6.4.1(c) requires R² ≥ 0.80 for prospective effectiveness. Para B6.4.14
          requires retrospective offset ratio within 80%–125%.
        </p>
      </section>

      {/* Section 2 — Internal Risk Limits */}
      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <h2 className="text-xl font-semibold text-white">Internal Risk Limits</h2>
          <StatusBadge status={internal_limits.overall_status} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {internal_limits.limits.map((limit) => (
            <div
              key={limit.limit_name}
              className={cn(
                'p-4 rounded-xl border',
                limit.status === 'BREACH' && 'border-red-600 bg-red-950/20',
                limit.status === 'WARNING' && 'border-amber-600 bg-amber-950/20',
                (limit.status === 'COMPLIANT' || limit.status === 'NO_DATA') && 'border-slate-700 bg-slate-900'
              )}
            >
              <div className="flex justify-between items-start mb-2">
                <p className="font-medium text-white text-sm">{limit.limit_name}</p>
                <StatusBadge status={limit.status} />
              </div>
              <div className="h-2 bg-slate-700 rounded-full overflow-hidden mb-2">
                <div
                  className={cn(
                    'h-full rounded-full transition-all',
                    limit.status === 'BREACH' && 'bg-red-500',
                    limit.status === 'WARNING' && 'bg-amber-500',
                    (limit.status === 'COMPLIANT' || limit.status === 'NO_DATA') && 'bg-green-500'
                  )}
                  style={{ width: `${Math.min(limit.utilisation_pct, 100)}%` }}
                />
              </div>
              <div className="flex justify-between text-xs text-slate-400">
                <span>
                  Current: <strong className="text-white">{limit.display_current}</strong>
                </span>
                <span>Limit: {limit.display_limit}</span>
                <span>{limit.utilisation_pct.toFixed(0)}% utilised</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Section 3 — Trade Reporting Checklist */}
      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <h2 className="text-xl font-semibold text-white">Dodd-Frank / EMIR Trade Reporting</h2>
          <span className="text-xs text-slate-500 italic">(Simulated — demonstration purposes only)</span>
        </div>

        <div className="overflow-x-auto rounded-xl border border-slate-700">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 bg-slate-900/50">
                <th className="w-10 py-3 px-4"></th>
                <th className="text-left py-3 px-4 text-slate-300 font-medium">Requirement</th>
                <th className="text-left py-3 px-4 text-slate-300 font-medium">Description</th>
                <th className="text-left py-3 px-4 text-slate-300 font-medium">Reference</th>
                <th className="text-left py-3 px-4 text-slate-300 font-medium">Next Due</th>
              </tr>
            </thead>
            <tbody>
              {trade_reporting.checklist.map((item, idx) => (
                <tr key={idx} className="border-b border-slate-800">
                  <td className="py-3 px-4">
                    <StatusIcon status={item.status} />
                  </td>
                  <td className="py-3 px-4 font-medium text-white">{item.requirement}</td>
                  <td className="py-3 px-4 text-slate-400">{item.description}</td>
                  <td className="py-3 px-4 text-xs font-mono text-slate-500">{item.reference}</td>
                  <td className="py-3 px-4 text-xs text-slate-400">
                    {item.next_due ?? item.last_reconciled ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
