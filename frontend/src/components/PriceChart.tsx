import { useState, useEffect, useMemo } from 'react';
import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  Brush,
} from 'recharts';
import { formatCurrency, formatDate, cn } from '@/lib/utils';
import { useLivePrices } from '@/hooks/useLivePrices';
import { DataSourceBadge } from '@/components/ui/DataSourceBadge';
import { 
  TrendingUp, 
  TrendingDown, 
  Activity,
  Download,
  ZoomIn,
  LineChart as LineChartIcon,
  Clock,
} from 'lucide-react';

interface PriceTickInput {
  time: string;
  jet_fuel_spot: number;
  heating_oil_futures: number | null;
  brent_futures: number | null;
  wti_futures: number | null;
  volatility_index?: number | null;
}

interface PriceChartProps {
  showMultipleSeries?: boolean;
  data?: PriceTickInput[];
}

export function PriceChart({ showMultipleSeries = false, data: externalData }: PriceChartProps) {
  const live = useLivePrices();
  const prices = externalData ?? live.prices;
  const { latestTick, isConnected, dataSource } = live;
  
  const [chartType, setChartType] = useState<'line' | 'area'>('line');
  const [selectedSeries, setSelectedSeries] = useState<string[]>(['jetFuel']);
  const [showVolatility, setShowVolatility] = useState(false);
  const [enableZoom, setEnableZoom] = useState(false);
  const [showMovingAverage, setShowMovingAverage] = useState(false);
  const [secondsSinceUpdate, setSecondsSinceUpdate] = useState(0);

  // Track time since last update
  useEffect(() => {
    setSecondsSinceUpdate(0);
    const interval = setInterval(() => {
      setSecondsSinceUpdate(prev => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [latestTick]);

  // Calculate moving average
  const calculateMA = (dataPoints: number[], period: number = 20) => {
    return dataPoints.map((_, index) => {
      if (index < period - 1) return null;
      const slice = dataPoints.slice(index - period + 1, index + 1);
      return slice.reduce((sum, val) => sum + val, 0) / period;
    });
  };

  // Transform price ticks into chart data
  const chartData = useMemo(() => {
    return prices.map((tick, index) => {
      const jetFuelValues = prices.slice(0, index + 1).map(t => t.jet_fuel_spot ?? 0);
      const ma20 = calculateMA(jetFuelValues, 20);
      const vol = tick.volatility_index ?? 0;
      return {
        time: new Date(tick.time).getTime(),
        timeLabel: formatDate(tick.time, 'short'),
        jetFuel: tick.jet_fuel_spot ?? 0,
        heatingOil: tick.heating_oil_futures ?? 0,
        brent: tick.brent_futures ?? 0,
        wti: tick.wti_futures ?? 0,
        ma20: ma20[ma20.length - 1],
        volatility: vol / 10,
      };
    });
  }, [prices]);

  // Calculate session open (first tick of data)
  const sessionOpen = useMemo(() => {
    if (chartData.length === 0) return null;
    const first = chartData[0];
    if (!first) return null;
    return {
      jetFuel: first.jetFuel,
      heatingOil: first.heatingOil,
      brent: first.brent,
      wti: first.wti,
    };
  }, [chartData]);

  // Calculate statistics
  const stats = useMemo(() => {
    if (chartData.length === 0) {
      return { firstPrice: 0, lastPrice: 0, priceChange: 0, priceChangePercent: 0, highPrice: 0, lowPrice: 0, avgVolatility: 0 };
    }
    
    const first = chartData[0];
    const last = chartData[chartData.length - 1];
    const firstPrice = first?.jetFuel ?? 0;
    const lastPrice = last?.jetFuel ?? 0;
    const priceChange = lastPrice - firstPrice;
    const priceChangePercent = (priceChange / firstPrice) * 100;
    const highPrice = Math.max(...chartData.map(d => d.jetFuel));
    const lowPrice = Math.min(...chartData.map(d => d.jetFuel));
    const avgVolatility = chartData.reduce((sum, d) => sum + d.volatility, 0) / chartData.length;

    return { firstPrice, lastPrice, priceChange, priceChangePercent, highPrice, lowPrice, avgVolatility };
  }, [chartData]);

  const seriesConfig = {
    jetFuel: { name: 'Jet Fuel Spot', color: '#0ea5e9', enabled: selectedSeries.includes('jetFuel') },
    heatingOil: { name: 'Heating Oil', color: '#f59e0b', enabled: selectedSeries.includes('heatingOil') },
    brent: { name: 'Brent Crude', color: '#22c55e', enabled: selectedSeries.includes('brent') },
    wti: { name: 'WTI Crude', color: '#ef4444', enabled: selectedSeries.includes('wti') },
  };

  const toggleSeries = (series: string) => {
    setSelectedSeries(prev =>
      prev.includes(series) ? prev.filter(s => s !== series) : [...prev, series]
    );
  };

  const downloadData = () => {
    const csv = [
      ['Time', 'Jet Fuel', 'Heating Oil', 'Brent', 'WTI', 'MA(20)', 'Volatility'],
      ...chartData.map(d => [
        d.timeLabel,
        d.jetFuel.toFixed(2),
        d.heatingOil.toFixed(2),
        d.brent.toFixed(2),
        d.wti.toFixed(2),
        d.ma20?.toFixed(2) || '',
        d.volatility.toFixed(4)
      ])
    ].map(row => row.join(',')).join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `price_data_${new Date().toISOString()}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-slate-900 border border-slate-700 rounded-lg p-4 shadow-xl min-w-[220px]">
          <p className="text-xs text-slate-400 mb-3 font-semibold">{label}</p>
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center justify-between gap-4 mb-2">
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: entry.color }}
                />
                <span className="text-xs text-slate-300">{entry.name}:</span>
              </div>
              <span className="text-sm font-bold text-white">
                {formatCurrency(entry.value)}
              </span>
            </div>
          ))}
          {showVolatility && payload[0]?.payload?.volatility && (
            <div className="mt-3 pt-3 border-t border-slate-700">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">Volatility:</span>
                <span className="text-xs font-semibold text-amber-400">
                  {(payload[0].payload.volatility * 10).toFixed(2)}%
                </span>
              </div>
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="card">
      {/* Header with Statistics */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-1">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              Live Market Prices
              {isConnected && (
                <span className="flex items-center gap-1 text-xs font-normal text-green-400">
                  <Activity className="h-3 w-3 animate-pulse" />
                  Live
                </span>
              )}
            </h3>
            <DataSourceBadge source={dataSource} isConnected={isConnected} />
          </div>
          <div className="flex items-center gap-3">
            <p className="text-sm text-slate-400">
              Real-time commodity price movements
            </p>
            <div className={cn(
              "flex items-center gap-1.5 text-xs px-2 py-1 rounded",
              secondsSinceUpdate > 15 ? "bg-red-500/10 text-red-400" :
              secondsSinceUpdate > 5 ? "bg-amber-500/10 text-amber-400" :
              "bg-slate-800 text-slate-400"
            )}>
              <Clock className="h-3 w-3" />
              <span>Updated {secondsSinceUpdate}s ago</span>
            </div>
          </div>
        </div>

        {/* Price Stats */}
        <div className="grid grid-cols-3 gap-4">
          <div className="text-right">
            <div className="flex items-center justify-end gap-1 mb-1">
              {stats.priceChange >= 0 ? (
                <TrendingUp className="h-3.5 w-3.5 text-green-500" />
              ) : (
                <TrendingDown className="h-3.5 w-3.5 text-red-500" />
              )}
              <span className={cn(
                "text-xs font-semibold",
                stats.priceChange >= 0 ? "text-green-400" : "text-red-400"
              )}>
                {stats.priceChange >= 0 ? '+' : ''}{stats.priceChangePercent.toFixed(2)}%
              </span>
            </div>
            <p className="text-xs text-slate-500">Change</p>
          </div>
          <div className="text-right">
            <div className="mb-1">
              <span className="text-xs font-semibold text-white">
                {formatCurrency(stats.lastPrice)}
              </span>
            </div>
            <p className="text-xs text-slate-500">Current</p>
          </div>
          <div className="text-right">
            <div className="mb-1">
              <span className="text-xs font-semibold text-amber-400">
                ${(stats.avgVolatility * 10).toFixed(2)}%
              </span>
            </div>
            <p className="text-xs text-slate-500">Volatility</p>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {/* Chart Type Selector */}
          <div className="flex items-center gap-1 bg-slate-800 rounded-lg p-1">
            <button
              onClick={() => setChartType('line')}
              className={cn(
                'px-2 py-1 rounded-md transition-colors flex items-center gap-1',
                chartType === 'line'
                  ? 'bg-primary-600 text-white'
                  : 'text-slate-400 hover:text-white'
              )}
              title="Line Chart"
            >
              <LineChartIcon className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => setChartType('area')}
              className={cn(
                'px-2 py-1 rounded-md transition-colors flex items-center gap-1',
                chartType === 'area'
                  ? 'bg-primary-600 text-white'
                  : 'text-slate-400 hover:text-white'
              )}
              title="Area Chart"
            >
              <Activity className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Series Selectors */}
          {showMultipleSeries && (
            <div className="flex items-center gap-1">
              {Object.entries(seriesConfig).map(([key, config]) => (
                <button
                  key={key}
                  onClick={() => toggleSeries(key)}
                  className={cn(
                    'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
                    config.enabled
                      ? 'text-white border'
                      : 'text-slate-400 hover:text-white border border-slate-700'
                  )}
                  style={config.enabled ? { 
                    borderColor: config.color, 
                    backgroundColor: `${config.color}20` 
                  } : {}}
                >
                  {config.name.split(' ')[0]}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowMovingAverage(!showMovingAverage)}
            className={cn(
              'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
              showMovingAverage
                ? 'bg-primary-600/20 text-primary-400 border border-primary-600/30'
                : 'text-slate-400 hover:text-white border border-slate-700'
            )}
          >
            MA(20)
          </button>
          <button
            onClick={() => setShowVolatility(!showVolatility)}
            className={cn(
              'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
              showVolatility
                ? 'bg-amber-600/20 text-amber-400 border border-amber-600/30'
                : 'text-slate-400 hover:text-white border border-slate-700'
            )}
          >
            Volatility
          </button>
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

      <div className="w-full" style={{ height: enableZoom ? '480px' : '420px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart 
            data={chartData} 
            margin={{ top: 5, right: 5, left: 5, bottom: enableZoom ? 35 : 5 }}
          >
            <defs>
              <linearGradient id="jetFuelGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0.05} />
              </linearGradient>
              <linearGradient id="volatilityGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis
              dataKey="timeLabel"
              tick={{ fontSize: 11, fill: '#94a3b8' }}
              tickLine={{ stroke: '#475569' }}
              stroke="#64748b"
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#94a3b8' }}
              tickLine={{ stroke: '#475569' }}
              stroke="#64748b"
              tickFormatter={(value) => formatCurrency(value, 0)}
              width={60}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#475569', strokeWidth: 1 }} />
            <Legend
              wrapperStyle={{ paddingTop: '15px' }}
              iconType="line"
              formatter={(value: string) => (
                <span className="text-sm text-slate-300">{value}</span>
              )}
            />

            {/* Session Open Reference Lines */}
            {sessionOpen && (
              <>
                {selectedSeries.includes('jetFuel') && (
                  <ReferenceLine
                    y={sessionOpen.jetFuel}
                    stroke={seriesConfig.jetFuel.color}
                    strokeDasharray="3 3"
                    strokeOpacity={0.4}
                    label={{
                      value: `Open: ${formatCurrency(sessionOpen.jetFuel, 0)}`,
                      position: 'insideTopLeft',
                      fill: seriesConfig.jetFuel.color,
                      fontSize: 10
                    }}
                  />
                )}
              </>
            )}

            {/* High/Low Reference Lines */}
            <ReferenceLine
              y={stats.highPrice}
              stroke="#22c55e"
              strokeDasharray="3 3"
              strokeOpacity={0.5}
              label={{
                value: `High: ${formatCurrency(stats.highPrice, 0)}`,
                position: 'insideTopRight',
                fill: '#22c55e',
                fontSize: 10
              }}
            />
            <ReferenceLine
              y={stats.lowPrice}
              stroke="#ef4444"
              strokeDasharray="3 3"
              strokeOpacity={0.5}
              label={{
                value: `Low: ${formatCurrency(stats.lowPrice, 0)}`,
                position: 'insideBottomRight',
                fill: '#ef4444',
                fontSize: 10
              }}
            />

            {/* Volatility indicator as background area */}
            {showVolatility && (
              <Area
                type="monotone"
                dataKey="volatility"
                stroke="none"
                fill="url(#volatilityGradient)"
                yAxisId="volatility"
                animationDuration={800}
              />
            )}

            {/* Main price lines/areas */}
            {chartType === 'area' && seriesConfig.jetFuel.enabled && (
              <Area
                type="monotone"
                dataKey="jetFuel"
                stroke={seriesConfig.jetFuel.color}
                strokeWidth={2.5}
                fill="url(#jetFuelGradient)"
                name={seriesConfig.jetFuel.name}
                dot={false}
                animationDuration={800}
              />
            )}

            {chartType === 'line' && Object.entries(seriesConfig).map(([key, config]) => {
              if (!config.enabled) return null;
              return (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={config.color}
                  strokeWidth={key === 'jetFuel' ? 2.5 : 2}
                  name={config.name}
                  dot={false}
                  activeDot={{ r: 4, strokeWidth: 2 }}
                  animationDuration={800}
                />
              );
            })}

            {/* Moving Average */}
            {showMovingAverage && (
              <Line
                type="monotone"
                dataKey="ma20"
                stroke="#a855f7"
                strokeWidth={2}
                strokeDasharray="5 5"
                name="MA(20)"
                dot={false}
                animationDuration={800}
              />
            )}

            {/* Zoom brush */}
            {enableZoom && (
              <Brush
                dataKey="timeLabel"
                height={30}
                stroke="#3b82f6"
                fill="#1e293b"
                travellerWidth={10}
              />
            )}

            {/* Hidden Y-axis for volatility */}
            {showVolatility && (
              <YAxis yAxisId="volatility" hide domain={[0, 'auto']} />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Summary Stats */}
      <div className="mt-4 grid grid-cols-4 gap-4 pt-4 border-t border-slate-800">
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
            Opening
          </p>
          <p className="text-sm font-semibold text-white">
            {formatCurrency(stats.firstPrice)}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
            High
          </p>
          <p className="text-sm font-semibold text-green-400">
            {formatCurrency(stats.highPrice)}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
            Low
          </p>
          <p className="text-sm font-semibold text-red-400">
            {formatCurrency(stats.lowPrice)}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
            Range
          </p>
          <p className="text-sm font-semibold text-white">
            {formatCurrency(stats.highPrice - stats.lowPrice)}
          </p>
        </div>
      </div>
    </div>
  );
}
