import { Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/contexts/AuthContext';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { AppShell } from '@/components/layout/Sidebar';
import { ErrorBoundary } from '@/components/layout/ErrorBoundary';
import { PageSkeleton } from '@/components/layout/PageSkeleton';
import { LoginPage } from '@/pages/LoginPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { MarketDataPage } from '@/pages/MarketDataPage';
import { RecommendationsPage } from '@/pages/RecommendationsPage';
import { AnalyticsPage } from '@/pages/AnalyticsPage';
import { PositionsPage } from '@/pages/PositionsPage';
import { AuditLogPage } from '@/pages/AuditLogPage';
import { CompliancePage } from '@/pages/CompliancePage';
import { SettingsPage } from '@/pages/SettingsPage';
import Unauthorized from '@/pages/Unauthorized';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/unauthorized" element={<Unauthorized />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <AppShell>
                    <Suspense fallback={<PageSkeleton />}>
                      <ErrorBoundary page="Dashboard">
                        <DashboardPage />
                      </ErrorBoundary>
                    </Suspense>
                  </AppShell>
                </ProtectedRoute>
              }
            />
            <Route
              path="/market-data"
              element={
                <ProtectedRoute>
                  <AppShell>
                    <Suspense fallback={<PageSkeleton />}>
                      <ErrorBoundary page="MarketData">
                        <MarketDataPage />
                      </ErrorBoundary>
                    </Suspense>
                  </AppShell>
                </ProtectedRoute>
              }
            />
            <Route
              path="/recommendations"
              element={
                <ProtectedRoute requiredPermission="approve:recommendation">
                  <AppShell>
                    <Suspense fallback={<PageSkeleton />}>
                      <ErrorBoundary page="Recommendations">
                        <RecommendationsPage />
                      </ErrorBoundary>
                    </Suspense>
                  </AppShell>
                </ProtectedRoute>
              }
            />
            <Route
              path="/analytics"
              element={
                <ProtectedRoute requiredPermission="read:analytics">
                  <AppShell>
                    <Suspense fallback={<PageSkeleton />}>
                      <ErrorBoundary page="Analytics">
                        <AnalyticsPage />
                      </ErrorBoundary>
                    </Suspense>
                  </AppShell>
                </ProtectedRoute>
              }
            />
            <Route
              path="/compliance"
              element={
                <ProtectedRoute requiredPermission="read:analytics">
                  <AppShell>
                    <Suspense fallback={<PageSkeleton />}>
                      <ErrorBoundary page="Compliance">
                        <CompliancePage />
                      </ErrorBoundary>
                    </Suspense>
                  </AppShell>
                </ProtectedRoute>
              }
            />
            <Route
              path="/positions"
              element={
                <ProtectedRoute requiredPermission="read:positions">
                  <AppShell>
                    <Suspense fallback={<PageSkeleton />}>
                      <ErrorBoundary page="Positions">
                        <PositionsPage />
                      </ErrorBoundary>
                    </Suspense>
                  </AppShell>
                </ProtectedRoute>
              }
            />
            <Route
              path="/audit"
              element={
                <ProtectedRoute requiredPermission="read:audit">
                  <AppShell>
                    <Suspense fallback={<PageSkeleton />}>
                      <ErrorBoundary page="AuditLog">
                        <AuditLogPage />
                      </ErrorBoundary>
                    </Suspense>
                  </AppShell>
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute requiredPermission="edit:config">
                  <AppShell>
                    <Suspense fallback={<PageSkeleton />}>
                      <ErrorBoundary page="Settings">
                        <SettingsPage />
                      </ErrorBoundary>
                    </Suspense>
                  </AppShell>
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
