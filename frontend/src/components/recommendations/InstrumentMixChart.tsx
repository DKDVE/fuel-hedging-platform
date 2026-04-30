import { useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Sector } from 'recharts';
import { TrendingUp, Download, Info } from 'lucide-react';

interface InstrumentMixChartProps {
  instrumentMix: Record<string, number>;
}

/** Active shape: center label + highlighted sector only. No external labels to avoid clipping the upper half. */
const renderActiveShape = (props: unknown) => {
  const p = props as {
    cx: number;
    cy: number;
    innerRadius: number;
    outerRadius: number;
    startAngle: number;
    endAngle: number;
    fill: string;
    payload: { name: string };
  };
  const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill, payload } = p;
  return (
    <g>
      <text x={cx} y={cy} dy={8} textAnchor="middle" fill="#fff" fontSize={14} fontWeight="bold">
        {payload.name}
      </text>
      <Sector
        cx={cx}
        cy={cy}
        innerRadius={innerRadius}
        outerRadius={outerRadius}
        startAngle={startAngle}
        endAngle={endAngle}
        fill={fill}
        stroke="#f8fafc"
        strokeWidth={2}
      />
    </g>
  );
};

export function InstrumentMixChart({ instrumentMix }: InstrumentMixChartProps) {
  const [activeIndex, setActiveIndex] = useState<number>(0);
  const [showDetails, setShowDetails] = useState(true);
  
  // Convert instrument mix to chart data, sorted by value descending so primary instrument is first
  const data = instrumentMix && typeof instrumentMix === 'object'
    ? Object.entries(instrumentMix)
        .filter(([_, value]) => Number(value) > 0)
        .map(([name, value]) => {
          const numVal = Number(value);
          return {
            name: name.charAt(0).toUpperCase() + name.slice(1),
            value: numVal * 100,
            percentage: (numVal * 100).toFixed(1),
          };
        })
        .sort((a, b) => b.value - a.value)
    : [];

  // Color mapping for instruments with gradients
  const COLORS: Record<string, string> = {
    Futures: '#3b82f6',   // blue
    Options: '#14b8a6',   // teal
    Collars: '#f59e0b',   // amber
    Swaps: '#a855f7',     // purple
    Forwards: '#ec4899',  // pink
    Swaptions: '#10b981', // green
  };

  // Risk levels for each instrument type
  const INSTRUMENT_INFO: Record<string, { risk: string; liquidity: string }> = {
    Futures: { risk: 'Low', liquidity: 'High' },
    Options: { risk: 'Medium', liquidity: 'High' },
    Collars: { risk: 'Low', liquidity: 'Medium' },
    Swaps: { risk: 'Medium', liquidity: 'Medium' },
    Forwards: { risk: 'Low', liquidity: 'High' },
    Swaptions: { risk: 'High', liquidity: 'Low' },
  };

  const downloadData = () => {
    const csv = [
      ['Instrument', 'Allocation (%)', 'Risk Level', 'Liquidity'],
      ...data.map(d => [
        d.name,
        d.percentage,
        INSTRUMENT_INFO[d.name]?.risk || 'N/A',
        INSTRUMENT_INFO[d.name]?.liquidity || 'N/A'
      ])
    ].map(row => row.join(',')).join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `instrument_mix_${new Date().toISOString()}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const onPieEnter = (_: any, index: number) => {
    setActiveIndex(index);
  };

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const info = INSTRUMENT_INFO[payload[0].name];
      return (
        <div className="bg-slate-900 border border-slate-700 rounded-lg p-4 shadow-xl min-w-[180px]">
          <p className="text-sm font-semibold text-white mb-2">
            {payload[0].name}
          </p>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400">Allocation:</span>
              <span className="text-lg font-bold text-primary-400">
                {payload[0].payload.percentage}%
              </span>
            </div>
            {info && (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400">Risk Level:</span>
                  <span className={`text-xs font-semibold ${
                    info.risk === 'Low' ? 'text-green-400' :
                    info.risk === 'Medium' ? 'text-amber-400' :
                    'text-red-400'
                  }`}>
                    {info.risk}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400">Liquidity:</span>
                  <span className={`text-xs font-semibold ${
                    info.liquidity === 'High' ? 'text-green-400' :
                    info.liquidity === 'Medium' ? 'text-amber-400' :
                    'text-red-400'
                  }`}>
                    {info.liquidity}
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      );
    }
    return null;
  };

  const CustomLegend = () => {
    if (!data || data.length === 0) return null;
    return (
      <div className="flex flex-col gap-2">
        {data.map((entry, index) => {
          const name = entry.name;
          const info = INSTRUMENT_INFO[name];
          const isActive = index === activeIndex;
          return (
            <div
              key={index}
              className={`flex items-center justify-between px-3 py-2 rounded-lg transition-all cursor-pointer ${
                isActive ? 'bg-slate-800/50 border border-slate-700' : 'hover:bg-slate-800/30'
              }`}
              onMouseEnter={() => setActiveIndex(index)}
            >
              <div className="flex items-center gap-3">
                <div
                  className={`w-3 h-3 rounded-full transition-all ${
                    isActive ? 'w-4 h-4' : ''
                  }`}
                  style={{ backgroundColor: COLORS[name] || '#64748b' }}
                />
                <div>
                  <span className="text-sm text-slate-300 font-medium">{name}</span>
                  {info && showDetails && (
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className={`text-xs ${
                        info.risk === 'Low' ? 'text-green-400' :
                        info.risk === 'Medium' ? 'text-amber-400' :
                        'text-red-400'
                      }`}>
                        {info.risk} Risk
                      </span>
                      <span className="text-xs text-slate-600">•</span>
                      <span className={`text-xs ${
                        info.liquidity === 'High' ? 'text-green-400' :
                        info.liquidity === 'Medium' ? 'text-amber-400' :
                        'text-red-400'
                      }`}>
                        {info.liquidity} Liquidity
                      </span>
                    </div>
                  )}
                </div>
              </div>
              <span className={`text-sm font-semibold transition-all ${
                isActive ? 'text-white text-base' : 'text-slate-400'
              }`}>
                {entry.percentage}%
              </span>
            </div>
          );
        })}
      </div>
    );
  };

  if (data.length === 0) {
    return (
      <div className="card">
        <h3 className="text-lg font-semibold text-white mb-4">Instrument Mix</h3>
        <div className="flex items-center justify-center h-64 text-slate-500">
          <p>No instrument allocation data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card overflow-visible relative z-10">
      {/* Header - separated from chart to prevent overlap */}
      <div className="flex items-start justify-between mb-8 pb-4 border-b border-slate-800">
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-semibold text-white mb-1">Instrument Mix</h3>
          <p className="text-sm text-slate-400">
            Recommended allocation across hedging instruments
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 ml-2">
          <button
            onClick={() => setShowDetails(!showDetails)}
            className={`p-2 rounded-lg transition-colors ${
              showDetails
                ? 'bg-primary-600/20 text-primary-400 border border-primary-600/30'
                : 'text-slate-400 hover:text-white border border-slate-700'
            }`}
            title="Toggle Details"
          >
            <Info className="h-4 w-4" />
          </button>
          <button
            onClick={downloadData}
            className="p-2 rounded-lg transition-colors text-slate-400 hover:text-white border border-slate-700"
            title="Download CSV"
          >
            <Download className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Chart + legend are separate blocks to prevent overlap */}
      <div className="pt-4 overflow-visible relative">
        <ResponsiveContainer width="100%" height={220}>
          <PieChart margin={{ top: 8, right: 24, bottom: 8, left: 24 }}>
            <Tooltip content={<CustomTooltip />} />
            <Pie
              activeIndex={activeIndex}
              activeShape={renderActiveShape}
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={65}
              outerRadius={100}
              paddingAngle={1}
              dataKey="value"
              onMouseEnter={onPieEnter}
              animationBegin={0}
              animationDuration={800}
            >
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={COLORS[entry.name] || '#64748b'}
                  stroke={index === activeIndex ? '#f8fafc' : '#0b1220'}
                  strokeWidth={index === activeIndex ? 2 : 1.5}
                  style={{
                    filter: index === activeIndex
                      ? 'drop-shadow(0 0 8px rgba(248, 250, 252, 0.2))'
                      : 'drop-shadow(0 0 6px rgba(37, 99, 235, 0.18))'
                  }}
                />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="mt-4">
          <CustomLegend />
        </div>
      </div>

      {/* Summary Statistics */}
      <div className="mt-4 pt-4 border-t border-slate-800">
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
              Primary Instrument
            </p>
            <p className="text-sm font-semibold text-white">
              {data.sort((a, b) => b.value - a.value)[0]?.name || 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
              Diversification
            </p>
            <div className="flex items-center gap-1">
              <TrendingUp className="h-3.5 w-3.5 text-green-500" />
              <p className="text-sm font-semibold text-white">
                {data.length} instrument{data.length !== 1 ? 's' : ''}
              </p>
            </div>
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
              Top Allocation
            </p>
            <p className="text-sm font-semibold text-primary-400">
              {data.sort((a, b) => b.value - a.value)[0]?.percentage || '0'}%
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
