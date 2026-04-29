import { useState, useEffect } from 'react';
import { Clock, CheckCircle, XCircle, PauseCircle, AlertTriangle, Eye, EyeOff } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn, safeNumber } from '@/lib/utils';
import { UserRole } from '@/types/api';
import type { HedgeRecommendationResponse, RecommendationStatus } from '@/types/api';
import { apiClient } from '@/lib/api';
import { formatMillions } from '@/lib/formatters';
import {
  generateExecutiveSummary,
  generateRiskNarrative,
  generateActionStatement,
  generateAgentPlainEnglish,
} from '@/lib/recommendationNarrative';
import { useAuth } from '@/contexts/AuthContext';

interface ApprovalWorkflowCardProps {
  recommendation: HedgeRecommendationResponse;
  onApprove?: (comments?: string, customHR?: number, customMix?: Record<string, number>) => void;
  onReject?: (reason: string) => void;
  onDefer?: (reason: string, deferUntil?: string) => void;
  canApprove: boolean;
  isSubmitting?: boolean;
}

type InstrumentKey = 'futures' | 'options' | 'collars' | 'swaps';

type InstrumentMix = Record<InstrumentKey, number>;

interface StrategyMetrics {
  var_hedged?: number | string | null;
  var_hedged_usd?: number | string | null;
  collateral_pct?: number | string | null;
}

interface WhatIfApiResponse {
  your_strategy?: StrategyMetrics;
  custom_strategy?: StrategyMetrics;
  system_recommendation?: StrategyMetrics;
  recommended_strategy?: StrategyMetrics;
  your_var_hedged?: number | string | null;
  system_var_hedged?: number | string | null;
  your_collateral_pct?: number | string | null;
  system_collateral_pct?: number | string | null;
  var_difference?: number | string | null;
  var_difference_usd?: number | string | null;
  verdict?: string | null;
  message?: string | null;
}

const DEFAULT_MIX: InstrumentMix = {
  futures: 70,
  options: 20,
  collars: 10,
  swaps: 0,
};

const MIX_LABELS: Record<InstrumentKey, string> = {
  futures: 'Futures',
  options: 'Options',
  collars: 'Collars',
  swaps: 'Swaps',
};

const clamp = (value: number, min: number, max: number): number => Math.min(max, Math.max(min, value));
const roundToStep = (value: number, step: number): number => Math.round(value / step) * step;

