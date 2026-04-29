import { useState } from 'react';
import { ApprovalWorkflowCard } from '@/components/recommendations/ApprovalWorkflowCard';
import { InstrumentMixChart } from '@/components/recommendations/InstrumentMixChart';
import { AgentDetailsAccordion } from '@/components/recommendations/AgentDetailsAccordion';
import { ExplainabilityPanel } from '@/components/recommendations/ExplainabilityPanel';
import { TimelineAuditTrail } from '@/components/recommendations/TimelineAuditTrail';
import {
  useRecommendations,
  usePendingRecommendations,
  useApproveRecommendation,
  useRejectRecommendation,
  useDeferRecommendation,
} from '@/hooks/useRecommendations';
import { usePermissions } from '@/hooks/usePermissions';
import { AlertCircle, Filter } from 'lucide-react';
import { cn } from '@/lib/utils';

export function RecommendationsPage() {
  const [activeTab, setActiveTab] = useState<'pending' | 'all'>('pending');
  const [page, setPage] = useState(1);

  const { hasPermission } = usePermissions();
  const canApprove = hasPermission('approve:recommendation');

  const { data: pendingData, isLoading: pendingLoading } = usePendingRecommendations();
  const { data: allData, isLoading: allLoading } = useRecommendations(page, 10);

  const approveMutation = useApproveRecommendation();
  const rejectMutation = useRejectRecommendation();
  const deferMutation = useDeferRecommendation();

  // Mock agent analysis data - replace with actual API call
  const mockAgents = [
    {
      agent_id: 'basis_risk',
      risk_level: 'LOW' as const,
      recommendation: 'Heating oil correlation remains strong at R²=0.85. Hedge effectiveness is within acceptable bounds.',
      metrics: {
        r2_heating_oil: 0.8517,
        correlation_coefficient: 0.9229,
        hedge_effectiveness: 0.8234,
      },
      constraints_satisfied: true,
      ifrs9_eligible: true,
    },
    {
      agent_id: 'liquidity',
      risk_level: 'MODERATE' as const,
      recommendation: 'Collateral utilization at 12.5% of reserves. Monitor closely as approaching 15% limit.',
      metrics: {
        collateral_utilization: 0.125,
        available_capacity: 0.025,
        margin_calls: 0,
      },
      constraints_satisfied: true,
      ifrs9_eligible: null,
    },
    {
      agent_id: 'operational',
      risk_level: 'LOW' as const,
      recommendation: 'All systems operational. Data feeds stable from EIA, CME, and ICE sources.',
      metrics: {
        system_uptime: 0.9987,
        data_quality_score: 0.98,
        api_latency_ms: 145,
      },
      constraints_satisfied: true,
      ifrs9_eligible: null,
    },
    {
      agent_id: 'ifrs9',
      risk_level: 'LOW' as const,
      recommendation: 'Hedge accounting requirements satisfied. Prospective R²=0.85 and retrospective ratio=0.92 both within bounds.',
      metrics: {
        prospective_r2: 0.8517,
        retrospective_ratio: 0.9234,
        dollar_offset_ratio: 0.9123,
      },
      constraints_satisfied: true,
      ifrs9_eligible: true,
    },
    {
      agent_id: 'macro',
      risk_level: 'MODERATE' as const,
      recommendation: 'Geopolitical tensions in Middle East may impact crude prices. Consider increasing hedge ratio to 75%.',
      metrics: {
        volatility_index: 28.5,
        brent_wti_spread: 2.34,
        crack_spread_volatility: 15.2,
      },
      constraints_satisfied: true,
      ifrs9_eligible: null,
    },
  ];

  const handleApprove = async (
    id: string,
    comments?: string,
    customHR?: number,
    customMix?: Record<string, number>,
  ) => {
    try {
      await approveMutation.mutateAsync({
        id,
        data: {
          comments: comments || undefined,
          custom_hedge_ratio: customHR,
          custom_instrument_mix: customMix,
        },
      });
    } catch (error) {
      console.error('Approve failed:', error);
    }
  };

  const handleReject = async (id: string, reason: string) => {
    try {
      await rejectMutation.mutateAsync({
        id,
        data: { reason },
      });
    } catch (error) {
      console.error('Reject failed:', error);
    }
  };

  const handleDefer = async (id: string, reason: string) => {
    try {
      await deferMutation.mutateAsync({
        id,
        data: { reason },
      });
    } catch (error) {
      console.error('Defer failed:', error);
    }
  };

  const isLoading = activeTab === 'pending' ? pendingLoading : allLoading;
  const recommendations = activeTab === 'pending' ? pendingData : allData?.items;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Hedge Recommendations</h1>
          <p className="text-slate-400">
            Review and approve AI-generated hedging strategies
          </p>
        </div>
        {!canApprove && (
          <div className="flex items-center gap-2 px-4 py-2 bg-amber-950/30 border border-amber-800 rounded-lg text-amber-400">
            <AlertCircle className="h-4 w-4" />
            <span className="text-sm font-medium">View Only</span>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-800">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('pending')}
            className={cn(
              'py-4 px-1 border-b-2 font-medium text-sm transition-colors',
              activeTab === 'pending'
                ? 'border-primary-500 text-primary-400'
                : 'border-transparent text-slate-400 hover:text-slate-300 hover:border-slate-700'
            )}
          >
            Pending Approval
            {pendingData && pendingData.length > 0 && (
              <span className="ml-2 bg-primary-600 text-white py-0.5 px-2 rounded-full text-xs font-semibold">
                {pendingData.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('all')}
            className={cn(
              'py-4 px-1 border-b-2 font-medium text-sm transition-colors',
              activeTab === 'all'
                ? 'border-primary-500 text-primary-400'
                : 'border-transparent text-slate-400 hover:text-slate-300 hover:border-slate-700'
            )}
          >
            All Recommendations
          </button>
        </nav>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      )}

      {/* Content */}
      {!isLoading && recommendations && recommendations.length > 0 && (
        <div className="space-y-6">
          {recommendations.map((rec) => (
            <div key={rec.id} className="space-y-6">
              {/* Approval Workflow Card */}
              <ApprovalWorkflowCard
                recommendation={rec}
                onApprove={(comments, customHR, customMix) =>
                  handleApprove(rec.id, comments, customHR, customMix)
                }
                onReject={(reason) => handleReject(rec.id, reason)}
                onDefer={(reason) => handleDefer(rec.id, reason)}
                canApprove={canApprove}
                isSubmitting={
                  approveMutation.isPending ||
                  rejectMutation.isPending ||
                  deferMutation.isPending
                }
              />

              {/* Two-column layout for charts and details */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Instrument Mix Chart */}
                <InstrumentMixChart instrumentMix={rec.instrument_mix} />

                {/* Agent Details Accordion — use actual agent_outputs when available */}
                <AgentDetailsAccordion
                  agents={
                    (rec.agent_outputs ?? mockAgents).map((a) => ({
                      agent_id: a.agent_id,
                      risk_level: a.risk_level,
                      recommendation: a.recommendation,
                      metrics: (a.metrics ?? {}) as Record<string, number>,
                      constraints_satisfied: a.constraints_satisfied ?? true,
                      ifrs9_eligible: (a as { ifrs9_eligible?: boolean | null }).ifrs9_eligible ?? null,
                    }))
                  }
                />
              </div>

              {/* Explainability Panel — AI committee reasoning */}
              <ExplainabilityPanel
                agentOutputs={
                  (rec.agent_outputs ?? mockAgents).map((a) => ({
                    agent_id: a.agent_id,
                    risk_level: a.risk_level,
                    recommendation: a.recommendation,
                    metrics: a.metrics ?? {},
                    constraints_satisfied: a.constraints_satisfied ?? true,
                  }))
                }
                consensusRiskLevel={rec.risk_level}
                approvedForPresentation={rec.status !== 'CONSTRAINT_VIOLATED'}
              />

              {/* Timeline Audit Trail */}
              {'approvals' in rec && rec.approvals && (
                <TimelineAuditTrail
                  approvals={rec.approvals}
                  createdAt={rec.created_at}
                />
              )}

              {/* Divider between recommendations */}
              {recommendations.length > 1 && (
                <div className="border-t border-slate-800 pt-6" />
              )}
            </div>
          ))}

          {/* Pagination for 'all' tab */}
          {activeTab === 'all' && allData && allData.pages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-4">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="btn btn-secondary disabled:opacity-50"
              >
                Previous
              </button>
              <span className="text-sm text-slate-400">
                Page {page} of {allData.pages}
              </span>
              <button
                onClick={() => setPage(Math.min(allData.pages, page + 1))}
                disabled={page === allData.pages}
                className="btn btn-secondary disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && (!recommendations || recommendations.length === 0) && (
        <div className="card">
          <div className="flex flex-col items-center justify-center py-12 text-slate-500">
            <Filter className="h-12 w-12 mb-3 opacity-50" />
            <p className="text-lg font-medium">No recommendations found</p>
            <p className="text-sm mt-1">
              {activeTab === 'pending'
                ? 'There are no pending recommendations at this time'
                : 'No recommendations match your criteria'}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
