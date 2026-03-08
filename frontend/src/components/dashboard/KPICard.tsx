import React from 'react';
import { TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface KPICardProps {
  title: string;
  value: string | number;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  threshold?: {
    value: number;
    current: number;
    label?: string;
    /** Override display (e.g. "$2.10M / $5.00M limit" for VaR) */
    display?: string;
    type: 'warning' | 'danger' | 'success';
  };
  icon?: React.ReactNode;
  glowColor?: string;
}

export function KPICard({
  title,
  value,
  trend,
  trendValue,
  threshold,
  icon,
  glowColor = 'from-primary-600',
}: KPICardProps) {
  const getTrendColor = () => {
    if (trend === 'up') return 'text-green-500';
    if (trend === 'down') return 'text-red-500';
    return 'text-slate-400';
  };

  const getThresholdColor = () => {
    if (!threshold) return 'bg-slate-700';
    if (threshold.type === 'danger') return 'bg-red-600';
    if (threshold.type === 'warning') return 'bg-amber-600';
    return 'bg-green-600';
  };

  const getThresholdProgress = () => {
    if (!threshold) return 0;
    const ratio = threshold.value !== 0 ? threshold.current / threshold.value : 0;
    return Math.min(Math.max(ratio * 100, 0), 100);
  };

  return (
    <div className="relative metric-card group overflow-hidden">
      {/* Glow effect background */}
      <div className={cn(
        "absolute inset-0 bg-gradient-to-br opacity-0 group-hover:opacity-5 transition-opacity duration-300 pointer-events-none",
        glowColor,
        "to-transparent"
      )} />

      <div className="relative z-10">
        {/* Header with icon */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <p className="text-sm font-medium text-slate-400 uppercase tracking-wide">
              {title}
            </p>
          </div>
          {icon && (
            <div className="text-slate-500 ml-3">
              {icon}
            </div>
          )}
        </div>

        {/* Main value */}
        <div className="mb-4">
          <div className="flex items-baseline gap-3">
            <span className="text-4xl font-bold text-white tracking-tight">
              {value}
            </span>
            {trend && trendValue && (
              <div className={cn("flex items-center gap-1", getTrendColor())}>
                {trend === 'up' && <TrendingUp className="h-5 w-5" />}
                {trend === 'down' && <TrendingDown className="h-5 w-5" />}
                <span className="text-sm font-semibold">{trendValue}</span>
              </div>
            )}
          </div>
        </div>

        {/* Threshold indicator */}
        {threshold && (
          <div className="mt-6 pt-4 border-t border-slate-800">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-slate-400 flex items-center gap-1">
                {threshold.type !== 'success' && (
                  <AlertTriangle className="h-3 w-3" />
                )}
                {threshold.label ?? 'Limit'}
              </span>
              <span className="text-xs font-medium text-slate-300">
                {threshold.display ??
                  `${threshold.current.toFixed(2)}% / ${threshold.value}%`}
              </span>
            </div>
            <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-500",
                  getThresholdColor()
                )}
                style={{ width: `${getThresholdProgress()}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
