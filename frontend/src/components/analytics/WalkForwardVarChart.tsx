import React, { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  ComposedChart,
  Brush,
} from 'recharts';
import { TrendingDown, Download, ZoomIn, Filter, BarChart3 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatMillions, formatPct } from '@/lib/formatters';

interface VarDataPoint {
  date: string;
  dynamic_var: number;
  static_var: number;
  retraining_date?: boolean;
}

interface WalkForwardVarChartProps {
  data: VarDataPoint[];
  isLoading?: boolean;
}

export function WalkForwardVarChart({ data, isLoading = false }: WalkForwardVarChartProps) {
  const [showRetrainingMarkers, setShowRetrainingMarkers] = useState(true);
  const [showStaticLine, setShowStaticLine] = useState(true);
  const [enableZoom, setEnableZoom] = useState(false);
  const [showDifferenceArea, setShowDifferenceArea] = useState(true);

  // Prepare data with difference calculation (guard against division by zero)
  const enrichedData = React.useMemo(() => {
    return data.map(d => ({
      ...d,
      difference: d.static_var - d.dynamic_var,
      improvement_pct: d.static_var > 0 ? ((d.static_var - d.dynamic_var) / d.static_var) * 100 : 0
    }));
  }, [data]);
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const formatCurrency = (value: number) => formatMillions(value);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const dataPoint = enrichedData.find(d => d.date === label);
      const isRetrainingDate = dataPoint?.retraining_date;
      
      return (
        <div className="bg-slate-900 border border-slate-700 rounded-lg p-4 shadow-xl min-w-[220px]">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-slate-400 font-semibold">
              {formatDate(label)}
            </p>
            {isRetrainingDate && (
              <span className="px-2 py-0.5 bg-primary-600 text-white rounded text-xs font-semibold">
                Retrain
              </span>
            )}
          </div>
          
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center justify-between gap-4 mb-2">
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: entry.color }}
                />
                <span className="text-xs text-slate-300">
                  {entry.name.replace('_', ' ')}:
                </span>
              </div>
              <span className="text-sm font-bold text-white">
                {formatCurrency(entry.value)}
              </span>
            </div>
          ))}
          
          {dataPoint && (
            <>
              <div className="mt-3 pt-3 border-t border-slate-700 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400">Improvement:</span>
                  <span className="text-xs font-semibold text-green-400">
                    {formatCurrency(dataPoint.difference)} ({formatPct(dataPoint.improvement_pct)})
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400">VaR Reduction:</span>
                  <div className="flex items-center gap-1">
                    <TrendingDown className="h-3 w-3 text-green-500" />
                    <span className="text-xs font-semibold text-green-400">
                      {dataPoint.static_var > 0
                        ? formatPct((dataPoint.difference / dataPoint.static_var) * 100)
                        : formatPct(0)}
                    </span>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      );
    }
    return null;
  };

  const CustomLegend = ({ payload }: any) => {
    return (
      <div className="flex items-center justify-center gap-6 mt-4">
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-sm text-slate-300 capitalize">
              {entry.value.replace('_', ' ')}
            </span>
          </div>
        ))}
      </div>
    );
  };

  // Calculate summary statistics (guard against empty data)
  const hasData = enrichedData.length > 0;
  const avgDynamic = hasData ? enrichedData.reduce((sum, d) => sum + d.dynamic_var, 0) / enrichedData.length : 0;
  const avgStatic = hasData ? enrichedData.reduce((sum, d) => sum + d.static_var, 0) / enrichedData.length : 0;
  const improvement = avgStatic > 0 ? ((avgStatic - avgDynamic) / avgStatic) * 100 : 0;
  const maxImprovement = hasData ? Math.max(...enrichedData.map(d => d.improvement_pct)) : 0;
  const retrainingCount = enrichedData.filter(d => d.retraining_date).length;

  const downloadData = () => {
    const csv = [
      ['Date', 'Dynamic VaR', 'Static VaR', 'Improvement ($)', 'Improvement (%)', 'Retraining'],
      ...enrichedData.map(d => [
        d.date,
        d.dynamic_var,
        d.static_var,
        d.difference,
        d.improvement_pct.toFixed(2),
        d.retraining_date ? 'Yes' : 'No'
      ])
    ].map(row => row.join(',')).join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `var_analysis_${new Date().toISOString()}.csv`;
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
        <h3 className="text-lg font-semibold text-white mb-2">
          Dynamic vs Static Hedge Ratio VaR
        </h3>
        <p className="text-sm text-slate-400 mb-4">
          Walk-forward analysis comparing dynamic rebalancing against static hedge ratio
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
                  value: 'VaR (USD)',
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
          <h3 className="text-lg font-semibold text-white mb-2">
            Dynamic vs Static Hedge Ratio VaR
          </h3>
          <p className="text-sm text-slate-400">
            Walk-forward analysis comparing dynamic rebalancing against static hedge ratio
          </p>
        </div>
        <div className="text-right">
          <div className="flex items-center gap-2 mb-1">
            <TrendingDown className="h-4 w-4 text-green-500" />
            <span className="text-sm font-semibold text-green-400">
              {formatPct(improvement)} Improvement
            </span>
          </div>
          <p className="text-xs text-slate-500">
            Average VaR reduction with dynamic HR
          </p>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowRetrainingMarkers(!showRetrainingMarkers)}
            className={cn(
              'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5',
              showRetrainingMarkers
                ? 'bg-primary-600/20 text-primary-400 border border-primary-600/30'
                : 'text-slate-400 hover:text-white border border-slate-700'
            )}
          >
            <Filter className="h-3.5 w-3.5" />
            <span>Retrain Markers</span>
          </button>
          <button
            onClick={() => setShowStaticLine(!showStaticLine)}
            className={cn(
              'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
              showStaticLine
                ? 'bg-slate-700 text-white'
                : 'text-slate-400 hover:text-white border border-slate-700'
            )}
          >
            Static Baseline
          </button>
          <button
            onClick={() => setShowDifferenceArea(!showDifferenceArea)}
            className={cn(
              'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
              showDifferenceArea
                ? 'bg-green-600/20 text-green-400 border border-green-600/30'
                : 'text-slate-400 hover:text-white border border-slate-700'
            )}
          >
            Show Savings
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
        <ComposedChart data={enrichedData} margin={{ top: 5, right: 5, left: 5, bottom: enableZoom ? 35 : 5 }}>
          <defs>
            <linearGradient id="improvementGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0.05} />
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
            tickFormatter={formatCurrency}
            stroke="#64748b"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            tickLine={{ stroke: '#475569' }}
            width={70}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#475569', strokeWidth: 1 }} />
          <Legend content={<CustomLegend />} />

          {/* Average lines */}
          <ReferenceLine
            y={avgDynamic}
            stroke="#3b82f6"
            strokeDasharray="3 3"
            strokeOpacity={0.5}
            label={{
              value: `Avg Dynamic: ${formatCurrency(avgDynamic)}`,
              position: 'insideTopRight',
              fill: '#3b82f6',
              fontSize: 10
            }}
          />
          {showStaticLine && (
            <ReferenceLine
              y={avgStatic}
              stroke="#64748b"
              strokeDasharray="3 3"
              strokeOpacity={0.5}
              label={{
                value: `Avg Static: ${formatCurrency(avgStatic)}`,
                position: 'insideTopRight',
                fill: '#64748b',
                fontSize: 10
              }}
            />
          )}

          {/* Vertical lines for retraining dates */}
          {showRetrainingMarkers && enrichedData
            .filter(d => d.retraining_date)
            .map((d, i) => (
              <ReferenceLine
                key={i}
                x={d.date}
                stroke="#3b82f6"
                strokeDasharray="3 3"
                strokeOpacity={0.6}
                strokeWidth={2}
                label={{
                  value: '↻',
                  position: 'top',
                  fill: '#3b82f6',
                  fontSize: 16
                }}
              />
            ))}

          {/* Improvement area (difference between static and dynamic) */}
          {showDifferenceArea && (
            <Area
              type="monotone"
              dataKey="difference"
              stroke="none"
              fill="url(#improvementGradient)"
              fillOpacity={1}
              animationDuration={800}
            />
          )}

          {/* Static VaR Line */}
          {showStaticLine && (
            <Line
              type="monotone"
              dataKey="static_var"
              stroke="#64748b"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              name="Static VaR"
              animationDuration={800}
            />
          )}

          {/* Dynamic VaR Line */}
          <Line
            type="monotone"
            dataKey="dynamic_var"
            stroke="#3b82f6"
            strokeWidth={3}
            dot={{ fill: '#3b82f6', r: 4, strokeWidth: 2, stroke: '#0f172a' }}
            activeDot={{ r: 6, strokeWidth: 2 }}
            name="Dynamic VaR"
            animationDuration={800}
          />

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
      <div className="mt-6 grid grid-cols-4 gap-4 pt-4 border-t border-slate-800">
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
            Avg Dynamic VaR
          </p>
          <p className="text-sm font-semibold text-primary-400">
            {formatCurrency(avgDynamic)}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
            Avg Static VaR
          </p>
          <p className="text-sm font-semibold text-slate-400">
            {formatCurrency(avgStatic)}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
            Max Improvement
          </p>
          <div className="flex items-center gap-1">
            <TrendingDown className="h-3.5 w-3.5 text-green-500" />
            <p className="text-sm font-semibold text-green-400">
              {formatPct(maxImprovement)}
            </p>
          </div>
        </div>
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
            Retraining Events
          </p>
          <p className="text-sm font-semibold text-white">
            {retrainingCount}
          </p>
        </div>
      </div>
    </div>
  );
}
