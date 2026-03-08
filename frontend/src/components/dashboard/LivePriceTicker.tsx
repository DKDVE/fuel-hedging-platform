import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { LivePriceFeedEvent } from '@/types/api';

interface PriceTickerProps {
  prices: LivePriceFeedEvent[];
  isConnected: boolean;
}

interface PriceItemProps {
  label: string;
  price: number | null;
  change?: number;
}

function PriceItem({ label, price, change }: PriceItemProps) {
  // Handle both null and undefined
  if (price === null || price === undefined || isNaN(price)) return null;

  const getChangeColor = () => {
    if (!change) return 'text-slate-400';
    if (change > 0) return 'text-green-500';
    if (change < 0) return 'text-red-500';
    return 'text-slate-400';
  };

  const getChangeIcon = () => {
    if (!change) return <Minus className="h-3 w-3" />;
    if (change > 0) return <TrendingUp className="h-3 w-3" />;
    return <TrendingDown className="h-3 w-3" />;
  };

  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-slate-900 rounded-lg border border-slate-800 min-w-[180px]">
      <div className="flex-1">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide">
          {label}
        </p>
        <p className="text-lg font-bold text-white mt-0.5">
          ${price.toFixed(2)}
        </p>
      </div>
      {change !== undefined && !isNaN(change) && (
        <div className={cn("flex items-center gap-0.5", getChangeColor())}>
          {getChangeIcon()}
          <span className="text-xs font-semibold">
            {Math.abs(change).toFixed(2)}%
          </span>
        </div>
      )}
    </div>
  );
}

export function LivePriceTicker({ prices, isConnected }: PriceTickerProps) {
  // Handle undefined or empty prices array
  if (!prices || prices.length === 0) {
    return (
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-white">Live Market Prices</h3>
            <p className="text-sm text-slate-400 mt-1">Waiting for price data...</p>
          </div>
          <div className="flex items-center gap-2">
            <div className={cn(
              "h-2 w-2 rounded-full",
              isConnected ? "bg-green-500 animate-pulse" : "bg-red-500"
            )} />
            <span className="text-xs text-slate-400">
              {isConnected ? 'Connecting...' : 'Disconnected'}
            </span>
          </div>
        </div>
        <div className="flex items-center justify-center h-32 text-slate-500">
          <div className="animate-pulse">Connecting to price stream...</div>
        </div>
      </div>
    );
  }

  const latestPrice = prices[prices.length - 1];
  const previousPrice = prices[prices.length - 2];

  const calculateChange = (current: number | null, previous: number | null) => {
    if (!current || !previous) return undefined;
    return ((current - previous) / previous) * 100;
  };

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-white">Live Market Prices</h3>
          <p className="text-sm text-slate-400 mt-1">Real-time fuel & commodity prices</p>
        </div>
        <div className="flex items-center gap-2">
          <div className={cn(
            "h-2 w-2 rounded-full",
            isConnected ? "bg-green-500 animate-pulse" : "bg-red-500"
          )} />
          <span className="text-xs text-slate-400">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-slate-900">
        {latestPrice && (
          <>
            <PriceItem
              label="Jet Fuel"
              price={latestPrice.jet_fuel_spot}
              change={calculateChange(
                latestPrice.jet_fuel_spot,
                previousPrice?.jet_fuel_spot || null
              )}
            />
            <div className="hidden md:flex">
              <PriceItem
                label="Heating Oil"
                price={latestPrice.heating_oil_futures}
                change={calculateChange(
                  latestPrice.heating_oil_futures,
                  previousPrice?.heating_oil_futures || null
                )}
              />
            </div>
            <div className="hidden md:flex">
              <PriceItem
                label="Brent Crude"
                price={latestPrice.brent_futures}
                change={calculateChange(
                  latestPrice.brent_futures,
                  previousPrice?.brent_futures || null
                )}
              />
            </div>
            <div className="hidden md:flex">
              <PriceItem
                label="WTI Crude"
                price={latestPrice.wti_futures}
                change={calculateChange(
                  latestPrice.wti_futures,
                  previousPrice?.wti_futures || null
                )}
              />
            </div>
            <PriceItem
              label="Crack Spread"
              price={latestPrice.crack_spread}
              change={calculateChange(
                latestPrice.crack_spread,
                previousPrice?.crack_spread || null
              )}
            />
            <PriceItem
              label="Volatility"
              price={latestPrice.volatility_index}
            />
          </>
        )}
      </div>

      {!latestPrice && (
        <div className="text-center py-8 text-slate-500">
          <p>Waiting for market data...</p>
        </div>
      )}
    </div>
  );
}
