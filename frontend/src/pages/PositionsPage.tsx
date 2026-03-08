import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { cn, formatDate } from '@/lib/utils';
import { formatUSD } from '@/lib/formatters';
import { ArrowUpDown, Filter, Plus, ArrowUp, ArrowDown, Minus } from 'lucide-react';
import { usePositions, type Position } from '@/hooks/usePositions';

export function PositionsPage() {
  const [sortField, setSortField] = useState<keyof Position>('expiry_date');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState(1);
  const limit = 20;

  const { data, isLoading, error } = usePositions(true);

  const positions = data?.items ?? [];
  const portfolioPnl = data?.portfolio_pnl ?? {
    total_mtm_pnl_usd: 0,
    total_cash_savings_usd: 0,
    avg_pnl_pct: 0,
  };
  const collateralSummary = data?.collateral_summary ?? {
    total_usd: 0,
    reserves_usd: 15_000_000,
    utilization_pct: 0,
    limit_pct: 15,
    available_capacity_usd: 2_250_000,
  };

  const handleSort = (field: keyof Position) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'OPEN':
        return <Badge variant="default">Open</Badge>;
      case 'CLOSED':
        return <Badge variant="secondary">Closed</Badge>;
      case 'EXPIRED':
        return <Badge variant="warning">Expired</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const sortedPositions = [...positions].sort((a, b) => {
    const aVal = a[sortField];
    const bVal = b[sortField];
    const modifier = sortDirection === 'asc' ? 1 : -1;

    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return aVal.localeCompare(bVal) * modifier;
    }
    return ((aVal as number) - (bVal as number)) * modifier;
  });

  const paginatedPositions = sortedPositions.slice(
    (page - 1) * limit,
    page * limit
  );

  if (isLoading) {
    return (
      <div className="p-8 max-w-7xl mx-auto">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 max-w-7xl mx-auto">
        <div className="card border-red-900/50">
          <p className="text-red-400">Failed to load positions. Please try again.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Hedge Positions</h1>
          <p className="text-slate-400">
            Active and historical hedging positions across all instruments
          </p>
        </div>
        <button className="btn btn-primary flex items-center gap-2">
          <Plus className="h-4 w-4" />
          New Position
        </button>
      </div>

      {/* Collateral Meter */}
      <div className="card">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-white mb-1">
              Collateral Utilization
            </h3>
            <p className="text-sm text-slate-400">
              Total collateral posted against cash reserves
            </p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold text-white">
              {collateralSummary.utilization_pct.toFixed(2)}%
            </p>
            <p className="text-xs text-slate-400">of reserves</p>
          </div>
        </div>

        <div className="relative">
          <div className="h-4 bg-slate-800 rounded-full overflow-hidden">
            <div
              className={cn(
                'h-full transition-all duration-500',
                collateralSummary.utilization_pct >= 12
                  ? 'bg-amber-600'
                  : 'bg-primary-600'
              )}
              style={{
                width: `${Math.min(100, (collateralSummary.utilization_pct / collateralSummary.limit_pct) * 100)}%`,
              }}
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mt-4">
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
              Total Collateral
            </p>
            <p className="text-sm font-semibold text-white">
              {formatUSD(collateralSummary.total_usd)}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
              Cash Reserves
            </p>
            <p className="text-sm font-semibold text-white">
              {formatUSD(collateralSummary.reserves_usd)}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
              Available Capacity
            </p>
            <p className="text-sm font-semibold text-green-400">
              {formatUSD(collateralSummary.available_capacity_usd)}
            </p>
          </div>
        </div>
      </div>

      {/* Portfolio P&L Summary Bar */}
      {positions.length > 0 && (
        <div className="card">
          <div className="flex flex-wrap items-center gap-6">
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-400">Total Portfolio P&L:</span>
              <span
                className={cn(
                  'text-lg font-bold',
                  portfolioPnl.total_mtm_pnl_usd > 0
                    ? 'text-green-400'
                    : portfolioPnl.total_mtm_pnl_usd < 0
                      ? 'text-red-400'
                      : 'text-slate-400'
                )}
              >
                {formatUSD(portfolioPnl.total_mtm_pnl_usd)}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-400">Total Cash Savings:</span>
              <span className="text-lg font-semibold text-white">
                {formatUSD(portfolioPnl.total_cash_savings_usd)}
              </span>
              <span
                className="text-xs text-slate-500"
                title="Estimated savings vs buying at current spot price"
              >
                (vs unhedged)
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-400">Avg P&L:</span>
              <span
                className={cn(
                  'text-lg font-semibold',
                  portfolioPnl.avg_pnl_pct > 0
                    ? 'text-green-400'
                    : portfolioPnl.avg_pnl_pct < 0
                      ? 'text-red-400'
                      : 'text-slate-400'
                )}
              >
                {portfolioPnl.avg_pnl_pct >= 0 ? '+' : ''}
                {portfolioPnl.avg_pnl_pct.toFixed(2)}%
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Positions Table */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">
            {positions.length > 0 ? 'Positions' : 'Open Positions'}
          </h3>
          <button className="btn btn-secondary flex items-center gap-2 text-sm">
            <Filter className="h-4 w-4" />
            Filter
          </button>
        </div>

        {positions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-500">
            <p className="text-lg font-medium mb-2">No positions yet</p>
            <p className="text-sm text-center max-w-md">
              Hedge positions are created when you approve recommendations. Approve a
              pending recommendation to create your first position.
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>
                      <button
                        onClick={() => handleSort('instrument_type')}
                        className="flex items-center gap-1 hover:text-white"
                      >
                        Instrument
                        <ArrowUpDown className="h-3 w-3" />
                      </button>
                    </th>
                    <th>
                      <button
                        onClick={() => handleSort('proxy')}
                        className="flex items-center gap-1 hover:text-white"
                      >
                        Proxy
                        <ArrowUpDown className="h-3 w-3" />
                      </button>
                    </th>
                    <th className="text-right">
                      <button
                        onClick={() => handleSort('notional_usd')}
                        className="flex items-center gap-1 hover:text-white ml-auto"
                      >
                        Notional (USD)
                        <ArrowUpDown className="h-3 w-3" />
                      </button>
                    </th>
                    <th className="text-right">
                      <button
                        onClick={() => handleSort('hedge_ratio')}
                        className="flex items-center gap-1 hover:text-white ml-auto"
                      >
                        Hedge Ratio
                        <ArrowUpDown className="h-3 w-3" />
                      </button>
                    </th>
                    <th className="text-right">Entry Price</th>
                    <th className="text-right">
                      <span title="Mark-to-market profit/loss">MTM P&L</span>
                    </th>
                    <th className="text-right">
                      <span title="Estimated savings vs buying at current spot price">
                        Cash Savings
                      </span>
                    </th>
                    <th>
                      <button
                        onClick={() => handleSort('expiry_date')}
                        className="flex items-center gap-1 hover:text-white"
                      >
                        Expiry Date
                        <ArrowUpDown className="h-3 w-3" />
                      </button>
                    </th>
                    <th className="text-right">Collateral (USD)</th>
                    <th className="text-center">IFRS9 R²</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedPositions.map((position) => (
                    <tr key={position.id} className="cursor-pointer">
                      <td className="font-medium">{position.instrument_type}</td>
                      <td>{position.proxy}</td>
                      <td className="text-right font-semibold">
                        {formatUSD(position.notional_usd)}
                      </td>
                      <td className="text-right">
                        {(position.hedge_ratio * 100).toFixed(1)}%
                      </td>
                      <td className="text-right">
                        ${position.entry_price.toFixed(2)}
                      </td>
                      <td className="text-right">
                        <span
                          className={cn(
                            'font-semibold',
                            position.status === 'OPEN'
                              ? position.is_profitable
                                ? 'text-green-400'
                                : 'text-red-400'
                              : 'text-slate-500'
                          )}
                        >
                          {formatUSD(position.mtm_pnl_usd)}
                        </span>
                      </td>
                      <td className="text-right">
                        <span
                          title="Estimated savings vs buying at current spot price"
                          className="text-slate-300"
                        >
                          {formatUSD(position.cash_savings_usd)}
                        </span>
                      </td>
                      <td>{formatDate(position.expiry_date)}</td>
                      <td className="text-right">
                        {formatUSD(position.collateral_usd)}
                      </td>
                      <td className="text-center">
                        <span
                          className={cn(
                            'font-semibold',
                            position.ifrs9_r2 >= 0.8
                              ? 'text-green-400'
                              : 'text-red-400'
                          )}
                        >
                          {position.ifrs9_r2.toFixed(4)}
                        </span>
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          {position.status === 'OPEN' && position.is_profitable !== undefined ? (
                            <span
                              className={cn(
                                'flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded',
                                position.is_profitable
                                  ? 'bg-green-900/50 text-green-400'
                                  : 'bg-red-900/50 text-red-400'
                              )}
                            >
                              {position.is_profitable ? (
                                <>
                                  <ArrowUp className="h-3 w-3" />
                                  Profit
                                </>
                              ) : (
                                <>
                                  <ArrowDown className="h-3 w-3" />
                                  Loss
                                </>
                              )}
                            </span>
                          ) : (
                            position.status !== 'OPEN' && (
                              <span className="flex items-center gap-1 text-xs text-slate-500">
                                <Minus className="h-3 w-3" />
                                —
                              </span>
                            )
                          )}
                          {getStatusBadge(position.status)}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between mt-4 pt-4 border-t border-slate-800">
              <p className="text-sm text-slate-400">
                Showing {paginatedPositions.length} of {positions.length} positions
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="btn btn-secondary text-sm disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page * limit >= positions.length}
                  className="btn btn-secondary text-sm disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
