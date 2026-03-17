import { useState, useMemo } from 'react';
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Brush,
} from 'recharts';
import { TrendingUp, TrendingDown, AlertTriangle, ZoomIn, Download, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { DataSourceBadge } from '@/components/ui/DataSourceBadge';
import type { DataSourceType } from '@/components/ui/DataSourceBadge';

interface ForecastDataPoint {
  date: string;
  actual: number | null;
  forecast: number | null;
  lower_bound?: number | null;
  upper_bound?: number | null;
}

interface ForecastChartProps {
  data: ForecastDataPoint[];
  title?: string;
  isLoading?: boolean;
  /** When true, forecast is from analytics pipeline (real data). When false/undefined, shows as simulated. */
  fromAnalytics?: boolean;
  /** MAPE from API (ensemble of ARIMA + LSTM + XGBoost). Used when data has no actual values to compute accuracy. */
  mapeFromApi?: number | null;
}

export function ForecastChart({
  data,
  title = '30-Day Forecast',
  isLoading = false,
  fromAnalytics = false,
  mapeFromApi = null,
}: ForecastChartProps) {
  const dataSource: DataSourceType = fromAnalytics ? 'analytics' : 'simulation';
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d');
  const [showConfidence, setShowConfidence] = useState(true);
  const [enableZoom, setEnableZoom] = useState(true);

  // Filter data based on time range
  const filteredData = useMemo(() => {
    const daysToShow = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;
    return data.slice(0, daysToShow);
  }, [data, timeRange]);

  // Calculate statistics (supports forecast-only when no actual data)
  const stats = useMemo(() => {
    const actualData = filteredData.filter(d => d.actual !== null && d.actual !== undefined);
    const forecastData = filteredData.filter(d => d.forecast !== null && d.forecast !== undefined);

    // Use forecast values when no actual data (forward-looking chart)
    const priceValues = actualData.length > 0
      ? actualData.map(d => d.actual!)
      : forecastData.map(d => d.forecast!);

    if (priceValues.length < 2) {
      return { trend: 0, accuracy: null, volatility: 0 };
    }

    const firstPrice = priceValues[0] ?? 0;
    const lastPrice = priceValues[priceValues.length - 1] ?? 0;
    const trend = firstPrice > 0 ? ((lastPrice - firstPrice) / firstPrice) * 100 : 0;

    // Accuracy: MAPE when we have actual vs forecast; null when forecast-only (matches Dashboard KPI metric)
    let accuracy: number | null = null;
    if (actualData.length > 0 && forecastData.length > 0) {
      const errors = actualData
        .filter(d => {
          const corresponding = forecastData.find(f => f.date === d.date);
          return corresponding && d.actual !== null && corresponding.forecast !== null;
        })
        .map(d => {
          const corresponding = forecastData.find(f => f.date === d.date);
          return Math.abs((d.actual! - corresponding!.forecast!) / d.actual!) * 100;
        });
      accuracy = errors.length > 0 ? errors.reduce((sum, e) => sum + e, 0) / errors.length : null;
    }

    // Volatility: std dev of prices (actual or forecast)
    const mean = priceValues.reduce((sum, v) => sum + v, 0) / priceValues.length;
    const variance = priceValues.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / priceValues.length;
    const volatility = Math.sqrt(variance);

    return { trend, accuracy, volatility };
  }, [filteredData]);

  const downloadData = () => {
    const csv = [
      ['Date', 'Actual', 'Forecast', 'Lower Bound', 'Upper Bound'],
      ...filteredData.map(d => [
        d.date,
        d.actual ?? '',
        d.forecast ?? '',
        d.lower_bound ?? '',
        d.upper_bound ?? ''
      ])
    ].map(row => row.join(',')).join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `forecast_${new Date().toISOString()}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const formatPrice = (value: number) => {
    return `$${value.toFixed(2)}`;
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const dataPoint = filteredData.find(d => d.date === label);
      const hasActual = dataPoint?.actual !== null && dataPoint?.actual !== undefined;
      const hasForecast = dataPoint?.forecast !== null && dataPoint?.forecast !== undefined;
      
      return (
        <div className="bg-slate-900/95 border border-slate-600 rounded-xl p-4 shadow-2xl backdrop-blur-sm min-w-[200px]">
          <p className="text-xs text-slate-400 mb-3 font-semibold uppercase tracking-wider">{formatDate(label)}</p>
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center justify-between gap-4 mb-2">
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: entry.color }}
                />
                <span className="text-xs text-slate-300 capitalize">
                  {entry.name}:
                </span>
              </div>
              <span className="text-sm font-bold text-white">
                {formatPrice(entry.value)}
              </span>
            </div>
          ))}
          {hasActual && hasForecast && dataPoint && (
            <div className="mt-3 pt-2 border-t border-slate-700">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">Error:</span>
                <span className={cn(
                  "text-xs font-semibold",
                  Math.abs(dataPoint.actual! - dataPoint.forecast!) < 2 
                    ? "text-green-400" 
                    : "text-amber-400"
                )}>
                  {Math.abs(dataPoint.actual! - dataPoint.forecast!).toFixed(2)} ({
                    ((Math.abs(dataPoint.actual! - dataPoint.forecast!) / dataPoint.actual!) * 100).toFixed(1)
                  }%)
                </span>
              </div>
            </div>
          )}
          {showConfidence && dataPoint?.lower_bound && dataPoint?.upper_bound && (
            <div className="mt-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Confidence:</span>
                <span className="text-primary-400 font-medium">
                  ±${((dataPoint.upper_bound - dataPoint.lower_bound) / 2).toFixed(2)}
                </span>
              </div>
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  if (isLoading) {
    return (
      <div className="card">
        <div className="animate-pulse">
          <div className="h-6 bg-slate-800 rounded w-1/3 mb-4" />
          <div className="h-[300px] bg-slate-800 rounded" />
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
            <p className="text-slate-400">Loading forecast...</p>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && (!data || data.length === 0) && (
        <div className="flex flex-col items-center justify-center h-96">
          <div className="text-center max-w-md">
            <Clock className="h-16 w-16 text-slate-600 mx-auto mb-4" />
            <h4 className="text-lg font-semibold text-white mb-2">
              No Forecast Available
            </h4>
            <p className="text-sm text-slate-400 mb-4">
              Forecast will appear after the analytics pipeline runs successfully.
            </p>
            <p className="text-xs text-slate-500">
              Click <strong>Load CSV</strong> in the header, then <strong>Run Pipeline</strong> to generate forecasts.
            </p>
          </div>
        </div>
      )}

      {/* Chart Content */}
      {!isLoading && data && data.length > 0 && (
        <>
          {/* Header with Statistics */}
          <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6 mb-6">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 mb-1">
                <h3 className="text-xl font-semibold text-white tracking-tight">{title}</h3>
                <DataSourceBadge source={dataSource} isConnected={!isLoading} />
              </div>
              <p className="text-sm text-slate-400 mt-0.5">
                Jet fuel price prediction with {showConfidence ? 'confidence intervals' : 'point estimates'}
              </p>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-3 gap-3 lg:gap-4">
              <div className="bg-slate-800/50 border border-slate-700/80 rounded-xl px-4 py-3 text-center lg:text-right">
                <div className="flex items-center justify-center lg:justify-end gap-1.5 mb-0.5">
                  {stats.trend >= 0 ? (
                    <TrendingUp className="h-4 w-4 text-green-500 flex-shrink-0" />
                  ) : (
                    <TrendingDown className="h-4 w-4 text-red-500 flex-shrink-0" />
                  )}
                  <span className={cn(
                    "text-sm font-bold tabular-nums",
                    stats.trend >= 0 ? "text-green-400" : "text-red-400"
                  )}>
                    {stats.trend >= 0 ? '+' : ''}{stats.trend.toFixed(1)}%
                  </span>
                </div>
                <p className="text-xs text-slate-500 font-medium">Trend</p>
              </div>
              <div
                className="bg-slate-800/50 border border-slate-700/80 rounded-xl px-4 py-3 text-center lg:text-right"
                title={
                  stats.accuracy !== null
                    ? 'Accuracy from actual vs forecast overlap'
                    : mapeFromApi != null && fromAnalytics
                      ? 'MAPE of ensemble forecast (ARIMA + LSTM + XGBoost) vs validation set'
                      : 'Accuracy requires completed analytics run'
                }
              >
                <div className="mb-0.5">
                  <span className="text-sm font-bold text-primary-400 tabular-nums">
                    {stats.accuracy !== null
                      ? `${stats.accuracy.toFixed(1)}%`
                      : mapeFromApi != null && fromAnalytics
                        ? `${mapeFromApi.toFixed(1)}%`
                        : '—'}
                  </span>
                </div>
                <p className="text-xs text-slate-500 font-medium">Accuracy</p>
              </div>
              <div className="bg-slate-800/50 border border-slate-700/80 rounded-xl px-4 py-3 text-center lg:text-right">
                <div className="flex items-center justify-center lg:justify-end gap-1.5 mb-0.5">
                  <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0" />
                  <span className="text-sm font-bold text-amber-400 tabular-nums">
                    ${stats.volatility.toFixed(2)}
                  </span>
                </div>
                <p className="text-xs text-slate-500 font-medium">Volatility</p>
              </div>
            </div>
          </div>

      {/* Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
        <div className="flex items-center gap-1 bg-slate-800/80 rounded-xl p-1.5 border border-slate-700/50">
          {(['7d', '30d', '90d'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={cn(
                'px-4 py-2 text-xs font-semibold rounded-lg transition-all duration-200',
                timeRange === range
                  ? 'bg-primary-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
              )}
            >
              {range.toUpperCase()}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowConfidence(!showConfidence)}
            className={cn(
              'px-4 py-2 text-xs font-semibold rounded-xl transition-all duration-200 flex items-center gap-2',
              showConfidence
                ? 'bg-primary-600/20 text-primary-400 border border-primary-600/40'
                : 'text-slate-400 hover:text-white border border-slate-600 hover:border-slate-500'
            )}
          >
            <span>Confidence Band</span>
          </button>
          <button
            onClick={() => setEnableZoom(!enableZoom)}
            className={cn(
              'p-2 rounded-xl transition-all duration-200',
              enableZoom
                ? 'bg-primary-600/20 text-primary-400 border border-primary-600/40'
                : 'text-slate-400 hover:text-white border border-slate-600 hover:border-slate-500'
            )}
            title={enableZoom ? 'Disable zoom' : 'Enable zoom'}
          >
            <ZoomIn className="h-4 w-4" />
          </button>
          <button
            onClick={downloadData}
            className="p-2 rounded-xl text-slate-400 hover:text-white border border-slate-600 hover:border-slate-500 transition-all duration-200"
            title="Download CSV"
          >
            <Download className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Chart - subtle gradient background */}
      <div className="rounded-xl bg-gradient-to-b from-slate-800/30 to-transparent border border-slate-700/50 p-4">
      <ResponsiveContainer width="100%" height={360}>
        <ComposedChart data={filteredData} margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
          <defs>
            <linearGradient id="confidenceBand" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" strokeOpacity={0.6} vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
            stroke="#64748b"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            tickLine={{ stroke: '#475569' }}
          />
          <YAxis
            tickFormatter={formatPrice}
            stroke="#64748b"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            tickLine={{ stroke: '#475569' }}
            width={60}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#475569', strokeWidth: 1 }} />
          <Legend
            wrapperStyle={{ paddingTop: '24px' }}
            iconType="line"
            iconSize={10}
            formatter={(value: string) => (
              <span className="text-sm text-slate-300 capitalize font-medium">{value.replace('_', ' ')}</span>
            )}
          />
          
          {/* Reference line for current price */}
          {filteredData.find(d => d.actual !== null) && (
            <ReferenceLine
              y={filteredData.filter(d => d.actual !== null).slice(-1)[0]?.actual ?? 0}
              stroke="#64748b"
              strokeDasharray="3 3"
              strokeOpacity={0.5}
              label={{
                value: 'Current',
                position: 'right',
                fill: '#94a3b8',
                fontSize: 10
              }}
            />
          )}

          {/* Confidence band */}
          {showConfidence && (
            <>
              <Area
                type="monotone"
                dataKey="upper_bound"
                stroke="none"
                fill="url(#confidenceBand)"
                fillOpacity={1}
                isAnimationActive={true}
                animationDuration={800}
              />
              <Area
                type="monotone"
                dataKey="lower_bound"
                stroke="none"
                fill="#0f172a"
                fillOpacity={1}
                isAnimationActive={true}
                animationDuration={800}
              />
            </>
          )}

          {/* Actual price line */}
          <Line
            type="monotone"
            dataKey="actual"
            stroke="#ffffff"
            strokeWidth={2.5}
            dot={{ fill: '#ffffff', r: 4, strokeWidth: 2, stroke: '#0f172a' }}
            activeDot={{ r: 6, strokeWidth: 2 }}
            name="Actual"
            connectNulls
            animationDuration={800}
          />

          {/* Forecast line */}
          <Line
            type="monotone"
            dataKey="forecast"
            stroke="#3b82f6"
            strokeWidth={2.5}
            strokeDasharray="5 5"
            dot={{ fill: '#3b82f6', r: 4, strokeWidth: 2, stroke: '#0f172a' }}
            activeDot={{ r: 6, strokeWidth: 2 }}
            name="Forecast"
            connectNulls
            animationDuration={800}
          />

          {/* Zoom brush */}
          {enableZoom && filteredData.length > 10 && (
            <Brush
              dataKey="date"
              height={28}
              stroke="#475569"
              fill="#1e293b"
              tickFormatter={formatDate}
              travellerWidth={12}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
      </div>
        </>
      )}
    </div>
  );
}
