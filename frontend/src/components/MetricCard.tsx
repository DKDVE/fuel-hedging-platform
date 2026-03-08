import React from 'react';
import { TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  icon?: React.ReactNode;
  colorClass?: string;
}

export function MetricCard({
  title,
  value,
  subtitle,
  trend,
  trendValue,
  icon,
  colorClass = 'text-primary-600',
}: MetricCardProps) {
  const getTrendIcon = () => {
    if (trend === 'up') return <TrendingUp className="h-4 w-4" />;
    if (trend === 'down') return <TrendingDown className="h-4 w-4" />;
    return <Activity className="h-4 w-4" />;
  };

  const getTrendColor = () => {
    if (trend === 'up') return 'text-success-600';
    if (trend === 'down') return 'text-danger-600';
    return 'text-gray-500';
  };

  return (
    <div className="card">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className={cn('text-3xl font-bold mt-2', colorClass)}>{value}</p>
          {subtitle && (
            <p className="text-sm text-gray-500 mt-1">{subtitle}</p>
          )}
        </div>
        {icon && (
          <div className={cn('p-3 rounded-lg bg-opacity-10', colorClass)}>
            {icon}
          </div>
        )}
      </div>
      {trend && trendValue && (
        <div className={cn('flex items-center mt-4 text-sm', getTrendColor())}>
          {getTrendIcon()}
          <span className="ml-1">{trendValue}</span>
        </div>
      )}
    </div>
  );
}
