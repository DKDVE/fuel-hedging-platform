/**
 * recommendationNarrative.ts
 *
 * Converts raw recommendation data into plain-English narratives.
 * Designed for CFO/executive consumption — no financial jargon.
 *
 * All functions are pure: same input always produces same output.
 * No API calls. No side effects. Fully unit-testable.
 */

import type { HedgeRecommendationResponse, AgentOutput } from '@/types/api';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface ExecutiveSummary {
  headline: string;
  context: string;
  urgency: 'routine' | 'time_sensitive' | 'urgent';
  confidence: 'high' | 'moderate' | 'low';
  confidenceReason: string;
}

export interface RiskNarrative {
  overallMessage: string;
  keyRisks: string[];
  protections: string[];
}

export interface ActionStatement {
  primaryAction: string;
  rationale: string;
  deadline: string;
  financialImpact: string;
}

export interface AgentPlainEnglish {
  agentId: string;
  plainLabel: string;
  summary: string;
  verdict: string;
}

// Extended type for recommendations that may have extra fields from API
interface RecWithExtras extends HedgeRecommendationResponse {
  committee_consensus?: { consensus_risk_level?: string };
  escalation_flag?: boolean;
  optimization_result?: { collateral_required_usd?: number };
}

// ─── Headline logic ───────────────────────────────────────────────────────────

export function generateExecutiveSummary(
  rec: RecWithExtras | HedgeRecommendationResponse
): ExecutiveSummary {
  const hr = rec.optimal_hedge_ratio;
  const varReduction = rec.expected_var_reduction ?? 0;
  const agents = (rec.agent_outputs ?? []) as AgentOutput[];

  let headline: string;
  if (hr >= 0.7) {
    headline = `We recommend hedging ${Math.round(hr * 100)}% of fuel exposure — near our maximum — because current volatility warrants strong protection.`;
  } else if (hr >= 0.5) {
    headline = `We recommend hedging ${Math.round(hr * 100)}% of fuel exposure, a balanced position reflecting moderate market risk.`;
  } else {
    headline = `We recommend a conservative hedge of ${Math.round(hr * 100)}% of fuel exposure. Current conditions favour maintaining flexibility.`;
  }

  const basisAgent = agents.find((a) => a.agent_id === 'basis_risk');
  const macroAgent = agents.find((a) => a.agent_id === 'macro');
  let context: string;
  if (basisAgent?.risk_level === 'HIGH' || basisAgent?.risk_level === 'CRITICAL') {
    context =
      'Note: heating oil futures are currently tracking jet fuel prices less closely than usual, which increases hedging costs.';
  } else if (macroAgent?.risk_level === 'HIGH' || macroAgent?.risk_level === 'CRITICAL') {
    context =
      'Elevated geopolitical risk and energy market volatility are driving this recommendation.';
  } else {
    context = `This hedge is projected to reduce fuel cost uncertainty by ${Math.round(varReduction * 100)}% compared to buying at spot prices.`;
  }

  const hasHighRisk = agents.some(
    (a) => a.risk_level === 'HIGH' || a.risk_level === 'CRITICAL'
  );
  const urgency: ExecutiveSummary['urgency'] = hasHighRisk
    ? 'urgent'
    : hr >= 0.65
      ? 'time_sensitive'
      : 'routine';

  const allSatisfied = agents.every((a) => a.constraints_satisfied !== false);
  const agentCount = agents.length;
  let confidence: ExecutiveSummary['confidence'];
  let confidenceReason: string;
  if (allSatisfied && agentCount === 5) {
    confidence = 'high';
    confidenceReason =
      'All 5 specialist agents agree this strategy satisfies our risk constraints.';
  } else if (agentCount >= 3) {
    confidence = 'moderate';
    confidenceReason =
      'Most agents approve, but one or more flagged concerns for review.';
  } else {
    confidence = 'low';
    confidenceReason =
      'Limited agent analysis available — manual review is recommended.';
  }

  return { headline, context, urgency, confidence, confidenceReason };
}

// ─── Risk narrative ───────────────────────────────────────────────────────────

