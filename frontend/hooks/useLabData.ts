/* ================================================================
   S&P Index Lab -- useLabData Hook
   Fetches all JSON data files from /data/ in parallel, transforms
   the snake_case Python output into camelCase TypeScript interfaces,
   and returns a typed, unified data object.
   ================================================================ */

"use client";

import { useState, useEffect, useCallback } from "react";
import type {
  LabData,
  MetaData,
  ConcentrationCurveData,
  ConcentrationPoint,
  VarianceDecompositionPoint,
  PerformanceNavData,
  PerformanceNavPoint,
  AllPerformanceMetrics,
  PerformanceMetrics,
  HoldingsData,
  Holding,
  DrawdownData,
  DrawdownPoint,
  DeviationData,
  DeviationBin,
} from "@/lib/types";

/* ──────────────────────────────────────────────────────────────
   Hook Return Type
   ────────────────────────────────────────────────────────────── */

export interface UseLabDataReturn {
  /** All loaded data (null until first successful load) */
  data: LabData | null;
  /** True while any file is still loading */
  isLoading: boolean;
  /** Error message if any fetch failed */
  error: string | null;
  /** Re-fetch all data */
  refetch: () => void;
}

/* ──────────────────────────────────────────────────────────────
   Data File Manifest
   Maps each data key to its public file path.
   ────────────────────────────────────────────────────────────── */

const DATA_FILES = {
  meta: "/data/meta.json",
  concentrationCurve: "/data/concentration_curve.json",
  varianceDecomposition: "/data/variance_decomposition.json",
  performanceNav: "/data/performance_nav.json",
  performanceMetrics: "/data/performance_metrics.json",
  holdings: "/data/holdings.json",
  drawdown: "/data/drawdowns.json",
  deviation: "/data/daily_deviations.json",
} as const;

type DataKey = keyof typeof DATA_FILES;

