import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { AGENT_DISPLAY_NAMES, RISK_LEVEL_STYLES } from '@/constants/agents';

export interface AgentOutput {
  agent_id: string;
  risk_level: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  recommendation: string;
  metrics: Record<string, number | boolean | string | undefined>;
  constraints_satisfied: boolean;
}

interface Props {
  agentOutputs: AgentOutput[];
  consensusRiskLevel?: string;
  approvedForPresentation?: boolean;
}

function AgentCard({ agent }: { agent: AgentOutput }) {
  const [expanded, setExpanded] = useState(false);
  const meta = AGENT_DISPLAY_NAMES[agent.agent_id] ?? {
    label: agent.agent_id,
    icon: '🤖',
    description: '',
    primaryMetrics: [],
  };
  const styles = RISK_LEVEL_STYLES[agent.risk_level] ?? RISK_LEVEL_STYLES.MODERATE ?? {
    bg: 'bg-amber-950',
    text: 'text-amber-400',
    border: 'border-amber-500',
  };

  return (
    <div
      className={`rounded-lg border-l-4 ${styles.border} bg-gray-900 overflow-hidden`}
    >
      <button
        className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-800/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <span className="text-xl">{meta.icon}</span>
          <div>
            <p className="font-medium text-white text-sm">{meta.label}</p>
            <p className="text-xs text-gray-400">{meta.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`text-xs font-bold px-2 py-1 rounded ${styles.bg} ${styles.text} border ${styles.border}`}
          >
            {agent.risk_level}
          </span>
          <span
            className={`text-xs font-medium ${
              agent.constraints_satisfied ? 'text-green-400' : 'text-red-400'
            }`}
          >
            {agent.constraints_satisfied ? '✅ Approved' : '❌ Blocked'}
          </span>
          {expanded ? (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-400" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-800">
          {Object.keys(agent.metrics).length > 0 && (
            <div className="mt-3 grid grid-cols-2 gap-2">
              {Object.entries(agent.metrics).map(([key, value]) => (
                <div key={key} className="bg-gray-800 rounded p-2">
                  <p className="text-[10px] text-gray-500 uppercase tracking-wide">
                    {key.replace(/_/g, ' ')}
                  </p>
                  <p className="text-sm font-mono text-white mt-0.5">
                    {typeof value === 'boolean'
                      ? value
                        ? '✅ Yes'
                        : '❌ No'
                      : typeof value === 'number'
                        ? Math.abs(value) < 10
                          ? value.toFixed(4)
                          : value.toFixed(2)
                        : String(value)}
                  </p>
                </div>
              ))}
            </div>
          )}

          <div className="mt-3 p-3 bg-gray-800/50 rounded border border-gray-700">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Assessment</p>
            <p className="text-sm text-gray-300 leading-relaxed italic">
              &quot;{agent.recommendation}&quot;
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export function ExplainabilityPanel({
  agentOutputs,
  consensusRiskLevel,
  approvedForPresentation,
}: Props) {
  if (!agentOutputs || agentOutputs.length === 0) {
    return (
      <div className="mt-6 p-6 bg-gray-900 rounded-xl border border-gray-700 text-center">
        <p className="text-gray-500 text-sm">
          No agent analysis available for this recommendation.
        </p>
        <p className="text-gray-600 text-xs mt-1">
          Agent outputs are generated when the pipeline triggers the n8n workflow.
        </p>
      </div>
    );
  }

  const approveCount = agentOutputs.filter((a) => a.constraints_satisfied).length;
  const cautionCount = agentOutputs.length - approveCount;

  return (
    <div className="mt-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="flex-1 h-px bg-gray-700" />
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider whitespace-nowrap">
          How This Recommendation Was Reached
        </h3>
        <div className="flex-1 h-px bg-gray-700" />
      </div>

      <p className="text-xs text-gray-500 mb-4 text-center">
        5 specialised AI agents analysed this strategy independently. Expand each for full
        reasoning.
      </p>

      <div className="space-y-3">
        {agentOutputs.map((agent) => (
          <AgentCard key={agent.agent_id} agent={agent} />
        ))}
      </div>

      <div className="mt-4 p-4 bg-gray-900 rounded-xl border border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Committee Vote</p>
            <p className="text-sm text-white">
              <span className="text-green-400 font-bold">{approveCount} Approve</span>
              {cautionCount > 0 && (
                <>
                  {' '}
                  / <span className="text-amber-400 font-bold">{cautionCount} Caution</span>
                </>
              )}
              {' → '}
              <span className="font-semibold">
                Consensus: {consensusRiskLevel ?? 'MODERATE'} RISK
              </span>
            </p>
          </div>
          <div
            className={`px-3 py-2 rounded-lg border text-sm font-medium ${
              approvedForPresentation
                ? 'border-green-600 bg-green-950 text-green-300'
                : 'border-red-600 bg-red-950 text-red-300'
            }`}
          >
            {approvedForPresentation
              ? '✅ CRO Gate: Approved for Review'
              : '❌ CRO Gate: Blocked'}
          </div>
        </div>
      </div>
    </div>
  );
}
