import { Activity, AlertCircle, Check, Info } from 'lucide-react';

export type DataSourceType = 
  | 'simulation'
  | 'analytics'
  | 'yahoo_finance'
  | 'eia'
  | 'massive'
  | 'mixed'
  | 'disconnected';

interface DataSourceBadgeProps {
  source: DataSourceType;
  isConnected: boolean;
  lastUpdated?: Date;
  className?: string;
  showDetails?: boolean;
  sourceBreakdown?: Record<string, string>;  // instrument -> source mapping
}

export function DataSourceBadge({ 
  source, 
  isConnected, 
  lastUpdated,
  className = '',
  showDetails = false,
  sourceBreakdown
}: DataSourceBadgeProps) {
  const getSourceLabel = () => {
    switch (source) {
      case 'simulation':
        return 'Simulated';
      case 'analytics':
        return 'Analytics';
      case 'yahoo_finance':
        return 'Yahoo Finance';
      case 'eia':
        return 'EIA Official';
      case 'massive':
        return 'Massive Live';
      case 'mixed':
        return 'Mixed Sources';
      case 'disconnected':
        return 'Disconnected';
      default:
        return 'Unknown';
    }
  };

  const getSourceColor = () => {
    if (!isConnected) return 'bg-red-500';
    
    switch (source) {
      case 'yahoo_finance':
      case 'massive':
        return 'bg-green-500';  // Real-time = Green
      case 'eia':
        return 'bg-yellow-500'; // Official but delayed = Yellow
      case 'mixed':
        return 'bg-purple-500'; // Multiple sources = Purple
      case 'simulation':
        return 'bg-blue-500';   // Simulated = Blue
      case 'analytics':
        return 'bg-green-500';  // Pipeline/Analytics = Green
      default:
        return 'bg-blue-500';
    }
  };

  const getSourceIcon = () => {
    if (!isConnected) return <AlertCircle className="h-3 w-3" />;
    
    switch (source) {
      case 'yahoo_finance':
      case 'massive':
        return <Check className="h-3 w-3" />;
      case 'eia':
        return <Info className="h-3 w-3" />;
      default:
        return <Activity className="h-3 w-3" />;
    }
  };

  const getSourceDescription = () => {
    switch (source) {
      case 'yahoo_finance':
        return 'Real-time futures data (15-min delay)';
      case 'eia':
        return 'Official U.S. government data (1-day lag)';
      case 'massive':
        return 'Live exchange data';
      case 'simulation':
        return 'Realistic GBM simulation';
      case 'analytics':
        return 'Pipeline forecast from historical data';
      case 'mixed':
        return 'Using multiple data sources';
      default:
        return '';
    }
  };

  const getTimeAgo = () => {
    if (!lastUpdated) return '';
    const seconds = Math.floor((Date.now() - lastUpdated.getTime()) / 1000);
    if (seconds < 5) return 'just now';
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    return `${minutes}m ago`;
  };

  return (
    <div className={`inline-flex flex-col gap-2 ${className}`}>
      {/* Main Badge */}
      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800 border border-slate-700">
        {/* Status Dot */}
        <div className="relative">
          <div className={`w-2 h-2 rounded-full ${getSourceColor()}`} />
          {isConnected && (
            <div className={`absolute inset-0 w-2 h-2 rounded-full ${getSourceColor()} animate-ping opacity-75`} />
          )}
        </div>

        {/* Icon */}
        <div className={`${isConnected ? 'text-slate-300' : 'text-red-400'}`}>
          {getSourceIcon()}
        </div>

        {/* Source Label */}
        <span className="text-xs font-medium text-slate-300">
          {getSourceLabel()}
        </span>

        {/* Connection Status */}
        {!isConnected && (
          <span className="text-xs text-red-400">• Disconnected</span>
        )}

        {/* Last Updated */}
        {isConnected && lastUpdated && (
          <span className="text-xs text-slate-500">
            • {getTimeAgo()}
          </span>
        )}
      </div>

      {/* Details (if enabled) */}
      {showDetails && isConnected && (
        <div className="px-3 py-2 rounded-lg bg-slate-800/50 border border-slate-700/50">
          <p className="text-xs text-slate-400 mb-2">{getSourceDescription()}</p>
          
          {sourceBreakdown && Object.keys(sourceBreakdown).length > 0 && (
            <div className="space-y-1">
              <p className="text-xs font-medium text-slate-300 mb-1">Source Breakdown:</p>
              {Object.entries(sourceBreakdown).map(([instrument, source]) => (
                <div key={instrument} className="flex items-center gap-2 text-xs">
                  <span className="text-slate-400 capitalize">
                    {instrument.replace('_', ' ')}:
                  </span>
                  <span className="text-slate-300 font-medium">{source}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
