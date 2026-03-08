import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { getApiBaseUrl } from '@/lib/api';
import { cn, formatDate } from '@/lib/utils';
import { Download, Calendar, Filter } from 'lucide-react';
import { useApprovals } from '@/hooks/useAudit';
import { toast } from 'sonner';

export function AuditLogPage() {
  const [activeTab, setActiveTab] = useState<'approvals' | 'ifrs9'>('approvals');
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [days, setDays] = useState(30);
  const [exporting, setExporting] = useState(false);

  const { data: approvalsData, isLoading, error } = useApprovals(days);
  const approvals = approvalsData?.items ?? [];

  const handleExportCSV = async () => {
    setExporting(true);
    try {
      const params = new URLSearchParams();
      if (dateRange.start) params.set('date_from', dateRange.start);
      if (dateRange.end) params.set('date_to', dateRange.end);

      const response = await fetch(`${getApiBaseUrl()}/audit/export?${params}`, {
        credentials: 'include',
      });
      if (!response.ok) throw new Error('Export failed');
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_log_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Audit log exported');
    } catch {
      toast.error('Failed to export audit log');
    } finally {
      setExporting(false);
    }
  };

  const getDecisionBadge = (decision: string) => {
    switch (decision) {
      case 'APPROVE':
        return <Badge variant="success">Approved</Badge>;
      case 'REJECT':
        return <Badge variant="destructive">Rejected</Badge>;
      case 'DEFER':
        return <Badge variant="warning">Deferred</Badge>;
      default:
        return <Badge variant="outline">{decision}</Badge>;
    }
  };

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
          <p className="text-red-400">Failed to load audit data. Please try again.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Audit Log</h1>
          <p className="text-slate-400">
            Complete audit trail of approvals and IFRS 9 compliance
          </p>
        </div>
        <button
          onClick={handleExportCSV}
          disabled={exporting}
          className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-600 text-white rounded-lg text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Download className="h-4 w-4" />
          {exporting ? 'Exporting…' : 'Export CSV'}
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-800">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('approvals')}
            className={cn(
              'py-4 px-1 border-b-2 font-medium text-sm transition-colors',
              activeTab === 'approvals'
                ? 'border-primary-500 text-primary-400'
                : 'border-transparent text-slate-400 hover:text-slate-300 hover:border-slate-700'
            )}
          >
            Approval History
          </button>
          <button
            onClick={() => setActiveTab('ifrs9')}
            className={cn(
              'py-4 px-1 border-b-2 font-medium text-sm transition-colors',
              activeTab === 'ifrs9'
                ? 'border-primary-500 text-primary-400'
                : 'border-transparent text-slate-400 hover:text-slate-300 hover:border-slate-700'
            )}
          >
            IFRS 9 Compliance
          </button>
        </nav>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 flex-1">
            <Calendar className="h-4 w-4 text-slate-400" />
            <input
              type="date"
              value={dateRange.start}
              onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
              className="input text-sm"
              placeholder="Start date"
            />
            <span className="text-slate-500">to</span>
            <input
              type="date"
              value={dateRange.end}
              onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
              className="input text-sm"
              placeholder="End date"
            />
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="input text-sm"
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          </div>
          <button className="btn btn-secondary flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Apply Filters
          </button>
        </div>
      </div>

      {/* Approval History Table */}
      {activeTab === 'approvals' && (
        <div className="card">
          <h3 className="text-lg font-semibold text-white mb-4">
            Recommendation Approvals
          </h3>
          {approvals.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-500">
              <p className="text-lg font-medium mb-2">No approval records yet</p>
              <p className="text-sm text-center max-w-md">
                Approval history will appear here when recommendations are approved,
                rejected, or deferred.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Recomm. #</th>
                    <th>Approver</th>
                    <th>Role</th>
                    <th>Decision</th>
                    <th>Reason</th>
                    <th className="text-right">Response Time</th>
                  </tr>
                </thead>
                <tbody>
                  {approvals.map((record) => (
                    <tr key={record.id}>
                      <td className="font-medium">
                        {record.date ? formatDate(record.date) : '—'}
                      </td>
                      <td className="font-mono text-xs">{record.recommendation_id}</td>
                      <td>{record.approver}</td>
                      <td>
                        <span className="text-xs text-slate-400">{record.role}</span>
                      </td>
                      <td>{getDecisionBadge(record.decision)}</td>
                      <td className="max-w-xs truncate">
                        {record.reason || (
                          <span className="text-slate-500 italic">—</span>
                        )}
                      </td>
                      <td className="text-right">
                        <span className="text-slate-300">
                          {Math.floor(record.response_time_mins / 60)}h{' '}
                          {record.response_time_mins % 60}m
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* IFRS9 Compliance Table - no API yet, show empty state */}
      {activeTab === 'ifrs9' && (
        <div className="card">
          <h3 className="text-lg font-semibold text-white mb-4">
            IFRS 9 Hedge Accounting Compliance
          </h3>
          <div className="flex flex-col items-center justify-center py-16 text-slate-500">
            <p className="text-lg font-medium mb-2">No IFRS 9 data available</p>
            <p className="text-sm text-center max-w-md">
              IFRS 9 compliance records will appear when the analytics pipeline completes
              and hedge designations are evaluated.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
