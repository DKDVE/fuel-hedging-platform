import { Shield, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AgentStatus {
  agent_id: string;
  risk_level: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  recommendation: string;
  constraints_satisfied: boolean;
  ifrs9_eligible: boolean | null;
  generated_at: string;
}

interface AgentStatusGridProps {
  agents: AgentStatus[];
  isLoading?: boolean;
}

function AgentCard({ agent }: { agent: AgentStatus }) {
  const getRiskColor = (level: string) => {
    switch (level) {
      case 'LOW':
        return 'bg-green-600 text-white';
      case 'MODERATE':
        return 'bg-amber-600 text-white';
      case 'HIGH':
        return 'bg-red-600 text-white';
      case 'CRITICAL':
        return 'bg-red-700 text-white animate-pulse';
      default:
        return 'bg-slate-600 text-white';
    }
  };

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

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${Math.floor(diffHours / 24)}d ago`;
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors group">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="text-2xl">{getAgentIcon(agent.agent_id)}</div>
          <div>
            <h4 className="text-sm font-semibold text-white">
              {getAgentLabel(agent.agent_id)}
            </h4>
            <p className="text-xs text-slate-500 mt-0.5">
              Updated {formatTimestamp(agent.generated_at)}
            </p>
          </div>
        </div>
        <div className={cn(
          'px-2.5 py-1 rounded-md text-xs font-bold tracking-wide',
          getRiskColor(agent.risk_level)
        )}>
          {agent.risk_level}
        </div>
      </div>

      {/* Recommendation */}
      <p className="text-sm text-slate-300 mb-4 line-clamp-2 group-hover:line-clamp-none transition-all">
        {agent.recommendation}
      </p>

      {/* Status indicators */}
      <div className="flex items-center gap-4 pt-4 border-t border-slate-800">
        <div className="flex items-center gap-1.5">
          {agent.constraints_satisfied ? (
            <CheckCircle className="h-4 w-4 text-green-500" />
          ) : (
            <XCircle className="h-4 w-4 text-red-500" />
          )}
          <span className="text-xs text-slate-400">
            Constraints
          </span>
        </div>
        {agent.ifrs9_eligible !== null && (
          <div className="flex items-center gap-1.5">
            {agent.ifrs9_eligible ? (
              <CheckCircle className="h-4 w-4 text-primary-500" />
            ) : (
              <AlertTriangle className="h-4 w-4 text-amber-500" />
            )}
            <span className="text-xs text-slate-400">
              IFRS 9
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

export function AgentStatusGrid({ agents, isLoading = false }: AgentStatusGridProps) {
  if (isLoading) {
    return (
      <div className="card">
        <h3 className="text-lg font-semibold text-white mb-4">AI Agent Analysis</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="bg-slate-900 border border-slate-800 rounded-xl p-5 animate-pulse">
              <div className="h-16 bg-slate-800 rounded mb-3" />
              <div className="h-12 bg-slate-800 rounded mb-3" />
              <div className="h-8 bg-slate-800 rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary-500" />
            AI Agent Analysis
          </h3>
          <p className="text-sm text-slate-400 mt-1">
            Real-time risk assessment from 5 specialized agents
          </p>
        </div>
      </div>

      {agents && agents.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent) => (
            <AgentCard key={agent.agent_id} agent={agent} />
          ))}
        </div>
      ) : (
        <div className="text-center py-12 text-slate-500">
          <Shield className="h-12 w-12 mx-auto mb-3 opacity-50" />
          <p>No agent data available</p>
          <p className="text-sm mt-1">Run analytics to generate agent assessments</p>
        </div>
      )}
    </div>
  );
}
