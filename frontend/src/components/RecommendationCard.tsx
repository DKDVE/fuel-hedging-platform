import { cn, getRiskLevelColor, formatPercentage } from '@/lib/utils';
import type { HedgeRecommendationResponse } from '@/types/api';

interface RecommendationCardProps {
  recommendation: HedgeRecommendationResponse;
  onApprove?: () => void;
  onReject?: () => void;
  onDefer?: () => void;
  showActions?: boolean;
}

export function RecommendationCard({
  recommendation,
  onApprove,
  onReject,
  onDefer,
  showActions = false,
}: RecommendationCardProps) {
  const riskColorClass = getRiskLevelColor(recommendation.risk_level);

  return (
    <div className="card">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold">
            Hedge Recommendation #{recommendation.id.slice(0, 8)}
          </h3>
          <p className="text-sm text-gray-500">
            Created: {new Date(recommendation.created_at).toLocaleString()}
          </p>
        </div>
        <span className={cn('badge', riskColorClass)}>
          {recommendation.risk_level}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-sm text-gray-600">Optimal Hedge Ratio</p>
          <p className="text-xl font-bold">
            {formatPercentage(recommendation.optimal_hedge_ratio)}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-600">Expected VaR Reduction</p>
          <p className="text-xl font-bold">
            {formatPercentage(recommendation.expected_var_reduction)}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-600">Hedge Effectiveness (R²)</p>
          <p className="text-xl font-bold">
            {formatPercentage(recommendation.hedge_effectiveness_r2)}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-600">Collateral Impact</p>
          <p className="text-xl font-bold">
            {formatPercentage(recommendation.collateral_impact)}
          </p>
        </div>
      </div>

      <div className="mb-4">
        <p className="text-sm text-gray-600 mb-2">Instrument Mix</p>
        <div className="flex flex-wrap gap-2">
          {Object.entries(recommendation.instrument_mix).map(
            ([instrument, weight]) => (
              <span
                key={instrument}
                className="badge badge-info"
              >
                {instrument}: {formatPercentage(weight as number)}
              </span>
            )
          )}
        </div>
      </div>

      <div className="mb-4">
        <p className="text-sm text-gray-600 mb-2">Recommendation</p>
        <p className="text-sm">{recommendation.recommendation_text}</p>
      </div>

      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-4">
          <span
            className={cn(
              'badge',
              recommendation.ifrs9_eligible ? 'badge-success' : 'badge-danger'
            )}
          >
            {recommendation.ifrs9_eligible
              ? 'IFRS 9 Eligible'
              : 'Not IFRS 9 Eligible'}
          </span>
          <span
            className={cn(
              'badge',
              recommendation.constraints_satisfied
                ? 'badge-success'
                : 'badge-warning'
            )}
          >
            {recommendation.constraints_satisfied
              ? 'Constraints Satisfied'
              : 'Constraints Violated'}
          </span>
        </div>
        {recommendation.action_required && (
          <span className="badge badge-warning">Action Required</span>
        )}
      </div>

      {showActions && recommendation.status === 'PENDING' && (
        <div className="flex space-x-2 mt-4">
          <button onClick={onApprove} className="btn btn-success flex-1">
            Approve
          </button>
          <button onClick={onDefer} className="btn btn-secondary flex-1">
            Defer
          </button>
          <button onClick={onReject} className="btn btn-danger flex-1">
            Reject
          </button>
        </div>
      )}
    </div>
  );
}
