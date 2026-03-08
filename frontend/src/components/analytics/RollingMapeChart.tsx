import { useState, useMemo } from 'react';
import {
  Area,
  LineChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
  ComposedChart,
  Line,
  Brush,
} from 'recharts';
import { TrendingDown, AlertTriangle, Download, ZoomIn, Activity, BarChart3 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatPct } from '@/lib/formatters';

interface MapeDataPoint {
  date: string;
  mape: number;
}

interface RollingMapeChartProps {
  data: MapeDataPoint[];
  targetThreshold?: number;
  alertThreshold?: number;
  isLoading?: boolean;
}

export function RollingMapeChart({
  data,
  targetThreshold = 8.0,
  alertThreshold = 10.0,
  isLoading = false,
}: RollingMapeChartProps) {
  const [timeRange, setTimeRange] = useState<'30d' | '90d' | '180d'>('90d');
  const [showThresholds, setShowThresholds] = useState(true);
  const [showTrendLine, setShowTrendLine] = useState(true);
  const [enableZoom, setEnableZoom] = useState(false);
  const [highlightViolations, setHighlightViolations] = useState(true);

  // Filter data based on time range
  const filteredData = useMemo(() => {
    const daysToShow = timeRange === '30d' ? 30 : timeRange === '90d' ? 90 : 180;
    return data.slice(0, daysToShow);
  }, [data, timeRange]);

  // Calculate trend line using linear regression
  const trendData = useMemo(() => {
    if (!showTrendLine || filteredData.length < 2) return [];
    
    const n = filteredData.length;
    const sumX = filteredData.reduce((sum, _, i) => sum + i, 0);
    const sumY = filteredData.reduce((sum, d) => sum + d.mape, 0);
    const sumXY = filteredData.reduce((sum, d, i) => sum + i * d.mape, 0);
    const sumX2 = filteredData.reduce((sum, _, i) => sum + i * i, 0);
    
    const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
    const intercept = (sumY - slope * sumX) / n;
    
    return filteredData.map((d, i) => ({
      ...d,
      trend: slope * i + intercept
    }));
  }, [filteredData, showTrendLine]);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const formatMape = (value: number | null | undefined) => formatPct(value, 2);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const mape = payload[0].value;
      const trend = payload.find((p: any) => p.dataKey === 'trend')?.value;
      const status =
        mape < targetThreshold
          ? 'Excellent'
          : mape < alertThreshold
          ? 'Acceptable'
          : 'Alert';
      const statusColor =
        mape < targetThreshold
          ? 'text-green-400'
          : mape < alertThreshold
          ? 'text-amber-400'
          : 'text-red-400';

      const trendDirection = trend ? (
        mape > trend ? 'above' : 'below'
      ) : null;

      return (
        <div className="bg-slate-900 border border-slate-700 rounded-lg p-4 shadow-xl min-w-[200px]">
          <p className="text-xs text-slate-400 mb-3 font-semibold">{formatDate(label)}</p>
          <div className="flex items-center justify-between gap-4 mb-2">
            <span className="text-xs text-slate-300">MAPE:</span>
            <span className="text-lg font-bold text-white">
              {formatMape(mape)}
            </span>
          </div>
          {trend && (
            <div className="flex items-center justify-between gap-4 mb-2">
              <span className="text-xs text-slate-300">Trend:</span>
              <span className="text-sm font-semibold text-primary-400">
                {formatMape(trend)}
              </span>
            </div>
          )}
          <div className="mt-3 pt-3 border-t border-slate-700 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400">Status:</span>
              <span className={cn('text-xs font-semibold', statusColor)}>
                {status}
              </span>
            </div>
            {trend && trendDirection && (
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">vs Trend:</span>
                <span className={cn(
                  'text-xs font-semibold flex items-center gap-1',
                  mape > trend ? 'text-red-400' : 'text-green-400'
                )}>
                  {mape > trend ? (
                    <>
                      <Activity className="h-3 w-3" />
                      Above
                    </>
                  ) : (
                    <>
                      <TrendingDown className="h-3 w-3" />
                      Below
                    </>
                  )}
                </span>
              </div>
            )}
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400">vs Target:</span>
              <span className={cn(
                'text-xs font-semibold',
                mape < targetThreshold ? 'text-green-400' : 'text-red-400'
              )}>
                {mape < targetThreshold ? '✓ Met' : '✗ Missed'}
              </span>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  // Calculate statistics (guard against empty data)
  const hasData = filteredData.length > 0;
  const avgMape = hasData ? filteredData.reduce((sum, d) => sum + d.mape, 0) / filteredData.length : 0;
  const minMape = hasData ? Math.min(...filteredData.map(d => d.mape)) : 0;
  const maxMape = hasData ? Math.max(...filteredData.map(d => d.mape)) : 10;
  const withinTarget = filteredData.filter(d => d.mape < targetThreshold).length;
  const targetPercentage = hasData ? (withinTarget / filteredData.length) * 100 : 0;
  const violations = filteredData.filter(d => d.mape > alertThreshold);
  
  // Calculate trend direction
  const trendSlope = trendData.length > 1 
    ? ((trendData[trendData.length - 1]?.trend || 0) - (trendData[0]?.trend || 0))
    : 0;
  const isImproving = trendSlope < 0;

  const downloadData = () => {
    const csv = [
      ['Date', 'MAPE (%)', 'Status', 'Within Target'],
      ...filteredData.map(d => [
        d.date,
        d.mape.toFixed(2),
        d.mape < targetThreshold ? 'Excellent' : d.mape < alertThreshold ? 'Acceptable' : 'Alert',
        d.mape < targetThreshold ? 'Yes' : 'No'
      ])
    ].map(row => row.join(',')).join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mape_history_${new Date().toISOString()}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div className="card">
        <div className="animate-pulse">
          <div className="h-6 bg-slate-800 rounded w-1/3 mb-4" />
          <div className="h-[350px] bg-slate-800 rounded" />
        </div>
      </div>
    );
  }

  if (!hasData) {
    return (
      <div className="card">
        <h3 className="text-lg font-semibold text-white mb-2 flex items-center gap-2">
          Rolling MAPE History
            <Activity className="h-5 w-5 text-slate-500" />
        </h3>
        <p className="text-sm text-slate-400 mb-4">
          30-day forecast accuracy over time (lower is better)
        </p>
        <div className="relative">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={[]}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis
                dataKey="date"
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                label={{ value: 'Date', position: 'insideBottom', offset: -5 }}
              />
              <YAxis
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                label={{
                  value: 'MAPE (%)',
                  angle: -90,
                  position: 'insideLeft',
                }}
              />
            </LineChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="text-center text-gray-500">
              <BarChart3 className="w-8 h-8 mx-auto mb-2 opacity-30" />
              <p className="text-sm">Run the analytics pipeline to generate data</p>
              <p className="text-xs mt-1 opacity-60">Analytics → Run Pipeline</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-white mb-2 flex items-center gap-2">
            Rolling MAPE History
            {isImproving ? (
              <TrendingDown className="h-5 w-5 text-green-500" />
            ) : (
              <Activity className="h-5 w-5 text-amber-500" />
            )}
          </h3>
          <p className="text-sm text-slate-400">
            30-day forecast accuracy over time (lower is better)
          </p>
        </div>
        <div className="flex items-center gap-2 bg-slate-800 rounded-lg p-1">
          <button
            onClick={() => setTimeRange('30d')}
            className={cn(
              'px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
              timeRange === '30d'
                ? 'bg-primary-600 text-white'
                : 'text-slate-400 hover:text-white'
            )}
          >
            30D
          </button>
          <button
            onClick={() => setTimeRange('90d')}
            className={cn(
              'px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
              timeRange === '90d'
                ? 'bg-primary-600 text-white'
                : 'text-slate-400 hover:text-white'
            )}
          >
            90D
          </button>
          <button
            onClick={() => setTimeRange('180d')}
            className={cn(
              'px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
              timeRange === '180d'
                ? 'bg-primary-600 text-white'
                : 'text-slate-400 hover:text-white'
            )}
          >
            180D
          </button>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowThresholds(!showThresholds)}
            className={cn(
              'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
              showThresholds
                ? 'bg-green-600/20 text-green-400 border border-green-600/30'
                : 'text-slate-400 hover:text-white border border-slate-700'
            )}
          >
            Thresholds
          </button>
          <button
            onClick={() => setShowTrendLine(!showTrendLine)}
            className={cn(
              'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
              showTrendLine
                ? 'bg-primary-600/20 text-primary-400 border border-primary-600/30'
                : 'text-slate-400 hover:text-white border border-slate-700'
            )}
          >
            Trend Line
          </button>
          <button
            onClick={() => setHighlightViolations(!highlightViolations)}
            className={cn(
              'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
              highlightViolations
                ? 'bg-red-600/20 text-red-400 border border-red-600/30'
                : 'text-slate-400 hover:text-white border border-slate-700'
            )}
          >
            Alert Zones
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setEnableZoom(!enableZoom)}
            className={cn(
              'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5',
              enableZoom
                ? 'bg-primary-600/20 text-primary-400 border border-primary-600/30'
                : 'text-slate-400 hover:text-white border border-slate-700'
            )}
          >
            <ZoomIn className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={downloadData}
            className="px-3 py-1.5 text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5 text-slate-400 hover:text-white border border-slate-700"
            title="Download CSV"
          >
            <Download className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart 
          data={showTrendLine ? trendData : filteredData} 
          margin={{ top: 5, right: 5, left: 5, bottom: enableZoom ? 35 : 5 }}
        >
          <defs>
            <linearGradient id="mapeGradient" x1="0" y1="0" x2="0" y2="1">
              <stop
                offset="5%"
                stopColor={avgMape < targetThreshold ? '#22c55e' : '#f59e0b'}
                stopOpacity={0.4}
              />
              <stop
                offset="95%"
                stopColor={avgMape < targetThreshold ? '#22c55e' : '#f59e0b'}
                stopOpacity={0.05}
              />
            </linearGradient>
            <linearGradient id="alertGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
            stroke="#64748b"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            tickLine={{ stroke: '#475569' }}
          />
          <YAxis
            tickFormatter={formatMape}
            stroke="#64748b"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            tickLine={{ stroke: '#475569' }}
            domain={[0, 'auto']}
            width={60}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#475569', strokeWidth: 1 }} />

          {/* Highlight alert zone above threshold */}
          {showThresholds && highlightViolations && (
            <ReferenceArea
              y1={alertThreshold}
              y2={maxMape * 1.1}
              fill="url(#alertGradient)"
              fillOpacity={0.3}
            />
          )}

          {/* Target threshold line (green) */}
          {showThresholds && (
            <ReferenceLine
              y={targetThreshold}
              stroke="#22c55e"
              strokeWidth={2}
              strokeDasharray="5 5"
              label={{
                value: `Target: ${targetThreshold}%`,
                position: 'insideTopRight',
                fill: '#22c55e',
                fontSize: 11,
                fontWeight: 'bold'
              }}
            />
          )}

          {/* Alert threshold line (amber) */}
          {showThresholds && (
            <ReferenceLine
              y={alertThreshold}
              stroke="#f59e0b"
              strokeWidth={2}
              strokeDasharray="5 5"
              label={{
                value: `Alert: ${alertThreshold}%`,
                position: 'insideTopRight',
                fill: '#f59e0b',
                fontSize: 11,
                fontWeight: 'bold'
              }}
            />
          )}

          {/* Average line */}
          <ReferenceLine
            y={avgMape}
            stroke={avgMape < targetThreshold ? '#22c55e' : '#f59e0b'}
            strokeDasharray="3 3"
            strokeOpacity={0.5}
            label={{
              value: `Avg: ${formatMape(avgMape)}`,
              position: 'insideBottomRight',
              fill: avgMape < targetThreshold ? '#22c55e' : '#f59e0b',
              fontSize: 10
            }}
          />

          <Area
            type="monotone"
            dataKey="mape"
            stroke={avgMape < targetThreshold ? '#22c55e' : '#f59e0b'}
            strokeWidth={2.5}
            fill="url(#mapeGradient)"
            dot={{ 
              fill: avgMape < targetThreshold ? '#22c55e' : '#f59e0b', 
              r: 3,
              strokeWidth: 2,
              stroke: '#0f172a'
            }}
            activeDot={{ r: 5, strokeWidth: 2 }}
            animationDuration={800}
          />

          {/* Trend line */}
          {showTrendLine && (
            <Line
              type="monotone"
              dataKey="trend"
              stroke="#3b82f6"
              strokeWidth={2}
              strokeDasharray="8 4"
              dot={false}
              name="Trend"
              animationDuration={800}
            />
          )}

          {/* Zoom brush */}
          {enableZoom && (
            <Brush
              dataKey="date"
              height={30}
              stroke="#3b82f6"
              fill="#1e293b"
              tickFormatter={formatDate}
              travellerWidth={10}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>

      {/* Summary Stats */}
      <div className="mt-6 grid grid-cols-5 gap-4 pt-4 border-t border-slate-800">
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
            Average MAPE
          </p>
          <p className={cn(
            'text-sm font-semibold',
            avgMape < targetThreshold ? 'text-green-400' : 'text-amber-400'
          )}>
            {formatMape(avgMape)}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
            Best MAPE
          </p>
          <div className="flex items-center gap-1">
            <TrendingDown className="h-3.5 w-3.5 text-green-500" />
            <p className="text-sm font-semibold text-green-400">
              {formatMape(minMape)}
            </p>
          </div>
        </div>
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
            Worst MAPE
          </p>
          <div className="flex items-center gap-1">
            <AlertTriangle className="h-3.5 w-3.5 text-red-500" />
            <p className="text-sm font-semibold text-red-400">
              {formatMape(maxMape)}
            </p>
          </div>
        </div>
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-1 flex items-center gap-1">
            {targetPercentage >= 80 ? (
              <TrendingDown className="h-3 w-3 text-green-500" />
            ) : (
              <AlertTriangle className="h-3 w-3 text-amber-500" />
            )}
            Within Target
          </p>
          <p className={cn(
            'text-sm font-semibold',
            targetPercentage >= 80 ? 'text-green-400' : 'text-amber-400'
          )}>
            {targetPercentage.toFixed(0)}% ({withinTarget}/{filteredData.length})
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
            Violations
          </p>
          <p className={cn(
            'text-sm font-semibold',
            violations.length === 0 ? 'text-green-400' : 'text-red-400'
          )}>
            {violations.length}
          </p>
        </div>
      </div>

      {/* Trend indicator */}
      <div className="mt-4 p-3 rounded-lg bg-slate-800/50 border border-slate-700">
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-400">Forecast Accuracy Trend:</span>
          <div className="flex items-center gap-2">
            {isImproving ? (
              <>
                <TrendingDown className="h-4 w-4 text-green-500" />
                <span className="text-sm font-semibold text-green-400">Improving</span>
              </>
            ) : (
              <>
                <Activity className="h-4 w-4 text-amber-500" />
                <span className="text-sm font-semibold text-amber-400">
                  {Math.abs(trendSlope) < 0.01 ? 'Stable' : 'Degrading'}
                </span>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
