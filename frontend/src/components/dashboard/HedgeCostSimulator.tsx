import { formatInt, formatMillions, formatPrice } from '@/lib/formatters';

interface HedgeCostSimulatorProps {
  currentPrice: number;
  consumption: number;
  hedgeRatioPct: number;
  selectedInstruments: Set<string>;
}

export function HedgeCostSimulator({
  currentPrice,
  consumption,
  hedgeRatioPct,
  selectedInstruments,
}: HedgeCostSimulatorProps) {
  const hedgedBbl = Math.round((consumption * hedgeRatioPct) / 100);
  const unhedgedBbl = consumption - hedgedBbl;
  const hedgedCost = currentPrice * 42 * hedgedBbl;
  const unhedgedCost = currentPrice * 42 * unhedgedBbl;
  const totalEst = hedgedCost + unhedgedCost;

  const futuresCollateral = Math.round(currentPrice * 42 * hedgedBbl * 0.02);
  const optionsStrike = Math.round(currentPrice * 1.05 * 100) / 100;
  const optionsPremiumPerBbl = currentPrice * 0.037;
  const optionsPremiumMonthly = optionsPremiumPerBbl * hedgedBbl;
  const collarCap = currentPrice * 1.08;
  const collarFloor = currentPrice * 0.92;
  const swapsFixedRate = currentPrice;

  return (
    <div className="card">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-white uppercase tracking-wide">
          Hedge Cost Simulator
        </h3>
        <p className="text-xs text-slate-500 mt-0.5">
          What each instrument costs your operation this month
        </p>
      </div>

      <div className="space-y-3">
        {selectedInstruments.has('futures') && (
          <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-3">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-2 text-sm">
              <p className="text-white font-semibold">Futures</p>
              <p className="text-slate-300">Lock-in price: {formatPrice(currentPrice)}/bbl</p>
              <p className="text-slate-300">Collateral est.: {formatMillions(futuresCollateral)}</p>
              <p className="text-green-400">✓ Price certainty</p>
            </div>
            <p className="text-xs text-slate-500 mt-2">
              You pay {formatPrice(currentPrice)}/bbl regardless of market movement.
            </p>
          </div>
        )}

        {selectedInstruments.has('options') && (
          <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-3">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-2 text-sm">
              <p className="text-white font-semibold">Call Options</p>
              <p className="text-slate-300">Strike cap: {formatPrice(optionsStrike)}/bbl</p>
              <p className="text-slate-300">Premium est.: {formatPrice(optionsPremiumPerBbl)}/bbl</p>
              <p className="text-slate-300">Monthly premium: {formatMillions(optionsPremiumMonthly)}</p>
            </div>
            <p className="text-xs text-slate-500 mt-2">
              Costs {formatPrice(optionsPremiumPerBbl)}/bbl upfront. Max you pay is {formatPrice(optionsStrike)}
              /bbl. Profit if price falls.
            </p>
          </div>
        )}

        {selectedInstruments.has('collars') && (
          <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-3">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-2 text-sm">
              <p className="text-white font-semibold">Collar</p>
              <p className="text-slate-300">Cap: {formatPrice(collarCap)}/bbl</p>
              <p className="text-slate-300">Floor: {formatPrice(collarFloor)}/bbl</p>
              <p className="text-slate-300">Net premium: ~$0 (zero-cost)</p>
            </div>
            <p className="text-xs text-slate-500 mt-2">
              Protects above {formatPrice(collarCap)}/bbl. You give up gains below {formatPrice(collarFloor)}/bbl.
            </p>
          </div>
        )}

        {selectedInstruments.has('swaps') && (
          <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-3">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-2 text-sm">
              <p className="text-white font-semibold">Swaps</p>
              <p className="text-slate-300">Fixed rate: {formatPrice(swapsFixedRate)}/bbl</p>
              <p className="text-slate-300">No collateral</p>
              <p className="text-slate-300">Monthly settlement</p>
            </div>
            <p className="text-xs text-slate-500 mt-2">
              No upfront cost. Locked to {formatPrice(swapsFixedRate)}/bbl monthly avg. Risk if price falls.
            </p>
          </div>
        )}
      </div>

      <div className="mt-4 rounded-xl border border-blue-800/40 bg-blue-950/20 p-4">
        <p className="text-xs text-blue-400 uppercase tracking-wide mb-3">Total Monthly Exposure</p>
        <div className="space-y-1 text-sm">
          <p className="text-slate-300">
            Hedged portion ({formatInt(hedgedBbl)} bbl @ ~{formatPrice(currentPrice)}/bbl):{' '}
            <span className="font-mono text-white">{formatMillions(hedgedCost)}</span>
          </p>
          <p className="text-slate-300">
            Unhedged portion ({formatInt(unhedgedBbl)} bbl @ market price):{' '}
            <span className="font-mono text-white">{formatMillions(unhedgedCost)} (varies)</span>
          </p>
          <p className="text-slate-100 font-semibold pt-1 border-t border-slate-700">
            Total monthly fuel cost estimate:{' '}
            <span className="font-mono">{formatMillions(totalEst)}</span>
          </p>
        </div>
      </div>

      <p className="text-xs text-slate-500 mt-3">
        Estimates only. Option premiums are indicative at ~3.7% of notional. Collateral rates are approximate
        (2% of futures notional). Actual rates depend on counterparty and market conditions.
      </p>
    </div>
  );
}
