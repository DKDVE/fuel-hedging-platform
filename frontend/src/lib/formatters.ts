/**
 * Safe formatters — every numeric display in the app must use one of these.
 * They guard against null, undefined, NaN, and Infinity before rendering.
 */

const FALLBACK = "—";

export function isSafe(v: unknown): v is number {
  return typeof v === "number" && isFinite(v) && !isNaN(v);
}

/** Format as USD millions: $1.24M */
export function formatMillions(v: number | null | undefined): string {
  if (!isSafe(v)) return FALLBACK;
  return `$${(v / 1_000_000).toFixed(2)}M`;
}

/** Format as USD full: $1,234,500.00 */
export function formatUSD(v: number | null | undefined): string {
  if (!isSafe(v)) return FALLBACK;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(v);
}

/** Format as percentage with N decimals: 68.5% */
export function formatPct(v: number | null | undefined, decimals = 1): string {
  if (!isSafe(v)) return FALLBACK;
  return `${v.toFixed(decimals)}%`;
}

/** Format as a ratio 0–1 as percentage: 0.685 → 68.5% */
export function formatRatio(v: number | null | undefined, decimals = 1): string {
  if (!isSafe(v)) return FALLBACK;
  return `${(v * 100).toFixed(decimals)}%`;
}

/** Format as a plain number with commas: 1,827 */
export function formatInt(v: number | null | undefined): string {
  if (!isSafe(v)) return FALLBACK;
  return new Intl.NumberFormat("en-US").format(Math.round(v));
}

/** Format a price per barrel/gallon: $84.96 */
export function formatPrice(v: number | null | undefined): string {
  if (!isSafe(v)) return FALLBACK;
  return `$${v.toFixed(2)}`;
}

/** Format delta with sign: +2.3% or -1.1% */
export function formatDelta(v: number | null | undefined, decimals = 1): string {
  if (!isSafe(v)) return FALLBACK;
  const sign = v >= 0 ? "+" : "";
  return `${sign}${v.toFixed(decimals)}%`;
}

/** Clamp a ratio 0–1 for progress bars — never feed NaN to a bar width */
export function safeRatio(v: number | null | undefined, max = 1): number {
  if (!isSafe(v)) return 0;
  return Math.min(Math.max(v, 0), max);
}

/** Format benchmark metric value by unit type */
export function formatBenchmarkValue(
  value: number,
  unit: 'pct' | 'usd_per_gallon' | 'ratio' | 'usd'
): string {
  if (!isSafe(value)) return FALLBACK;
  switch (unit) {
    case 'pct':
      return `${value.toFixed(1)}%`;
    case 'usd_per_gallon':
      return `$${value.toFixed(2)}/gal`;
    case 'ratio':
      return value.toFixed(4);
    case 'usd':
      return `$${(value / 1e6).toFixed(2)}M`;
    default:
      return String(value);
  }
}

/** Relative time: "just now", "5m ago", "2h ago", "3d ago" */
export function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

