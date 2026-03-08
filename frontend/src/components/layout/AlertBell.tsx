import { useState } from 'react';
import { Bell } from 'lucide-react';
import { useAlerts } from '@/hooks/useAlerts';
import { timeAgo } from '@/lib/formatters';

export function AlertBell() {
  const { alerts, unreadCount, acknowledge } = useAlerts();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-lg hover:bg-gray-100 transition-colors"
        aria-label={`${unreadCount} unread alerts`}
      >
        <Bell className="w-5 h-5 text-gray-600" />
        {unreadCount > 0 && (
          <span
            className="absolute top-1 right-1 w-4 h-4 bg-red-500 rounded-full text-[10px] text-white flex items-center justify-center font-bold animate-pulse"
          >
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Alert panel */}
      {isOpen && (
        <div
          className="absolute right-0 top-10 w-80 max-h-96 overflow-y-auto bg-gray-900 border border-gray-700 rounded-xl shadow-2xl z-50"
          style={{ minWidth: '320px' }}
        >
          <div className="flex justify-between items-center p-3 border-b border-gray-700">
            <span className="font-semibold text-sm text-white">Alerts</span>
            <button
              onClick={() => setIsOpen(false)}
              className="text-gray-400 hover:text-white"
            >
              ✕
            </button>
          </div>

          {alerts.length === 0 ? (
            <div className="p-6 text-center text-gray-500 text-sm">No active alerts</div>
          ) : (
            <div className="divide-y divide-gray-800">
              {alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`p-3 border-l-4 ${
                    alert.severity === 'CRITICAL'
                      ? 'border-red-500 bg-red-950/30'
                      : alert.severity === 'WARNING'
                        ? 'border-amber-500 bg-amber-950/30'
                        : 'border-blue-500 bg-blue-950/30'
                  }`}
                >
                  <div className="flex justify-between items-start gap-2">
                    <p className="font-medium text-xs text-white leading-tight">
                      {alert.title}
                    </p>
                    <span
                      className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        alert.severity === 'CRITICAL'
                          ? 'bg-red-500 text-white'
                          : alert.severity === 'WARNING'
                            ? 'bg-amber-500 text-black'
                            : 'bg-blue-500 text-white'
                      }`}
                    >
                      {alert.severity}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mt-1 leading-snug">{alert.message}</p>
                  <div className="flex justify-between items-center mt-2">
                    <span className="text-[10px] text-gray-500">
                      {timeAgo(alert.created_at)}
                    </span>
                    {!alert.is_acknowledged && (
                      <button
                        onClick={() => acknowledge(alert.id)}
                        className="text-[10px] text-blue-400 hover:text-blue-300"
                      >
                        Acknowledge
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
