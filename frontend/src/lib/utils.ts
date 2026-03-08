import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Utility functions for formatting
export function formatCurrency(value: number, decimals?: number): string {
  const d = decimals ?? 2;
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: d,
    maximumFractionDigits: d,
  }).format(value);
}

export function formatPercentage(value: number | unknown): string {
  const n = Number(value);
  return Number.isNaN(n) ? 'N/A' : `${n.toFixed(2)}%`;
}

/** Safely format a number for display; handles null/undefined/string. */
export function safeNumber(value: unknown, decimals: number, fallback = 'N/A'): string {
  const n = Number(value);
  return Number.isNaN(n) ? fallback : n.toFixed(decimals);
}

export function formatDate(dateString: string, _format?: 'short' | 'long'): string {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'UTC',
  }).format(date) + ' UTC';
}

export function getRiskLevelColor(level: string): string {
  switch (level.toUpperCase()) {
    case 'LOW':
      return 'text-green-500';
    case 'MODERATE':
      return 'text-amber-500';
    case 'HIGH':
      return 'text-red-500';
    case 'CRITICAL':
      return 'text-red-600';
    default:
      return 'text-gray-500';
  }
}

export function getStatusColor(status: string): string {
  switch (status.toUpperCase()) {
    case 'APPROVED':
      return 'bg-green-100 text-green-800';
    case 'PENDING_APPROVAL':
      return 'bg-amber-100 text-amber-800';
    case 'REJECTED':
      return 'bg-red-100 text-red-800';
    case 'DEFERRED':
      return 'bg-gray-100 text-gray-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}
