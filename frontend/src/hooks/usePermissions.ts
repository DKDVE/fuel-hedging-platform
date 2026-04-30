import { useAuth } from '@/contexts/AuthContext';
import { type Permission } from '@/constants/permissions';

/**
 * Hook for checking user permissions and roles.
 * Uses the centralized RBAC system from AuthContext.
 */
export function usePermissions() {
  const { permissions, hasPermission: checkPermission, isRole } = useAuth();

  const hasPermission = (permission: Permission): boolean => {
    return checkPermission(permission);
  };

  const canViewPage = (page: string): boolean => {
    const pagePermissions: Record<string, Permission> = {
      recommendations: 'approve:recommendation',
      analytics: 'read:analytics',
      positions: 'read:positions',
      compliance: 'read:analytics',
      audit: 'read:audit',
      settings: 'edit:config',
    };

    const permission = pagePermissions[page];
    return permission ? hasPermission(permission) : true;
  };

  return {
    hasPermission,
    canViewPage,
    permissions,
    isAdmin: isRole('admin'),
    isCFO: isRole('cfo'),
    isRiskManager: isRole('risk_manager'),
    isAnalyst: isRole('analyst'),
  };
}
