import React, { createContext, useContext, useState, useEffect } from 'react';
import type { UserResponse } from '@/types/api';
import apiClient, { setAccessToken, setRefreshToken } from '@/lib/api';
import { ROLE_PERMISSIONS, type Permission } from '@/constants/permissions';

interface AuthContextType {
  user: UserResponse | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
  permissions: Set<Permission>;
  hasPermission: (permission: Permission) => boolean;
  isRole: (role: string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // Compute permissions based on user role (api uses uppercase enum, permissions use lowercase)
  const roleKey = user?.role ? (user.role as string).toLowerCase() as keyof typeof ROLE_PERMISSIONS : null;
  const permissions = roleKey && roleKey in ROLE_PERMISSIONS
    ? ROLE_PERMISSIONS[roleKey]
    : new Set<Permission>();

  const hasPermission = (permission: Permission): boolean => {
    return permissions.has(permission);
  };

  const isRole = (role: string): boolean => {
    return user?.role === role;
  };

  // Verify session on mount — cookie may still be valid
  useEffect(() => {
    const initAuth = async () => {
      try {
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
          const { data } = await apiClient.get('/auth/me');
          setUser(data);
        }
      } catch {
        setUser(null);
        localStorage.removeItem('user');
      } finally {
        setLoading(false);
      }
    };
    initAuth();
  }, []);

  const login = async (email: string, password: string) => {
    const response = await apiClient.post<{ user: UserResponse; refresh_token?: string }>('/auth/login', { email, password });
    const { user: userData, refresh_token } = response.data;
    setUser(userData);
    localStorage.setItem('user', JSON.stringify(userData));
    // Cross-origin fallback: store refresh token when cookies are blocked
    if (refresh_token) {
      setRefreshToken(refresh_token);
    }
  };

  const logout = async () => {
    try {
      await apiClient.post('/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setUser(null);
      localStorage.removeItem('user');
      setAccessToken(null);
      setRefreshToken(null);
    }
  };

  const value = {
    user,
    loading,
    login,
    logout,
    isAuthenticated: !!user,
    permissions,
    hasPermission,
    isRole,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
