import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { type Permission } from '@/constants/permissions';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredPermission?: Permission;
  requiredRole?: string;
  allowedRoles?: string[];
}

/**
 * ProtectedRoute component with RBAC support.
 * Supports three authorization modes:
 * 1. requiredPermission - checks if user has specific permission
 * 2. requiredRole - checks if user has exact role
 * 3. allowedRoles - checks if user has one of the allowed roles
 */
export function ProtectedRoute({
  children,
  requiredPermission,
  requiredRole,
  allowedRoles,
}: ProtectedRouteProps) {
  const { user, loading, hasPermission, isRole } = useAuth();

  const getBestAllowedRoute = (): string => {
    if (hasPermission('read:analytics')) return '/';
    if (hasPermission('read:positions')) return '/positions';
    if (hasPermission('read:audit')) return '/audit';
    return '/';
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Check permission-based access
  if (requiredPermission && !hasPermission(requiredPermission)) {
    return <Navigate to={getBestAllowedRoute()} replace />;
  }

  // Check role-based access
  if (requiredRole && !isRole(requiredRole) && !isRole('admin')) {
    return <Navigate to={getBestAllowedRoute()} replace />;
  }

  // Check allowed roles
  if (allowedRoles && !allowedRoles.some(role => isRole(role)) && !isRole('admin')) {
    return <Navigate to={getBestAllowedRoute()} replace />;
  }

  return <>{children}</>;
}
