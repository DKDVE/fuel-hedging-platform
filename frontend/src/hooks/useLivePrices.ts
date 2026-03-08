/**
 * DIAGNOSIS: Root cause of SSE connectivity failure.
 * - Used API_BASE_URL (localhost:8000) — in Docker, frontend container cannot reach api via localhost.
 * - Must use relative URL /api/v1/stream/prices so request goes through Vite proxy to api:8000.
 * - Backend sends event types "history" and "tick" with event.data; also handle onmessage for proxies that strip event type.
 * - Handle both wrapped format { type: 'history', ticks } / { type: 'tick', tick } and raw PriceTick fallback.
 */
import { useState, useEffect, useRef, useCallback } from 'react';

// PriceTick shape from SSE (backend PriceTick.to_dict()) — exported for PriceChart
export interface PriceTickShape {
  time: string;
  jet_fuel_spot: number;
  heating_oil_futures: number;
  brent_futures: number;
  wti_futures: number;
  crack_spread: number;
  volatility_index: number;
  source: 'simulation' | 'eia' | 'massive';
  quality_flag: string | null;
}

type SSEMessage =
  | { type: 'history'; ticks: PriceTickShape[] }
  | { type: 'tick'; tick: PriceTickShape }
  | PriceTickShape;

function isPriceTick(obj: unknown): obj is PriceTickShape {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'jet_fuel_spot' in obj &&
    'time' in obj
  );
}

export function useLivePrices() {
  const [prices, setPrices] = useState<PriceTickShape[]>([]);
  const [latestTick, setLatestTick] = useState<PriceTickShape | null>(null);
  const [connected, setConnected] = useState(false);
  const [dataSource, setDataSource] = useState<'simulation' | 'mixed' | 'disconnected'>('disconnected');
  const esRef = useRef<EventSource | null>(null);
  const attemptsRef = useRef(0);
  const maxAttempts = 5;

  const addTick = useCallback((tick: PriceTickShape) => {
    setLatestTick(tick);
    setDataSource(tick.source === 'simulation' ? 'simulation' : 'mixed');
    setPrices((prev) => {
      const next = [...prev, tick];
      return next.length > 500 ? next.slice(next.length - 500) : next;
    });
  }, []);

  const connect = useCallback(() => {
    esRef.current?.close();

    const es = new EventSource('/api/v1/stream/prices', { withCredentials: true });

    es.onopen = () => {
      setConnected(true);
      setDataSource('simulation');
      attemptsRef.current = 0;
    };

    es.onmessage = (event: MessageEvent) => {
      try {
        const data: unknown = JSON.parse(event.data as string);

        if (!data || (typeof data === 'object' && 'type' in (data as object) && (data as { type: string }).type === 'keepalive')) {
          return;
        }

        if (typeof data === 'object' && data !== null && 'type' in data) {
          const msg = data as SSEMessage;
          if ('type' in msg && msg.type === 'history' && 'ticks' in msg) {
            const historyMsg = msg as { type: 'history'; ticks: PriceTickShape[] };
            setPrices(historyMsg.ticks.slice(-500));
            const last = historyMsg.ticks[historyMsg.ticks.length - 1];
            if (last) {
              setLatestTick(last);
              setDataSource(last.source === 'simulation' ? 'simulation' : 'mixed');
            }
            return;
          }
          if ('type' in msg && msg.type === 'tick' && 'tick' in msg) {
            const tickMsg = msg as { type: 'tick'; tick: PriceTickShape };
            addTick(tickMsg.tick);
            return;
          }
        }

        if (isPriceTick(data)) {
          addTick(data);
        }
      } catch {
        // Malformed JSON — skip silently
      }
    };

    es.addEventListener('history', (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data as string) as { type: 'history'; ticks: PriceTickShape[] };
        const last = data.ticks?.[data.ticks.length - 1];
        if (data.ticks?.length && last) {
          setPrices(data.ticks.slice(-500));
          setLatestTick(last);
          setDataSource(last.source === 'simulation' ? 'simulation' : 'mixed');
        }
      } catch {
        // ignore
      }
    });

    es.addEventListener('tick', (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data as string) as { type: 'tick'; tick: PriceTickShape };
        if (data.tick) addTick(data.tick);
      } catch {
        // ignore
      }
    });

    es.onerror = () => {
      setConnected(false);
      es.close();
      attemptsRef.current += 1;
      if (attemptsRef.current <= maxAttempts) {
        const delay = Math.pow(2, attemptsRef.current - 1) * 1000;
        setTimeout(connect, delay);
      } else {
        setDataSource('disconnected');
      }
    };

    esRef.current = es;
  }, [addTick]);

  useEffect(() => {
    connect();
    return () => {
      esRef.current?.close();
    };
  }, [connect]);

  return {
    prices,
    latestPrice: latestTick,
    latestTick,
    isConnected: connected,
    connected,
    dataSource,
    error: dataSource === 'disconnected' && !connected ? 'Connection failed' : null,
    source: dataSource === 'mixed' ? 'mixed' : dataSource,
  };
}

export type PriceTick = PriceTickShape;