const parseNumber = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
};

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
  const [showInstrumentOverride, setShowInstrumentOverride] = useState(false);
  const [instrumentOverride, setInstrumentOverride] = useState<string | null>(null);
  const [reason, setReason] = useState('');
  const [whatIfHR, setWhatIfHR] = useState<number>(70);
  const [whatIfMix, setWhatIfMix] = useState<InstrumentMix>(DEFAULT_MIX);
  const [whatIfLoading, setWhatIfLoading] = useState(false);
  const [whatIfResult, setWhatIfResult] = useState<WhatIfApiResponse | null>(null);
  const [whatIfError, setWhatIfError] = useState<string | null>(null);
  const { user } = useAuth();

  const canCustomise = (
    user?.role === UserRole.CFO ||
    user?.role === UserRole.RISK_MANAGER
  ) && recommendation.status === 'PENDING' && canApprove;

  const getRecommendationMix = (): InstrumentMix => {
    const source = recommendation.instrument_mix ?? {};
    return {
      futures: clamp(roundToStep(((parseNumber(source.futures) ?? DEFAULT_MIX.futures) <= 1
        ? (parseNumber(source.futures) ?? DEFAULT_MIX.futures) * 100
        : (parseNumber(source.futures) ?? DEFAULT_MIX.futures)), 5), 0, 100),
      options: clamp(roundToStep(((parseNumber(source.options) ?? DEFAULT_MIX.options) <= 1
        ? (parseNumber(source.options) ?? DEFAULT_MIX.options) * 100
        : (parseNumber(source.options) ?? DEFAULT_MIX.options)), 5), 0, 100),
      collars: clamp(roundToStep(((parseNumber(source.collars) ?? DEFAULT_MIX.collars) <= 1
        ? (parseNumber(source.collars) ?? DEFAULT_MIX.collars) * 100
        : (parseNumber(source.collars) ?? DEFAULT_MIX.collars)), 5), 0, 100),
      swaps: clamp(roundToStep(((parseNumber(source.swaps) ?? DEFAULT_MIX.swaps) <= 1
        ? (parseNumber(source.swaps) ?? DEFAULT_MIX.swaps) * 100
        : (parseNumber(source.swaps) ?? DEFAULT_MIX.swaps)), 5), 0, 100),
    };
  };

  const getRecommendationHR = (): number => {
    const ratio = parseNumber(recommendation.optimal_hedge_ratio) ?? 0.7;
    return clamp(Math.round(ratio * 100), 30, 80);
  };

  useEffect(() => {
    setWhatIfHR(getRecommendationHR());
    setWhatIfMix(getRecommendationMix());
    setWhatIfResult(null);
    setWhatIfError(null);
  }, [recommendation.id]);
  
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
      const overrideComment = instrumentOverride
        ? ` [Instrument override: ${instrumentOverride}]`
        : '';
      onApprove(overrideComment.trim() || undefined);
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

  const handleMixChange = (key: InstrumentKey, rawValue: number) => {
    setWhatIfMix((prev) => ({
      ...prev,
      [key]: clamp(roundToStep(rawValue, 5), 0, 100),
    }));
    setWhatIfResult(null);
    setWhatIfError(null);
  };

  const totalMix = whatIfMix.futures + whatIfMix.options + whatIfMix.collars + whatIfMix.swaps;
  const isMixValid = totalMix === 100;

  const getFirstNumber = (...values: Array<number | string | null | undefined>): number | null => {
    for (const candidate of values) {
      const parsed = parseNumber(candidate);
      if (parsed !== null) return parsed;
    }
    return null;
  };

  const normalisePct = (value: number | null): number | null => {
    if (value === null) return null;
    return value <= 1 ? value * 100 : value;
  };

  const runWhatIfAnalysis = async () => {
    setWhatIfLoading(true);
    setWhatIfError(null);

    try {
      const optimizationResult = (
        recommendation as HedgeRecommendationResponse & {
          optimization_result?: { collateral_required_usd?: number | string | null };
        }
      ).optimization_result;
      const collateralBaseRaw = Number(optimizationResult?.collateral_required_usd ?? 0);
      const collateralBase = Number.isFinite(collateralBaseRaw) ? collateralBaseRaw : 0;

      const response = await apiClient.post<WhatIfApiResponse>('/analytics/what-if', {
        hedge_ratio: whatIfHR / 100,
        instrument_mix: {
          futures: whatIfMix.futures / 100,
          options: whatIfMix.options / 100,
          collars: whatIfMix.collars / 100,
          swaps: whatIfMix.swaps / 100,
        },
        original_var_hedged: collateralBase * 10,
        original_var_unhedged: collateralBase * 17,
      });

      setWhatIfResult(response.data);
    } catch {
      setWhatIfError('Could not run what-if analysis. Please try again.');
      setWhatIfResult(null);
    } finally {
      setWhatIfLoading(false);
    }
  };

  const yourStrategy = whatIfResult?.your_strategy ?? whatIfResult?.custom_strategy;
  const systemStrategy = whatIfResult?.system_recommendation ?? whatIfResult?.recommended_strategy;

  const yourVar = getFirstNumber(
    yourStrategy?.var_hedged,
    yourStrategy?.var_hedged_usd,
    whatIfResult?.your_var_hedged
  );
  const systemVar = getFirstNumber(
    systemStrategy?.var_hedged,
    systemStrategy?.var_hedged_usd,
    whatIfResult?.system_var_hedged
  );
  const yourCollateral = normalisePct(
    getFirstNumber(yourStrategy?.collateral_pct, whatIfResult?.your_collateral_pct)
  );
  const systemCollateral = normalisePct(
    getFirstNumber(systemStrategy?.collateral_pct, whatIfResult?.system_collateral_pct)
  );
  const varDifference = getFirstNumber(
    whatIfResult?.var_difference,
    whatIfResult?.var_difference_usd,
    yourVar !== null && systemVar !== null ? systemVar - yourVar : null
  );
  const verdictText =
    (typeof whatIfResult?.verdict === 'string' && whatIfResult.verdict) ||
    (typeof whatIfResult?.message === 'string' && whatIfResult.message) ||
    'Custom strategy comparison completed.';

  const agents = (recommendation.agent_outputs ?? []) as Parameters<typeof generateRiskNarrative>[0];
  const executiveSummary = generateExecutiveSummary(recommendation);
  const riskNarrative = generateRiskNarrative(agents);
  const actionStatement = generateActionStatement(recommendation);
  const nearTermHR = recommendation.optimal_hedge_ratio;
  const midTermHR = nearTermHR * 0.75;
  const longTermHR = nearTermHR * 0.50;

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

          <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
            <p className="text-xs text-slate-400 uppercase tracking-wide mb-3">
              Recommended Hedge Horizon
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-slate-400 border-b border-slate-700">
                    <th className="pb-2 font-medium">Horizon</th>
                    <th className="pb-2 font-medium">Coverage</th>
                    <th className="pb-2 font-medium">Rationale</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-slate-800">
                    <td className="py-2 text-white">0-3 months</td>
                    <td className="py-2 text-white font-medium">
                      {safeNumber(nearTermHR * 100, 0, 'N/A')}%
                    </td>
                    <td className="py-2 text-slate-400">
                      Near-term: full recommended HR
                    </td>
                  </tr>
                  <tr className="border-b border-slate-800">
                    <td className="py-2 text-white">4-6 months</td>
                    <td className="py-2 text-white font-medium">
                      {safeNumber(midTermHR * 100, 0, 'N/A')}%
                    </td>
                    <td className="py-2 text-slate-400">
                      Mid-term: 75% of near-term (demand less certain)
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 text-white">7-12 months</td>
                    <td className="py-2 text-white font-medium">
                      {safeNumber(longTermHR * 100, 0, 'N/A')}%
                    </td>
                    <td className="py-2 text-slate-400">
                      Long-term: 50% of near-term (max forward visibility)
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="text-xs text-slate-500 mt-3">
              Layered coverage aligns with industry practice (IAG, Lufthansa, easyJet).
              Near-term is highest certainty; coverage tapers as demand forecast
              confidence decreases.
            </p>
          </div>
        </div>
      )}

      {canApprove && viewMode === 'detail' && recommendation.status === 'PENDING' && (
        <div className="mt-4 p-4 bg-slate-800 rounded-lg border border-slate-700">
          <button
            onClick={() => setShowInstrumentOverride((prev) => !prev)}
            className="w-full flex items-center justify-between text-left"
          >
            <p className="text-xs text-slate-400 uppercase tracking-wide">
              Override Instrument Preference (optional)
            </p>
            <span className="text-xs text-slate-400">
              {showInstrumentOverride ? 'Hide' : 'Show'}
            </span>
          </button>
          {showInstrumentOverride && (
            <>
              <div className="grid grid-cols-2 gap-2 mt-3 mb-3">
                {['Optimiser Default', 'Futures', 'Options', 'Collars', 'Swaps'].map((pref) => (
                  <button
                    key={pref}
                    onClick={() => setInstrumentOverride(pref === instrumentOverride ? null : pref)}
                    className={`px-3 py-2 rounded text-sm font-medium transition-all border ${
                      instrumentOverride === pref
                        ? 'border-blue-500 bg-blue-950 text-blue-300'
                        : 'border-slate-600 bg-slate-900 text-slate-400 hover:border-slate-400'
                    }`}
                  >
                    {pref}
                  </button>
                ))}
              </div>
              {instrumentOverride && instrumentOverride !== 'Optimiser Default' && (
                <p className="text-xs text-amber-400">
                  Override recorded in approval notes. Analytics team will adjust
                  instrument mix before position execution.
                </p>
              )}
            </>
          )}
        </div>
      )}

      {canCustomise && (
        <div className="mt-6 rounded-lg border border-slate-700 bg-slate-900/80 p-4">
          <div className="flex items-center justify-between gap-2">
            <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-200">
              Custom What-If Strategy
            </h4>
            <span className={cn(
              'text-xs font-medium',
              isMixValid ? 'text-emerald-400' : 'text-red-400'
            )}>
              Mix Total: {totalMix}%
            </span>
          </div>

          <div className="mt-4">
            <div className="mb-2 flex items-center justify-between">
              <label htmlFor="what-if-hr" className="text-sm text-slate-300">
                Hedge Ratio
              </label>
              <span className="text-sm font-semibold text-white">{whatIfHR}%</span>
            </div>
            <input
              id="what-if-hr"
              type="range"
              min={30}
              max={80}
              step={1}
              value={whatIfHR}
              onChange={(e) => {
                setWhatIfHR(Number(e.target.value));
                setWhatIfResult(null);
                setWhatIfError(null);
              }}
              className="w-full h-2 rounded-lg appearance-none cursor-pointer bg-slate-700 accent-blue-500"
            />
          </div>

          <div className="mt-4 space-y-4">
            {(Object.keys(whatIfMix) as InstrumentKey[]).map((key) => (
              <div key={key}>
                <div className="mb-2 flex items-center justify-between">
                  <label htmlFor={`what-if-${key}`} className="text-sm text-slate-300">
                    {MIX_LABELS[key]}
                  </label>
                  <span className="text-sm font-semibold text-white">{whatIfMix[key]}%</span>
                </div>
                <input
                  id={`what-if-${key}`}
                  type="range"
                  min={0}
                  max={100}
                  step={5}
                  value={whatIfMix[key]}
                  onChange={(e) => handleMixChange(key, Number(e.target.value))}
                  className="w-full h-2 rounded-lg appearance-none cursor-pointer bg-slate-700 accent-blue-500"
                />
              </div>
            ))}
          </div>

          {!isMixValid && (
            <p className="mt-3 text-xs text-red-400">
              Instrument mix must total exactly 100% before running analysis.
            </p>
          )}

          {whatIfError && (
            <p className="mt-3 text-xs text-red-400">{whatIfError}</p>
          )}

          <button
            type="button"
            onClick={runWhatIfAnalysis}
            disabled={!isMixValid || whatIfLoading}
            className="mt-4 w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
          >
            {whatIfLoading ? 'Running What-If...' : 'Run What-If Analysis'}
          </button>

          {whatIfResult !== null && (
            <div className="mt-4 rounded-lg border border-slate-700 bg-slate-800/70 p-4">
              <p className="mb-3 text-xs uppercase tracking-wide text-slate-400">
                Strategy Comparison
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-700 text-left text-slate-400">
                      <th className="pb-2 font-medium">Metric</th>
                      <th className="pb-2 font-medium">Your Strategy</th>
                      <th className="pb-2 font-medium">System Recommendation</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b border-slate-800">
                      <td className="py-2 text-slate-300">VaR</td>
                      <td className={cn(
                        'py-2 font-medium',
                        yourVar !== null && systemVar !== null && yourVar <= systemVar ? 'text-emerald-400' : 'text-red-400'
                      )}>
                        {formatMillions(yourVar)}
                      </td>
                      <td className="py-2 text-slate-200">{formatMillions(systemVar)}</td>
                    </tr>
                    <tr className="border-b border-slate-800">
                      <td className="py-2 text-slate-300">Collateral %</td>
                      <td className={cn(
                        'py-2 font-medium',
                        yourCollateral !== null && systemCollateral !== null && yourCollateral <= systemCollateral
                          ? 'text-emerald-400'
                          : 'text-red-400'
                      )}>
                        {yourCollateral === null ? '—' : `${yourCollateral.toFixed(2)}%`}
                      </td>
                      <td className="py-2 text-slate-200">
                        {systemCollateral === null ? '—' : `${systemCollateral.toFixed(2)}%`}
                      </td>
                    </tr>
                    <tr>
                      <td className="py-2 text-slate-300">var_difference</td>
                      <td className={cn(
                        'py-2 font-medium',
                        varDifference !== null && varDifference >= 0 ? 'text-emerald-400' : 'text-red-400'
                      )}>
                        {formatMillions(varDifference)}
                      </td>
                      <td className="py-2 text-slate-500">—</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p className="mt-3 text-sm text-slate-300">{verdictText}</p>

              <button
                type="button"
                onClick={() => {
                  const mix = {
                    futures: whatIfMix.futures / 100,
                    options: whatIfMix.options / 100,
                    collars: whatIfMix.collars / 100,
                    swaps: whatIfMix.swaps / 100,
                  };
                  const comment = `Custom strategy approved: HR=${whatIfHR}%, ` +
                    `Futures=${whatIfMix.futures}%, Options=${whatIfMix.options}%, ` +
                    `Collars=${whatIfMix.collars}%, Swaps=${whatIfMix.swaps}%`;
                  onApprove?.(comment, whatIfHR / 100, mix);
                }}
                disabled={isSubmitting}
                className="mt-4 w-full rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
              >
                Approve with my strategy
              </button>
            </div>
          )}
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
