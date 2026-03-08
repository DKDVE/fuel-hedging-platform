import { CheckCircle, XCircle, TrendingUp, TrendingDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatPct, isSafe } from '@/lib/formatters';

interface HypothesisCardProps {
  id: string;
  title: string;
  description: string;
  metric: {
    label: string;
    value: number;
    threshold: number;
    thresholdLabel: string;
    unit?: string;
  };
  passed: boolean;
  lastTested: string;
  trend?: 'up' | 'down' | 'neutral';
}

export function HypothesisCard({
  id,
  title,
  description,
  metric,
  passed,
  lastTested,
  trend,
}: HypothesisCardProps) {
  const formatValue = (value: number | null | undefined) => {
    if (!isSafe(value)) return '—';
    if (metric.unit === '%') return formatPct(value, 2);
    if (metric.unit === 'ratio') return value.toFixed(4);
    return value.toFixed(2);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric' 
    });
  };

  const safeValue = isSafe(metric.value) ? metric.value : 0;
  const safeThreshold = isSafe(metric.threshold) ? metric.threshold : 0;
  const isAboveThreshold = safeValue >= safeThreshold;
  const meetsCondition = id === 'h1' || id === 'h4' ? safeValue < safeThreshold : isAboveThreshold;

  return (
    <div className={cn(
      'relative overflow-hidden rounded-xl border-2 transition-all duration-300',
      passed 
        ? 'bg-green-950/20 border-green-700 hover:border-green-600' 
        : 'bg-red-950/20 border-red-700 hover:border-red-600'
    )}>
      {/* Status Badge */}
      <div className="absolute top-4 right-4">
        {passed ? (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-green-600 text-white rounded-full text-xs font-bold">
            <CheckCircle className="h-3.5 w-3.5" />
            VALIDATED
          </div>
        ) : (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-red-600 text-white rounded-full text-xs font-bold">
            <XCircle className="h-3.5 w-3.5" />
            FAILED
          </div>
        )}
      </div>

      <div className="p-6">
        {/* Header */}
        <div className="mb-4 pr-32">
          <h3 className="text-lg font-semibold text-white mb-2">
            {title}
          </h3>
          <p className="text-sm text-slate-400 leading-relaxed">
            {description}
          </p>
        </div>

        {/* Metric Display */}
        <div className="bg-slate-900/50 rounded-lg p-4 mb-4">
          <div className="flex items-end justify-between mb-2">
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
                {metric.label}
              </p>
              <div className="flex items-baseline gap-3">
                <span className={cn(
                  'text-3xl font-bold',
                  passed ? 'text-green-400' : 'text-red-400'
                )}>
                  {formatValue(metric.value)}
                </span>
                {trend && (
                  <div className={cn(
                    'flex items-center gap-1 text-sm font-semibold',
                    trend === 'up' ? 'text-green-500' : trend === 'down' ? 'text-red-500' : 'text-slate-400'
                  )}>
                    {trend === 'up' && <TrendingUp className="h-4 w-4" />}
                    {trend === 'down' && <TrendingDown className="h-4 w-4" />}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Threshold Indicator */}
          <div className="mt-3 pt-3 border-t border-slate-800">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">{metric.thresholdLabel}</span>
              <span className={cn(
                'font-semibold',
                meetsCondition ? 'text-green-400' : 'text-red-400'
              )}>
                {formatValue(metric.threshold)}
              </span>
            </div>
            <div className="mt-2 h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className={cn(
                  'h-full transition-all duration-500',
                  passed ? 'bg-green-600' : 'bg-red-600'
                )}
                style={{ 
                  width: `${safeThreshold !== 0 ? Math.min((safeValue / safeThreshold) * 100, 100) : 0}%` 
                }}
              />
            </div>
          </div>
        </div>

        {/* Last Tested */}
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>Last Tested</span>
          <span className="font-medium text-slate-400">{formatDate(lastTested)}</span>
        </div>
      </div>

      {/* Glow Effect */}
      <div className={cn(
        'absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity pointer-events-none',
        passed ? 'bg-gradient-to-br from-green-600' : 'bg-gradient-to-br from-red-600'
      )} />
    </div>
  );
}
