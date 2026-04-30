import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Lightbulb,
  BarChart3,
  Briefcase,
  ShieldCheck,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { usePermissions } from '@/hooks/usePermissions';

const primaryItems: { path: string; label: string; icon: typeof LayoutDashboard; permission?: string }[] = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/recommendations', label: 'Recs', icon: Lightbulb, permission: 'recommendations' },
  { path: '/analytics', label: 'Analytics', icon: BarChart3 },
  { path: '/positions', label: 'Positions', icon: Briefcase },
  { path: '/compliance', label: 'Comply', icon: ShieldCheck },
];

export function MobileBottomNav() {
  const location = useLocation();
  const { canViewPage } = usePermissions();
  const visibleItems = primaryItems.filter((item) => !item.permission || canViewPage(item.permission));

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-slate-900 border-t border-slate-700 flex md:hidden">
      {visibleItems.map((item) => {
        const isActive =
          location.pathname === item.path ||
          (item.path !== '/' && location.pathname.startsWith(item.path));
        return (
          <Link
            key={item.path}
            to={item.path}
            className={cn(
              'flex-1 flex flex-col items-center justify-center py-2 gap-0.5 transition-colors',
              isActive ? 'text-primary-400' : 'text-slate-500 hover:text-slate-300'
            )}
          >
            <item.icon className="w-5 h-5" />
            <span className="text-[10px] font-medium">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
