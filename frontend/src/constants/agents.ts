export const AGENT_DISPLAY_NAMES: Record<
  string,
  { label: string; icon: string; description: string; primaryMetrics: string[] }
> = {
  basis_risk: {
    label: 'Basis Risk Agent',
    icon: '🔗',
    description: 'Analyses proxy correlation and IFRS 9 hedge designation eligibility',
    primaryMetrics: ['r2_heating_oil', 'crack_spread_zscore'],
  },
  liquidity: {
    label: 'Liquidity Agent',
    icon: '💧',
    description: 'Checks collateral requirements and cash flow impact on reserves',
    primaryMetrics: ['collateral_pct', 'cash_reserves_remaining'],
  },
  operational: {
    label: 'Operational Agent',
    icon: '⚙️',
    description: 'Validates all operational constraints and position limits',
    primaryMetrics: ['hedge_ratio', 'counterparty_concentration'],
  },
  ifrs9: {
    label: 'IFRS 9 Agent',
    icon: '📋',
    description: 'Prospective and retrospective hedge effectiveness tests',
    primaryMetrics: ['r2_prospective', 'retrospective_offset_ratio'],
  },
  macro: {
    label: 'Macro Agent',
    icon: '🌐',
    description: 'Macro environment, volatility regime, and premium timing assessment',
    primaryMetrics: ['vol_zscore', 'geopolitical_risk'],
  },
};

export const RISK_LEVEL_STYLES: Record<
  string,
  { bg: string; text: string; border: string }
> = {
  LOW: { bg: 'bg-green-950', text: 'text-green-400', border: 'border-green-600' },
  MODERATE: { bg: 'bg-amber-950', text: 'text-amber-400', border: 'border-amber-500' },
  HIGH: { bg: 'bg-red-950', text: 'text-red-400', border: 'border-red-600' },
  CRITICAL: { bg: 'bg-red-950', text: 'text-red-300', border: 'border-red-500' },
};
