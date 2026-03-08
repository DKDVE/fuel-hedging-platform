import { useState, useEffect } from 'react';
import { Clock, CheckCircle, XCircle, PauseCircle, AlertTriangle, Eye, EyeOff } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn, safeNumber } from '@/lib/utils';
import { UserRole } from '@/types/api';
import type { HedgeRecommendationResponse, RecommendationStatus } from '@/types/api';
import {
  generateExecutiveSummary,
  generateRiskNarrative,
  generateActionStatement,
  generateAgentPlainEnglish,
} from '@/lib/recommendationNarrative';
import { useAuth } from '@/contexts/AuthContext';

interface ApprovalWorkflowCardProps {
  recommendation: HedgeRecommendationResponse;
  onApprove?: (comments?: string) => void;
  onReject?: (reason: string) => void;
  onDefer?: (reason: string) => void;
  canApprove: boolean;
  isSubmitting?: boolean;
}

export function ApprovalWorkflowCard({
  recommendation,
  onApprove,
  onReject,
  onDefer,
  canApprove,
  isSubmitting = false,
}: ApprovalWorkflowCardProps) {
  const [timeRemaining, setTimeRemaining] = useState<number>(0);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [showDeferModal, setShowDeferModal] = useState(false);
  const [reason, setReason] = useState('');
  const { user } = useAuth();
  
  // Determine default view mode based on role
  const getDefaultViewMode = () => {
    if (user?.role === UserRole.CFO || user?.role === UserRole.RISK_MANAGER) {
      return 'summary';
    }
    return 'detail'; // analyst, admin default to detail
  };
  
  const [viewMode, setViewMode] = useState<'summary' | 'detail'>(getDefaultViewMode());

  // Calculate time remaining until 4-hour SLA
  useEffect(() => {
    const calculateTimeRemaining = () => {
      const createdAt = new Date(recommendation.created_at);
      const slaDeadline = new Date(createdAt.getTime() + 4 * 60 * 60 * 1000); // 4 hours
      const now = new Date();
      const remaining = Math.max(0, slaDeadline.getTime() - now.getTime());
      setTimeRemaining(remaining);
    };

    calculateTimeRemaining();
    const interval = setInterval(calculateTimeRemaining, 1000);

    return () => clearInterval(interval);
  }, [recommendation.created_at]);

  const formatTimeRemaining = (ms: number) => {
    const hours = Math.floor(ms / (1000 * 60 * 60));
    const minutes = Math.floor((ms % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((ms % (1000 * 60)) / 1000);
    return `${hours}h ${minutes}m ${seconds}s`;
  };

  const getStatusBadge = (status: RecommendationStatus) => {
    switch (status) {
      case 'PENDING':
        return <Badge variant="warning">Pending Approval</Badge>;
      case 'APPROVED':
        return <Badge variant="success">Approved</Badge>;
      case 'REJECTED':
        return <Badge variant="destructive">Rejected</Badge>;
      case 'DEFERRED':
        return <Badge variant="secondary">Deferred</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getTimeRemainingColor = () => {
    const hoursRemaining = timeRemaining / (1000 * 60 * 60);
    if (hoursRemaining < 1) return 'text-red-500';
    if (hoursRemaining < 2) return 'text-amber-500';
    return 'text-green-500';
  };

  const handleApprove = () => {
    if (onApprove) {
      onApprove();
    }
  };

  const handleReject = () => {
    if (reason.trim() && onReject) {
      onReject(reason);
      setShowRejectModal(false);
      setReason('');
    }
  };

  const handleDefer = () => {
    if (reason.trim() && onDefer) {
      onDefer(reason);
      setShowDeferModal(false);
      setReason('');
    }
  };

  const agents = (recommendation.agent_outputs ?? []) as Parameters<typeof generateRiskNarrative>[0];
  const executiveSummary = generateExecutiveSummary(recommendation);
  const riskNarrative = generateRiskNarrative(agents);
  const actionStatement = generateActionStatement(recommendation);

  return (
    <div className="card">
      {/* Header with View Toggle */}
      <div className="flex items-start justify-between mb-6">
        <div className="flex-1">
          <h3 className="text-xl font-semibold text-white mb-2">
            Hedge Recommendation #{recommendation.id?.slice(0, 8) || 'N/A'}
          </h3>
          <p className="text-sm text-slate-400">
            Generated from analytics run {recommendation.run_id?.slice(0, 8) || 'N/A'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setViewMode(viewMode === 'summary' ? 'detail' : 'summary')}
            className={cn(
              'flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
              'border border-slate-700',
              viewMode === 'summary'
                ? 'bg-blue-600 text-white'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            )}
          >
            {viewMode === 'summary' ? (
              <>
                <Eye className="h-4 w-4" />
                Executive View
              </>
            ) : (
              <>
                <EyeOff className="h-4 w-4" />
                Technical Detail
              </>
            )}
          </button>
          {getStatusBadge(recommendation.status)}
        </div>
      </div>

      {/* SLA Countdown */}
      {recommendation.status === 'PENDING' && (
        <div className="bg-slate-800/50 rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Clock className={cn('h-5 w-5', getTimeRemainingColor())} />
              <div>
                <p className="text-sm font-medium text-white">SLA Countdown</p>
                <p className="text-xs text-slate-400 mt-0.5">
                  4-hour approval window
                </p>
              </div>
            </div>
            <div className={cn('text-2xl font-bold tabular-nums', getTimeRemainingColor())}>
              {formatTimeRemaining(timeRemaining)}
            </div>
          </div>
          {timeRemaining < 60 * 60 * 1000 && (
            <div className="mt-3 flex items-center gap-2 text-xs text-red-400">
              <AlertTriangle className="h-4 w-4" />
              <span>Urgent: Less than 1 hour remaining</span>
            </div>
          )}
        </div>
      )}

      {/* SUMMARY VIEW - Plain English */}
      {viewMode === 'summary' && (
        <div className="space-y-4 mb-6">
          {executiveSummary.urgency === 'urgent' && (
            <div className="flex items-center gap-2 p-3 bg-red-950 border border-red-600 rounded-lg">
              <span className="text-red-400 text-sm font-medium animate-pulse">⚠ URGENT</span>
              <span className="text-red-300 text-sm">Immediate review required</span>
            </div>
          )}
          {/* Executive Summary */}
          <div className="bg-blue-950/20 border border-blue-800 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-blue-400 uppercase tracking-wide mb-2">
              Executive Summary
            </h4>
            <p className="text-slate-200 leading-relaxed mb-3">
              {executiveSummary.headline}
            </p>
            <p className="text-slate-300 text-sm leading-relaxed">
              {executiveSummary.context}
            </p>
            <div className="flex items-center gap-3 mt-3">
              <span className={`text-xs font-medium px-2 py-1 rounded-full ${
                executiveSummary.confidence === 'high' ? 'bg-green-900 text-green-300' :
                executiveSummary.confidence === 'moderate' ? 'bg-amber-900 text-amber-300' :
                'bg-gray-700 text-gray-400'
              }`}>
                {executiveSummary.confidence === 'high' ? '✓ High confidence' :
                 executiveSummary.confidence === 'moderate' ? '~ Moderate confidence' :
                 '? Low confidence'}
              </span>
              <span className="text-xs text-gray-500">{executiveSummary.confidenceReason}</span>
            </div>
          </div>

          {/* Risk Assessment */}
          <div className="bg-slate-800/50 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-slate-300 uppercase tracking-wide mb-2">
              Risk Assessment
            </h4>
            <p className="text-slate-400 text-sm mb-3">{riskNarrative.overallMessage}</p>
            {riskNarrative.keyRisks.length > 0 && (
              <div className="space-y-1 mb-3">
                {riskNarrative.keyRisks.map((risk, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm text-amber-300">
                    <span className="mt-0.5 shrink-0">⚠</span>
                    <span>{risk}</span>
                  </div>
                ))}
              </div>
            )}
            <div className="space-y-1">
              {riskNarrative.protections.map((p, i) => (
                <div key={i} className="flex items-start gap-2 text-sm text-green-300">
                  <span className="mt-0.5 shrink-0">✓</span>
                  <span>{p}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Action Required */}
          <div className="rounded-lg p-4 border bg-blue-950/20 border-blue-800">
            <h4 className="text-sm font-semibold text-blue-300 uppercase tracking-wide mb-2">
              Recommended Action
            </h4>
            <p className="text-white font-medium mb-1">{actionStatement.primaryAction}</p>
            <p className="text-blue-200 text-sm mb-1">{actionStatement.rationale}</p>
            <p className="text-blue-300 text-sm">{actionStatement.financialImpact}</p>
            <p className="text-blue-400 text-xs mt-2">⏱ {actionStatement.deadline}</p>
          </div>

          {/* Plain-English agent summaries */}
          {agents.length > 0 && (
            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-slate-300 uppercase tracking-wide mb-3">
                What Our Specialists Say
              </h4>
              <div className="space-y-3">
                {agents.map((agent) => {
                  const pe = generateAgentPlainEnglish(agent);
                  return (
                    <div key={agent.agent_id} className="flex items-start gap-3">
                      <span className="text-xs text-slate-500 w-48 shrink-0 pt-0.5">
                        {pe.plainLabel}:
                      </span>
                      <div className="flex-1">
                        <span className="text-sm text-slate-300">{pe.summary}</span>
                        <span className={`ml-2 text-xs font-medium ${
                          pe.verdict.startsWith('✅') ? 'text-green-400' :
                          pe.verdict.startsWith('⚠️') ? 'text-amber-400' :
                          'text-red-400'
                        }`}>
                          {pe.verdict}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Compliance Status */}
          <div className="flex items-center gap-3">
            <div className={cn(
              'flex-1 flex items-center gap-2 px-4 py-3 rounded-lg border',
              recommendation.constraints_satisfied
                ? 'bg-green-950/30 border-green-800 text-green-400'
                : 'bg-red-950/30 border-red-800 text-red-400'
            )}>
              {recommendation.constraints_satisfied ? (
                <CheckCircle className="h-5 w-5" />
              ) : (
                <XCircle className="h-5 w-5" />
              )}
              <span className="text-sm font-medium">
                {recommendation.constraints_satisfied ? 'All constraints satisfied' : 'Constraint violations detected'}
              </span>
            </div>

            <div className={cn(
              'flex-1 flex items-center gap-2 px-4 py-3 rounded-lg border',
              recommendation.ifrs9_eligible
                ? 'bg-blue-950/30 border-blue-800 text-blue-400'
                : 'bg-slate-800 border-slate-700 text-slate-400'
            )}>
              {recommendation.ifrs9_eligible ? (
                <CheckCircle className="h-5 w-5" />
              ) : (
                <XCircle className="h-5 w-5" />
              )}
              <span className="text-sm font-medium">
                {recommendation.ifrs9_eligible ? 'IFRS 9 hedge accounting eligible' : 'Not eligible for hedge accounting'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* DETAIL VIEW - Technical Metrics */}
      {viewMode === 'detail' && (
        <div className="space-y-6 mb-6">
          {/* Key Metrics with Plain-English Labels */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
                Optimal Hedge Ratio
              </p>
              <p className="text-lg font-bold text-white">
                {safeNumber(Number(recommendation.optimal_hedge_ratio) * 100, 2, 'N/A')}%
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Recommended fuel coverage percentage
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
                Expected VaR Reduction
              </p>
              <p className="text-lg font-bold text-green-500">
                {safeNumber(Number(recommendation.expected_var_reduction) * 100, 2, 'N/A')}%
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Value-at-Risk improvement
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
                Hedge Effectiveness (R²)
              </p>
              <p className="text-lg font-bold text-white">
                {safeNumber(recommendation.hedge_effectiveness_r2, 4)}
              </p>
              <p className="text-xs text-slate-500 mt-1">
                How well hedge tracks jet fuel prices
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
                Collateral Impact
              </p>
              <p className="text-lg font-bold text-amber-500">
                {safeNumber(Number(recommendation.collateral_impact) * 100, 2, 'N/A')}%
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Percentage of cash reserves required
              </p>
            </div>
          </div>

          {/* Status Indicators */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className={cn(
              'flex items-center gap-2 px-3 py-2 rounded-lg border',
              recommendation.constraints_satisfied
                ? 'bg-green-950/30 border-green-800 text-green-400'
                : 'bg-red-950/30 border-red-800 text-red-400'
            )}>
              {recommendation.constraints_satisfied ? (
                <CheckCircle className="h-4 w-4" />
              ) : (
                <XCircle className="h-4 w-4" />
              )}
              <span className="text-xs font-medium">Constraints</span>
            </div>

            <div className={cn(
              'flex items-center gap-2 px-3 py-2 rounded-lg border',
              recommendation.ifrs9_eligible
                ? 'bg-blue-950/30 border-blue-800 text-blue-400'
                : 'bg-slate-800 border-slate-700 text-slate-400'
            )}>
              {recommendation.ifrs9_eligible ? (
                <CheckCircle className="h-4 w-4" />
              ) : (
                <XCircle className="h-4 w-4" />
              )}
              <span className="text-xs font-medium">IFRS 9</span>
            </div>

            <div className={cn(
              'flex items-center gap-2 px-3 py-2 rounded-lg border',
              recommendation.action_required
                ? 'bg-amber-950/30 border-amber-800 text-amber-400'
                : 'bg-slate-800 border-slate-700 text-slate-400'
            )}>
              <AlertTriangle className="h-4 w-4" />
              <span className="text-xs font-medium">Action Required</span>
            </div>

            <div className="flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-700 bg-slate-800">
              <div className={cn(
                'h-2 w-2 rounded-full',
                recommendation.risk_level === 'LOW' && 'bg-green-500',
                recommendation.risk_level === 'MODERATE' && 'bg-amber-500',
                recommendation.risk_level === 'HIGH' && 'bg-red-500',
                recommendation.risk_level === 'CRITICAL' && 'bg-red-600 animate-pulse'
              )} />
              <span className="text-xs font-medium text-slate-300">
                {recommendation.risk_level} Risk
              </span>
            </div>
          </div>

          {/* Recommendation Text */}
          <div className="bg-slate-800/50 rounded-lg p-4">
            <p className="text-sm text-slate-300 leading-relaxed">
              {recommendation.recommendation_text}
            </p>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      {canApprove && recommendation.status === 'PENDING' && (
        <div className="flex items-center gap-3">
          <button
            onClick={handleApprove}
            disabled={isSubmitting}
            className="btn btn-success flex-1 flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <CheckCircle className="h-4 w-4" />
            {viewMode === 'summary' ? 'Approve Strategy' : 'Approve'}
          </button>
          <button
            onClick={() => setShowDeferModal(true)}
            disabled={isSubmitting}
            className="btn btn-secondary flex-1 flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <PauseCircle className="h-4 w-4" />
            {viewMode === 'summary' ? 'Request Review' : 'Defer'}
          </button>
          <button
            onClick={() => setShowRejectModal(true)}
            disabled={isSubmitting}
            className="btn btn-danger flex-1 flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <XCircle className="h-4 w-4" />
            {viewMode === 'summary' ? 'Decline Strategy' : 'Reject'}
          </button>
        </div>
      )}

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-6 max-w-md w-full mx-4">
            <h4 className="text-lg font-semibold text-white mb-4">Reject Recommendation</h4>
            <p className="text-sm text-slate-400 mb-4">
              Please provide a reason for rejecting this recommendation:
            </p>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="input min-h-[100px] mb-4"
              placeholder="Enter rejection reason..."
            />
            <div className="flex gap-3">
              <button
                onClick={handleReject}
                disabled={!reason.trim()}
                className="btn btn-danger flex-1 disabled:opacity-50"
              >
                Reject
              </button>
              <button
                onClick={() => {
                  setShowRejectModal(false);
                  setReason('');
                }}
                className="btn btn-secondary flex-1"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Defer Modal */}
      {showDeferModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-6 max-w-md w-full mx-4">
            <h4 className="text-lg font-semibold text-white mb-4">Defer Recommendation</h4>
            <p className="text-sm text-slate-400 mb-4">
              Please provide a reason for deferring this recommendation:
            </p>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="input min-h-[100px] mb-4"
              placeholder="Enter deferral reason..."
            />
            <div className="flex gap-3">
              <button
                onClick={handleDefer}
                disabled={!reason.trim()}
                className="btn btn-secondary flex-1 disabled:opacity-50"
              >
                Defer
              </button>
              <button
                onClick={() => {
                  setShowDeferModal(false);
                  setReason('');
                }}
                className="btn btn-secondary flex-1"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
