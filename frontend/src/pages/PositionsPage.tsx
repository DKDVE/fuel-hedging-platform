import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { cn, formatDate } from '@/lib/utils';
import { formatUSD } from '@/lib/formatters';
import { ArrowUpDown, Filter, Plus, ArrowUp, ArrowDown, Minus, Calendar, X } from 'lucide-react';
import { usePositions, type Position } from '@/hooks/usePositions';
import apiClient from '@/lib/api';
import { toast } from 'sonner';

interface MonthlyCollateral {
  monthKey: string;
  monthLabel: string;
  positions: {
    id: string;
    instrument: string;
    collateral: number;
    expiry: string;
    status: string;
  }[];
  totalCollateral: number;
}

function buildCollateralCalendar(positions: import('@/hooks/usePositions').Position[]): MonthlyCollateral[] {
  const map = new Map<string, MonthlyCollateral>();

  positions
    .filter((p) => p.status === 'OPEN' && p.collateral_usd > 0)
    .forEach((p) => {
      const d = new Date(p.expiry_date);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
      const label = d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });

      if (!map.has(key)) {
        map.set(key, { monthKey: key, monthLabel: label, positions: [], totalCollateral: 0 });
      }
      const entry = map.get(key);
      if (!entry) return;

      entry.positions.push({
        id: p.id,
        instrument: p.instrument_type,
        collateral: p.collateral_usd,
        expiry: p.expiry_date,
        status: p.status,
      });
      entry.totalCollateral += p.collateral_usd;
    });

  return Array.from(map.values())
    .sort((a, b) => a.monthKey.localeCompare(b.monthKey))
    .slice(0, 6);
}

