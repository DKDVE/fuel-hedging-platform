import { useState } from 'react';
import { ChevronDown, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AgentAnalysis {
  agent_id: string;
  risk_level: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  recommendation: string;
  metrics: Record<string, number>;
  constraints_satisfied: boolean;
  ifrs9_eligible: boolean | null;
}

interface AgentDetailsAccordionProps {
  agents: AgentAnalysis[];
}

function AccordionItem({ agent }: { agent: AgentAnalysis }) {
  const [isExpanded, setIsExpanded] = useState(false);

  const getAgentIcon = (agentId: string) => {
    switch (agentId) {
      case 'basis_risk':
        return '📊';
      case 'liquidity':
        return '💧';
      case 'operational':
        return '⚙️';
      case 'ifrs9':
        return '📋';
      case 'macro':
        return '🌍';
      default:
        return '🤖';
    }
  };

  const getAgentLabel = (agentId: string) => {
    return agentId
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const getRiskBadgeColor = (level: string) => {
    switch (level) {
      case 'LOW':
        return 'bg-green-600 text-white';
      case 'MODERATE':
        return 'bg-amber-600 text-white';
      case 'HIGH':
        return 'bg-red-600 text-white';
      case 'CRITICAL':
        return 'bg-red-700 text-white';
      default:
        return 'bg-slate-600 text-white';
    }
  };

  return (
    <div className="border border-slate-800 rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-5 py-4 flex items-center justify-between bg-slate-900 hover:bg-slate-800/80 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-2xl">{getAgentIcon(agent.agent_id)}</span>
          <div className="text-left">
            <h4 className="text-sm font-semibold text-white">
              {getAgentLabel(agent.agent_id)}
            </h4>
            <p className="text-xs text-slate-400 mt-0.5">
              Risk Assessment Agent
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={cn(
            'px-2.5 py-1 rounded-md text-xs font-bold tracking-wide',
            getRiskBadgeColor(agent.risk_level)
          )}>
            {agent.risk_level}
          </span>
          <ChevronDown className={cn(
            'h-5 w-5 text-slate-400 transition-transform',
            isExpanded && 'transform rotate-180'
          )} />
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-5 py-4 bg-slate-900/50 border-t border-slate-800">
          {/* Recommendation */}
          <div className="mb-4">
            <h5 className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-2">
              Recommendation
            </h5>
            <p className="text-sm text-slate-300 leading-relaxed">
              {agent.recommendation}
            </p>
          </div>

          {/* Metrics Table */}
          {Object.keys(agent.metrics).length > 0 && (
            <div className="mb-4">
              <h5 className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-2">
                Key Metrics
              </h5>
              <div className="bg-slate-800/50 rounded-lg overflow-hidden">
                <table className="w-full">
                  <tbody>
                    {Object.entries(agent.metrics).map(([key, value], index) => (
                      <tr key={key} className={cn(
                        index !== Object.keys(agent.metrics).length - 1 && 'border-b border-slate-800'
                      )}>
                        <td className="px-3 py-2 text-xs text-slate-400">
                          {key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                        </td>
                        <td className="px-3 py-2 text-sm font-semibold text-white text-right">
                          {typeof value === 'number' ? value.toFixed(4) : value}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Status Indicators */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              {agent.constraints_satisfied ? (
                <CheckCircle className="h-4 w-4 text-green-500" />
              ) : (
                <XCircle className="h-4 w-4 text-red-500" />
              )}
              <span className="text-xs text-slate-400">
                {agent.constraints_satisfied ? 'Constraints Satisfied' : 'Constraints Failed'}
              </span>
            </div>

            {agent.ifrs9_eligible !== null && (
              <div className="flex items-center gap-2">
                {agent.ifrs9_eligible ? (
                  <CheckCircle className="h-4 w-4 text-primary-500" />
                ) : (
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                )}
                <span className="text-xs text-slate-400">
                  {agent.ifrs9_eligible ? 'IFRS 9 Eligible' : 'IFRS 9 Not Eligible'}
                </span>
              </div>
            )}

            {agent.ifrs9_eligible === null && (
              <span className="text-xs text-slate-500">
                IFRS 9: N/A
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function AgentDetailsAccordion({ agents }: AgentDetailsAccordionProps) {
  if (agents.length === 0) {
    return (
      <div className="card">
        <h3 className="text-lg font-semibold text-white mb-4">Agent Analysis</h3>
        <div className="flex items-center justify-center h-32 text-slate-500">
          <p>No agent analysis data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <h3 className="text-lg font-semibold text-white mb-2">Agent Analysis</h3>
      <p className="text-sm text-slate-400 mb-6">
        Detailed risk assessment from 5 specialized AI agents
      </p>

      <div className="space-y-3">
        {agents.map((agent) => (
          <AccordionItem key={agent.agent_id} agent={agent} />
        ))}
      </div>
    </div>
  );
}