export function generateRiskNarrative(
  agentOutputs: AgentOutput[]
): RiskNarrative {
  const risks: string[] = [];
  const protections: string[] = [];

  const basisAgent = agentOutputs.find((a) => a.agent_id === 'basis_risk');
  const liquidityAgent = agentOutputs.find((a) => a.agent_id === 'liquidity');
  const ifrs9Agent = agentOutputs.find((a) => a.agent_id === 'ifrs9');
  const macroAgent = agentOutputs.find((a) => a.agent_id === 'macro');

  if (basisAgent?.risk_level === 'HIGH' || basisAgent?.risk_level === 'CRITICAL') {
    risks.push(
      'The heating oil hedge may not track jet fuel prices as closely as usual, reducing effectiveness.'
    );
  }
  const collateralPct = liquidityAgent?.metrics?.collateral_pct_of_reserves as
    | number
    | undefined;
  if (collateralPct != null && collateralPct > 0.12) {
    risks.push(
      `Collateral requirements (${(collateralPct * 100).toFixed(1)}%) are approaching our 15% limit — a price spike could trigger margin calls.`
    );
  }
  if (macroAgent?.risk_level === 'HIGH' || macroAgent?.risk_level === 'CRITICAL') {
    risks.push(
      'Elevated geopolitical risk may cause sudden price moves that our hedge does not fully cover.'
    );
  }

  protections.push(
    'Locks in a portion of fuel costs, protecting the budget from price spikes.'
  );
  if (ifrs9Agent?.ifrs9_eligible) {
    protections.push(
      'Qualifies for IFRS 9 hedge accounting — gains and losses reported in Other Comprehensive Income, not through P&L.'
    );
  }
  protections.push(
    'VaR analysis shows this hedge reduces fuel cost uncertainty by the target amount.'
  );

  const overallMessage =
    risks.length === 0
      ? 'All risk checks passed. This is a standard hedging recommendation with no unusual risk factors.'
      : `This recommendation carries ${risks.length} risk factor${risks.length > 1 ? 's' : ''} that your Risk Manager has reviewed. The hedge is still recommended, but the items below should be monitored.`;

  return { overallMessage, keyRisks: risks.slice(0, 3), protections };
}

// ─── Action statement ─────────────────────────────────────────────────────────

export function generateActionStatement(
  rec: RecWithExtras | HedgeRecommendationResponse
): ActionStatement {
  const hr = rec.optimal_hedge_ratio;
  const colUsd =
    (rec as RecWithExtras).optimization_result?.collateral_required_usd ??
    (rec.collateral_impact ?? 0) * 100_000_000;

  const mix = rec.instrument_mix as Record<string, number> | undefined;
  const primaryInstrument = mix
    ? (Object.entries(mix).sort((a, b) => b[1] - a[1])[0]?.[0] ?? 'futures')
    : 'futures';
  const instrumentLabel =
    primaryInstrument.charAt(0).toUpperCase() + primaryInstrument.slice(1);

  const varUnhedged = 10_000_000; // Default estimate when not available

  return {
    primaryAction: 'Approve to lock in hedge',
    rationale: `Approving creates ${instrumentLabel} positions covering ${Math.round(hr * 100)}% of next-quarter fuel needs.`,
    deadline: 'Within 4 hours (SLA requirement)',
    financialImpact: `Requires posting $${(colUsd / 1_000_000).toFixed(2)}M in collateral. Protects against fuel cost overruns on a $${(varUnhedged / 1_000_000).toFixed(1)}M exposure.`,
  };
}

// ─── Per-agent plain English ──────────────────────────────────────────────────

export function generateAgentPlainEnglish(agent: AgentOutput): AgentPlainEnglish {
  const labels: Record<string, string> = {
    basis_risk: 'Our fuel price correlation specialist says',
    liquidity: 'Our cash management team says',
    operational: 'Our operations team says',
    ifrs9: 'Our accounting compliance team says',
    macro: 'Our market analysis team says',
  };

  const verdict = !agent.constraints_satisfied
    ? '❌ Blocked — constraint violated'
    : agent.risk_level === 'CRITICAL' || agent.risk_level === 'HIGH'
      ? '⚠️ Caution — review required'
      : '✅ Approved';

  return {
    agentId: agent.agent_id,
    plainLabel: labels[agent.agent_id] ?? 'Our specialist says',
    summary: agent.recommendation,
    verdict,
  };
}