/* ──────────────────────────────────────────────────────────────
   Generic fetch helper with error handling
   ────────────────────────────────────────────────────────────── */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function fetchJSON(url: string): Promise<any> {
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch ${url}: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/* ──────────────────────────────────────────────────────────────
   Transform Functions
   Map snake_case Python JSON → camelCase TypeScript interfaces.
   Each function is defensive, using nullish coalescing for
   missing or renamed fields.
   ────────────────────────────────────────────────────────────── */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function transformMeta(raw: any): MetaData {
  return {
    lastUpdated: raw.last_updated ?? "",
    tradingDays: raw.n_trading_days ?? 0,
    startDate: raw.date_range?.start ?? "",
    endDate: raw.date_range?.end ?? "",
    totalStocks: raw.top_50_tickers?.length ?? 50,
    topN: raw.top_20_tickers?.length ?? 20,
    benchmark: "^GSPC",
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function transformConcentrationCurve(raw: any): ConcentrationCurveData {
  const curve: ConcentrationPoint[] = (raw.curve || []).map(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (p: any) => ({
      n: p.n_stocks ?? p.n ?? 0,
      rSquared: p.r_squared ?? p.rSquared ?? 0,
      marginalRSquared: p.marginal_r_squared ?? p.marginalRSquared ?? 0,
      tickers: p.ticker_added ? [p.ticker_added] : p.tickers ?? [],
    }),
  );

  return {
    curve,
    elbowN: 20,
    elbowRSquared: raw.r_squared_at_20 ?? raw.elbowRSquared ?? 0,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function transformVarianceDecomposition(raw: any): VarianceDecompositionPoint[] {
  // JSON has { decomposition: [{ n_stocks, r_squared, adj_r_squared }] }
  // TypeScript expects per-stock variance data. We adapt to a compatible shape.
  const items = raw.decomposition || raw || [];
  if (!Array.isArray(items)) return [];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return items.map((d: any) => ({
    ticker: d.ticker ?? `Top ${d.n_stocks ?? 0}`,
    name: d.name ?? `Top ${d.n_stocks ?? 0} stocks`,
    varianceExplained: d.variance_explained ?? d.r_squared ?? 0,
    cumulativeVariance: d.cumulative_variance ?? d.r_squared ?? 0,
    correlation: d.correlation ?? 0,
    beta: d.beta ?? 0,
    sector: d.sector ?? "",
  }));
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function transformPerformanceNav(raw: any): PerformanceNavData {
  // JSON has { weekly: [...], recent_daily: [...] }
  // Use weekly for the main growth chart (smaller payload, full history)
  const source = raw.weekly || raw.recent_daily || [];

  return source.map(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (p: any): PerformanceNavPoint => ({
      date: p.date ?? "",
      sp500: p.sp500 ?? 0,
      sp20Mirror: p.sp20_mirror ?? p.sp20Mirror ?? 0,
      sp20Equal: p.sp20_equal ?? p.sp20Equal ?? 0,
    }),
  );
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function transformSingleMetrics(m: any): PerformanceMetrics {
  return {
    totalReturn: m.total_return ?? m.totalReturn ?? 0,
    cagr: m.cagr ?? 0,
    annualizedVolatility: m.annualised_volatility ?? m.annualized_volatility ?? m.annualizedVolatility ?? 0,
    sharpe: m.sharpe_ratio ?? m.sharpe ?? 0,
    sortino: m.sortino_ratio ?? m.sortino ?? 0,
    maxDrawdown: m.max_drawdown ?? m.maxDrawdown ?? 0,
    calmar: m.calmar_ratio ?? m.calmar ?? 0,
    beta: m.beta ?? 1.0,
    alpha: m.alpha ?? m.excess_return ?? 0,
    trackingError: m.tracking_error ?? m.trackingError ?? 0,
    informationRatio: m.information_ratio ?? m.informationRatio ?? 0,
    bestDay: m.best_day ?? m.bestDay ?? 0,
    worstDay: m.worst_day ?? m.worstDay ?? 0,
    winRate: m.win_rate ?? m.winRate ?? 0,
    avgDailyReturn: m.avg_daily_return ?? m.avgDailyReturn ?? 0,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function transformPerformanceMetrics(raw: any): AllPerformanceMetrics {
  return {
    sp500: transformSingleMetrics(raw.sp500 || {}),
    sp20Mirror: transformSingleMetrics(raw.sp20_mirror || raw.sp20Mirror || {}),
    sp20Equal: transformSingleMetrics(raw.sp20_equal || raw.sp20Equal || {}),
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function transformHoldings(raw: any): HoldingsData {
  // JSON: { as_of, n_holdings, holdings: [{ ticker, weight, last_price, name?, sector? }] }
  const rawHoldings = raw.holdings || [];
  const nHoldings = rawHoldings.length || 1;

  const mirrorHoldings: Holding[] = rawHoldings.map(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (h: any, i: number) => ({
      ticker: h.ticker ?? "",
      name: h.name ?? h.ticker ?? "",
      weight: h.weight ?? 0,
      sector: h.sector ?? "",
      returnContribution: h.return_contribution ?? h.returnContribution,
      rank: i + 1,
    }),
  );

  // Equal-weighted: same tickers, uniform weight
  const equalHoldings: Holding[] = mirrorHoldings.map((h) => ({
    ...h,
    weight: 1 / nHoldings,
  }));

  return {
    sp20Mirror: mirrorHoldings,
    sp20Equal: equalHoldings,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function transformDrawdown(raw: any): DrawdownData {
  // JSON: { weekly: [{ date, sp500, sp20_mirror, sp20_equal? }], ... }
  const source = raw.weekly || [];

  return source.map(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (p: any): DrawdownPoint => ({
      date: p.date ?? "",
      sp500: p.sp500 ?? 0,
      sp20Mirror: p.sp20_mirror ?? p.sp20Mirror ?? 0,
      sp20Equal: p.sp20_equal ?? p.sp20Equal,
    }),
  );
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function transformDeviation(raw: any): DeviationData {
  // JSON: { bins: [{ bin_start, bin_end, bin_center, count }], stats: { mean, std, ... } }
  const bins: DeviationBin[] = (raw.bins || []).map(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (b: any) => ({
      bin: b.bin_center ?? 0,
      count: b.count ?? 0,
      label: `${(b.bin_center ?? 0) >= 0 ? "+" : ""}${(b.bin_center ?? 0).toFixed(1)}pp`,
    }),
  );

  const stats = raw.stats || {};

  return {
    sp20Mirror: bins,
    sp20Equal: bins, // Same deviation data for both (only mirror computed)
    meanDeviationMirror: stats.mean ?? 0,
    meanDeviationEqual: stats.mean ?? 0,
    stdDeviationMirror: stats.std ?? 0,
    stdDeviationEqual: stats.std ?? 0,
  };
}

/* ──────────────────────────────────────────────────────────────
   useLabData Hook
   ────────────────────────────────────────────────────────────── */

export function useLabData(): UseLabDataReturn {
  const [data, setData] = useState<LabData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadAllData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Fetch all JSON files in parallel (raw, untyped)
      const [
        rawMeta,
        rawConcentration,
        rawVarianceDecomp,
        rawPerformanceNav,
        rawPerformanceMetrics,
        rawHoldings,
        rawDrawdown,
        rawDeviation,
      ] = await Promise.all([
        fetchJSON(DATA_FILES.meta),
        fetchJSON(DATA_FILES.concentrationCurve),
        fetchJSON(DATA_FILES.varianceDecomposition),
        fetchJSON(DATA_FILES.performanceNav),
        fetchJSON(DATA_FILES.performanceMetrics),
        fetchJSON(DATA_FILES.holdings),
        fetchJSON(DATA_FILES.drawdown),
        fetchJSON(DATA_FILES.deviation),
      ]);

      // Transform snake_case JSON → camelCase TypeScript types
      setData({
        meta: transformMeta(rawMeta),
        concentrationCurve: transformConcentrationCurve(rawConcentration),
        varianceDecomposition: transformVarianceDecomposition(rawVarianceDecomp),
        performanceNav: transformPerformanceNav(rawPerformanceNav),
        performanceMetrics: transformPerformanceMetrics(rawPerformanceMetrics),
        holdings: transformHoldings(rawHoldings),
        drawdown: transformDrawdown(rawDrawdown),
        deviation: transformDeviation(rawDeviation),
      });
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "An unknown error occurred while loading data";
      setError(message);
      console.error("[useLabData] Failed to load data:", message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  return {
    data,
    isLoading,
    error,
    refetch: loadAllData,
  };
}

/* ──────────────────────────────────────────────────────────────
   Individual Data Hooks
   For components that only need a single data slice, avoiding
   unnecessary re-renders when other slices change.
   ────────────────────────────────────────────────────────────── */

/**
 * Fetch a single data file and return its typed value.
 * Useful when a component only needs one slice (e.g., just holdings).
 *
 * Note: This returns the RAW (untransformed) JSON. For most uses
 * prefer the main `useLabData()` hook which transforms all data.
 */
export function useLabDataSlice<T>(key: DataKey): {
  data: T | null;
  isLoading: boolean;
  error: string | null;
} {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);

      try {
        const result = await fetchJSON(DATA_FILES[key]);
        if (!cancelled) {
          setData(result as T);
        }
      } catch (err) {
        if (!cancelled) {
          const message =
            err instanceof Error ? err.message : "Failed to load data";
          setError(message);
          console.error(`[useLabDataSlice:${key}]`, message);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [key]);

  return { data, isLoading, error };
}

export default useLabData;
