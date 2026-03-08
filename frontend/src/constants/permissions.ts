/**
 * Role-Based Access Control (RBAC) Permissions
 * 
 * Mirrors the backend ROLE_PERMISSIONS mapping.
 * This is the single source of truth for frontend permission checks.
 */

export type Permission = 
  | 'read:analytics'
  | 'read:positions'
  | 'read:audit'
  | 'approve:recommendation'
  | 'escalate:recommendation'
  | 'edit:config'
  | 'manage:users'
  | 'trigger:pipeline'
  | 'export:data';

export type UserRole = 'analyst' | 'risk_manager' | 'cfo' | 'admin';

export const ROLE_PERMISSIONS: Record<UserRole, Set<Permission>> = {
  analyst: new Set([
    'read:analytics',
    'read:positions',
  ]),
  
  risk_manager: new Set([
    'read:analytics',
    'read:positions',
    'read:audit',
    'approve:recommendation',
    'export:data',
  ]),
  
  cfo: new Set([
    'read:analytics',
    'read:positions',
    'read:audit',
    'approve:recommendation',
    'escalate:recommendation',
    'export:data',
  ]),
  
  admin: new Set([
    'read:analytics',
    'read:positions',
    'read:audit',
    'approve:recommendation',
    'escalate:recommendation',
    'edit:config',
    'manage:users',
    'trigger:pipeline',
    'export:data',
  ]),
};

export const ROLE_LABELS: Record<UserRole, string> = {
  analyst: 'Analyst',
  risk_manager: 'Risk Manager',
  cfo: 'CFO',
  admin: 'Administrator',
};

/**
 * Get all permissions for a given role
 */
export function getRolePermissions(role: UserRole): Set<Permission> {
  return ROLE_PERMISSIONS[role] || new Set();
}

/**
 * Check if a role has a specific permission
 */
export function hasPermission(role: UserRole, permission: Permission): boolean {
  const permissions = getRolePermissions(role);
  return permissions.has(permission);
}

/**
 * Check if a role has ANY of the specified permissions
 */
export function hasAnyPermission(role: UserRole, permissions: Permission[]): boolean {
  const rolePermissions = getRolePermissions(role);
  return permissions.some(p => rolePermissions.has(p));
}

/**
 * Check if a role has ALL of the specified permissions
 */
export function hasAllPermissions(role: UserRole, permissions: Permission[]): boolean {
  const rolePermissions = getRolePermissions(role);
  return permissions.every(p => rolePermissions.has(p));
}

/**
 * Get human-readable label for a role
 */
export function getRoleLabel(role: UserRole): string {
  return ROLE_LABELS[role] || role;
}
