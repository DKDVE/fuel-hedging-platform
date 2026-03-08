import { CheckCircle, XCircle, PauseCircle, Clock } from 'lucide-react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { cn, formatDate } from '@/lib/utils';
import type { ApprovalResponse, DecisionType } from '@/types/api';

interface TimelineAuditTrailProps {
  approvals: ApprovalResponse[];
  createdAt: string;
}

interface TimelineItemProps {
  approval?: ApprovalResponse;
  createdAt?: string;
  isFirst?: boolean;
  isLast?: boolean;
}

function TimelineItem({ approval, createdAt, isFirst: _isFirst, isLast }: TimelineItemProps) {
  const getDecisionIcon = (decision?: DecisionType) => {
    if (!decision) return <Clock className="h-5 w-5" />;
    
    switch (decision) {
      case 'APPROVE':
        return <CheckCircle className="h-5 w-5" />;
      case 'REJECT':
        return <XCircle className="h-5 w-5" />;
      case 'DEFER':
        return <PauseCircle className="h-5 w-5" />;
      default:
        return <Clock className="h-5 w-5" />;
    }
  };

  const getDecisionColor = (decision?: DecisionType) => {
    if (!decision) return 'bg-slate-700 text-slate-400';
    
    switch (decision) {
      case 'APPROVE':
        return 'bg-green-600 text-white';
      case 'REJECT':
        return 'bg-red-600 text-white';
      case 'DEFER':
        return 'bg-amber-600 text-white';
      default:
        return 'bg-slate-700 text-slate-400';
    }
  };

  const getDecisionLabel = (decision?: DecisionType) => {
    if (!decision) return 'Created';
    
    switch (decision) {
      case 'APPROVE':
        return 'Approved';
      case 'REJECT':
        return 'Rejected';
      case 'DEFER':
        return 'Deferred';
      default:
        return decision;
    }
  };

  const getUserInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const calculateResponseTime = (createdAtStr: string, approvalTime: string) => {
    const created = new Date(createdAtStr);
    const approved = new Date(approvalTime);
    const diffMs = approved.getTime() - created.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 60) return `${diffMins} mins`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ${diffMins % 60}m`;
    return `${Math.floor(diffHours / 24)}d ${diffHours % 24}h`;
  };

  // Creation event
  if (!approval && createdAt) {
    return (
      <div className="relative flex gap-4 pb-8">
        {/* Timeline line */}
        {!isLast && (
          <div className="absolute left-5 top-10 bottom-0 w-px bg-slate-800" />
        )}

        {/* Icon */}
        <div className={cn(
          'relative z-10 flex items-center justify-center w-10 h-10 rounded-full',
          'bg-slate-700 text-slate-400'
        )}>
          <Clock className="h-5 w-5" />
        </div>

        {/* Content */}
        <div className="flex-1 pt-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-semibold text-white">
              Recommendation Created
            </span>
          </div>
          <p className="text-xs text-slate-400">
            {formatDate(createdAt)}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            System generated hedge recommendation
          </p>
        </div>
      </div>
    );
  }

  if (!approval) return null;

  return (
    <div className="relative flex gap-4 pb-8">
      {/* Timeline line */}
      {!isLast && (
        <div className="absolute left-5 top-10 bottom-0 w-px bg-slate-800" />
      )}

      {/* Icon */}
      <div className={cn(
        'relative z-10 flex items-center justify-center w-10 h-10 rounded-full',
        getDecisionColor(approval.decision)
      )}>
        {getDecisionIcon(approval.decision)}
      </div>

      {/* Content */}
      <div className="flex-1 pt-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-semibold text-white">
            {getDecisionLabel(approval.decision)}
          </span>
          {createdAt && (
            <span className="text-xs text-slate-500">
              • Responded in {calculateResponseTime(createdAt, approval.created_at)}
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-2 mb-2">
          <Avatar className="h-6 w-6">
            <AvatarFallback className="bg-primary-600 text-white text-xs">
              {getUserInitials('Approver')}
            </AvatarFallback>
          </Avatar>
          <span className="text-xs text-slate-400">
            {approval.approver_id.slice(0, 8)} • CFO
          </span>
        </div>

        <p className="text-xs text-slate-400 mb-2">
          {formatDate(approval.created_at)}
        </p>

        {approval.comments && (
          <div className="mt-2 bg-slate-800/50 rounded-lg p-3 border-l-2 border-primary-600">
            <p className="text-xs text-slate-300">
              {approval.comments}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export function TimelineAuditTrail({ approvals, createdAt }: TimelineAuditTrailProps) {
  const sortedApprovals = [...approvals].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );

  return (
    <div className="card">
      <h3 className="text-lg font-semibold text-white mb-2">Approval Timeline</h3>
      <p className="text-sm text-slate-400 mb-6">
        Complete audit trail of all actions taken on this recommendation
      </p>

      <div className="relative">
        {/* Creation event */}
        <TimelineItem
          createdAt={createdAt}
          isFirst
          isLast={sortedApprovals.length === 0}
        />

        {/* Approval events */}
        {sortedApprovals.map((approval, index) => (
          <TimelineItem
            key={approval.id}
            approval={approval}
            createdAt={createdAt}
            isLast={index === sortedApprovals.length - 1}
          />
        ))}

        {sortedApprovals.length === 0 && (
          <div className="pl-14 text-xs text-slate-500">
            No approval actions yet
          </div>
        )}
      </div>
    </div>
  );
}