export function PositionsPage() {
  const queryClient = useQueryClient();
  const [sortField, setSortField] = useState<keyof Position>('expiry_date');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState(1);
  const [calendarExpanded, setCalendarExpanded] = useState(false);
  const [showNewPositionForm, setShowNewPositionForm] = useState(false);
  const [newPosition, setNewPosition] = useState({
    instrument_type: 'FUTURES',
    proxy: 'heating_oil',
    notional_usd: '',
    hedge_ratio: '65',
    entry_price: '',
    expiry_date: '',
    collateral_usd: '',
    ifrs9_r2: '0.8517',
  });
  const [submitting, setSubmitting] = useState(false);
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
  const calendar = buildCollateralCalendar(positions);
  const maxMonthlyCollateral = Math.max(...calendar.map((m) => m.totalCollateral), 1);

  const handleCreatePosition = async () => {
    if (!newPosition.notional_usd || !newPosition.entry_price || !newPosition.expiry_date) {
      toast.error('Please fill in all required fields.');
      return;
    }
    setSubmitting(true);
    try {
      await apiClient.post('/positions', {
        ...newPosition,
        notional_usd: parseFloat(newPosition.notional_usd),
        hedge_ratio: parseFloat(newPosition.hedge_ratio) / 100,
        entry_price: parseFloat(newPosition.entry_price),
        collateral_usd: parseFloat(newPosition.collateral_usd || '0'),
        ifrs9_r2: parseFloat(newPosition.ifrs9_r2),
      });
      toast.success('Position created successfully.');
      setShowNewPositionForm(false);
      queryClient.invalidateQueries({ queryKey: ['positions'] });
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      toast.error(e.response?.data?.detail ?? 'Failed to create position.');
    } finally {
      setSubmitting(false);
    }
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
        <button
          onClick={() => setShowNewPositionForm(true)}
          className="btn btn-primary flex items-center gap-2"
        >
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

      {/* Collateral Cash Flow Calendar */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <Calendar className="h-5 w-5 text-blue-400" />
              Collateral Cash Flow Calendar
            </h3>
            <p className="text-sm text-slate-400 mt-1">
              Upcoming collateral obligations by expiry month
            </p>
          </div>
          <button
            onClick={() => setCalendarExpanded((e) => !e)}
            className="text-xs text-slate-400 hover:text-white border border-slate-700
                       rounded-lg px-3 py-1.5 transition-colors"
          >
            {calendarExpanded ? 'Collapse' : 'Expand'}
          </button>
        </div>

        {calendar.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            <p className="text-sm">No open positions with future collateral obligations.</p>
            <p className="text-xs mt-1 text-slate-600">
              Approve a recommendation to create positions and see collateral scheduling.
            </p>
          </div>
        ) : (
          <>
            <div className="flex items-end gap-3 mb-4 overflow-x-auto pb-2">
              {calendar.map((month) => {
                const barPct = (month.totalCollateral / maxMonthlyCollateral) * 100;
                const isCurrentMonth = month.monthKey ===
                  `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`;
                return (
                  <div
                    key={month.monthKey}
                    className="flex flex-col items-center gap-1 min-w-[80px]"
                  >
                    <span className="text-xs text-slate-400 font-mono whitespace-nowrap">
                      {formatUSD(month.totalCollateral)}
                    </span>
                    <div className="w-full flex items-end" style={{ height: '80px' }}>
                      <div
                        className={`w-full rounded-t-sm transition-all duration-500 ${
                          isCurrentMonth ? 'bg-amber-500' : 'bg-blue-600'
                        }`}
                        style={{ height: `${Math.max(barPct, 4)}%` }}
                      />
                    </div>
                    <span
                      className={`text-xs font-medium ${
                        isCurrentMonth ? 'text-amber-400' : 'text-slate-400'
                      }`}
                    >
                      {month.monthLabel}
                    </span>
                    <span className="text-xs text-slate-600">
                      {month.positions.length} pos.
                    </span>
                  </div>
                );
              })}
            </div>

            {calendar.some((m) => m.totalCollateral > 1_000_000) && (
              <div className="rounded-lg bg-amber-950/20 border border-amber-800/30 p-3 mb-3">
                <p className="text-xs text-amber-400">
                  ⚠ One or more months have collateral obligations exceeding $1M.
                  Ensure adequate cash reserves are available before those expiry dates.
                </p>
              </div>
            )}

            {calendarExpanded && (
              <div className="border-t border-slate-700 pt-4 space-y-3">
                {calendar.map((month) => (
                  <div key={month.monthKey}>
                    <p className="text-xs text-slate-400 uppercase tracking-wide mb-2">
                      {month.monthLabel} — {formatUSD(month.totalCollateral)} total
                    </p>
                    <div className="space-y-1">
                      {month.positions.map((pos) => (
                        <div
                          key={pos.id}
                          className="flex items-center justify-between text-sm
                                     bg-slate-800/50 rounded-lg px-3 py-2"
                        >
                          <span className="text-slate-300 capitalize">
                            {pos.instrument.toLowerCase()} — expires {pos.expiry}
                          </span>
                          <span className="font-mono text-white">
                            {formatUSD(pos.collateral)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        <p className="text-xs text-slate-600 mt-4">
          Shows OPEN positions only. Amber bars indicate the current month.
          Collateral amounts from approved position records.
        </p>
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

      {showNewPositionForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center
                        bg-black/60 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl
                          shadow-2xl w-full max-w-lg mx-4 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-white">New Hedge Position</h2>
              <button
                onClick={() => setShowNewPositionForm(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1.5 uppercase tracking-wide">
                  Instrument Type *
                </label>
                <select
                  value={newPosition.instrument_type}
                  onChange={(e) => setNewPosition((p) => ({ ...p, instrument_type: e.target.value }))}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg
                             px-3 py-2 text-white text-sm focus:outline-none
                             focus:border-blue-500"
                >
                  {['FUTURES', 'OPTIONS', 'COLLAR', 'SWAP'].map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1.5 uppercase tracking-wide">
                  Proxy Instrument *
                </label>
                <select
                  value={newPosition.proxy}
                  onChange={(e) => setNewPosition((p) => ({ ...p, proxy: e.target.value }))}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg
                             px-3 py-2 text-white text-sm focus:outline-none
                             focus:border-blue-500"
                >
                  <option value="heating_oil">Heating Oil (HO=F) — Recommended</option>
                  <option value="brent">Brent Crude (BZ=F)</option>
                  <option value="wti">WTI Crude (CL=F)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5 uppercase tracking-wide">
                    Notional (USD) *
                  </label>
                  <input
                    type="number"
                    placeholder="5000000"
                    value={newPosition.notional_usd}
                    onChange={(e) => setNewPosition((p) => ({ ...p, notional_usd: e.target.value }))}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg
                               px-3 py-2 text-white text-sm focus:outline-none
                               focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5 uppercase tracking-wide">
                    Entry Price ($/bbl) *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="9.52"
                    value={newPosition.entry_price}
                    onChange={(e) => setNewPosition((p) => ({ ...p, entry_price: e.target.value }))}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg
                               px-3 py-2 text-white text-sm focus:outline-none
                               focus:border-blue-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5 uppercase tracking-wide">
                    Hedge Ratio (%)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="80"
                    value={newPosition.hedge_ratio}
                    onChange={(e) => setNewPosition((p) => ({ ...p, hedge_ratio: e.target.value }))}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg
                               px-3 py-2 text-white text-sm focus:outline-none
                               focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5 uppercase tracking-wide">
                    Expiry Date *
                  </label>
                  <input
                    type="date"
                    value={newPosition.expiry_date}
                    onChange={(e) => setNewPosition((p) => ({ ...p, expiry_date: e.target.value }))}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg
                               px-3 py-2 text-white text-sm focus:outline-none
                               focus:border-blue-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5 uppercase tracking-wide">
                    Collateral (USD)
                  </label>
                  <input
                    type="number"
                    placeholder="100000"
                    value={newPosition.collateral_usd}
                    onChange={(e) => setNewPosition((p) => ({ ...p, collateral_usd: e.target.value }))}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg
                               px-3 py-2 text-white text-sm focus:outline-none
                               focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5 uppercase tracking-wide">
                    IFRS 9 R²
                  </label>
                  <input
                    type="number"
                    step="0.0001"
                    min="0"
                    max="1"
                    value={newPosition.ifrs9_r2}
                    onChange={(e) => setNewPosition((p) => ({ ...p, ifrs9_r2: e.target.value }))}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg
                               px-3 py-2 text-white text-sm focus:outline-none
                               focus:border-blue-500"
                  />
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowNewPositionForm(false)}
                className="flex-1 btn btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleCreatePosition}
                disabled={submitting}
                className="flex-1 btn btn-primary disabled:opacity-60"
              >
                {submitting ? 'Creating...' : 'Create Position'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
