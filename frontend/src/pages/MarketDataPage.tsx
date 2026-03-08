import { useState } from 'react';
import { Layout } from '@/components/Layout';
import { PriceChart } from '@/components/PriceChart';
import { useMarketData } from '@/hooks/useMarketData';
import { useLivePrices } from '@/hooks/useLivePrices';
import { formatCurrency, formatDate } from '@/lib/utils';

export function MarketDataPage() {
  const [dateRange, setDateRange] = useState<'7d' | '30d' | '90d' | '1y'>(
    '30d'
  );
  const { latestPrice, isConnected } = useLivePrices();

  const getDateRange = () => {
    const end = new Date();
    const start = new Date();
    switch (dateRange) {
      case '7d':
        start.setDate(start.getDate() - 7);
        break;
      case '30d':
        start.setDate(start.getDate() - 30);
        break;
      case '90d':
        start.setDate(start.getDate() - 90);
        break;
      case '1y':
        start.setFullYear(start.getFullYear() - 1);
        break;
    }
    return { start: start.toISOString(), end: end.toISOString() };
  };

  const { start, end } = getDateRange();
  const { data: marketData, isLoading } = useMarketData(start, end);

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1>Market Data</h1>
          <div className="flex items-center space-x-2">
            <div
              className={`h-2 w-2 rounded-full ${
                isConnected ? 'bg-success-500' : 'bg-danger-500'
              }`}
            />
            <span className="text-sm text-gray-600">
              {isConnected ? 'Live feed active' : 'Disconnected'}
            </span>
          </div>
        </div>

        {/* Live Prices */}
        {latestPrice && (
          <div className="card">
            <h2 className="mb-4">Current Prices</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div>
                <p className="text-sm text-gray-600">Jet Fuel Spot</p>
                <p className="text-2xl font-bold text-primary-600">
                  {formatCurrency(latestPrice.jet_fuel_spot)}
                </p>
              </div>
              {latestPrice.heating_oil_futures && (
                <div>
                  <p className="text-sm text-gray-600">Heating Oil Futures</p>
                  <p className="text-2xl font-bold">
                    {formatCurrency(latestPrice.heating_oil_futures)}
                  </p>
                </div>
              )}
              {(latestPrice.brent_futures ?? (latestPrice as { brent_crude_futures?: number }).brent_crude_futures) != null && (
                <div>
                  <p className="text-sm text-gray-600">Brent Crude Futures</p>
                  <p className="text-2xl font-bold">
                    {formatCurrency(latestPrice.brent_futures ?? (latestPrice as { brent_crude_futures?: number }).brent_crude_futures ?? 0)}
                  </p>
                </div>
              )}
              {(latestPrice.wti_futures ?? (latestPrice as { wti_crude_futures?: number }).wti_crude_futures) != null && (
                <div>
                  <p className="text-sm text-gray-600">WTI Crude Futures</p>
                  <p className="text-2xl font-bold">
                    {formatCurrency(latestPrice.wti_futures ?? (latestPrice as { wti_crude_futures?: number }).wti_crude_futures ?? 0)}
                  </p>
                </div>
              )}
            </div>
            <p className="text-xs text-gray-500 mt-4">
              Last updated: {formatDate(latestPrice.time, 'long')}
            </p>
          </div>
        )}

        {/* Historical Chart */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2>Historical Prices</h2>
            <div className="flex space-x-2">
              {(['7d', '30d', '90d', '1y'] as const).map((range) => (
                <button
                  key={range}
                  onClick={() => setDateRange(range)}
                  className={`px-3 py-1 text-sm rounded-md ${
                    dateRange === range
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  {range.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
          {isLoading ? (
            <div className="flex items-center justify-center h-96">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
          ) : marketData && marketData.ticks.length > 0 ? (
            <PriceChart data={marketData.ticks} showMultipleSeries />
          ) : (
            <div className="flex items-center justify-center h-96 text-gray-500">
              No data available for selected range
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
