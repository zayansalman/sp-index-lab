/* ================================================================
   S&P Index Lab -- Number & Date Formatting Utilities
   Consistent presentation of financial data across the UI.
   ================================================================ */

/* ──────────────────────────────────────────────────────────────
   Percentage Formatter
   formatPercent(0.153)     => "15.3%"
   formatPercent(0.153, 2)  => "15.30%"
   formatPercent(-0.042, 1) => "-4.2%"
   ────────────────────────────────────────────────────────────── */

/**
 * Format a decimal value as a percentage string.
 *
 * @param value     Decimal fraction (e.g., 0.153 for 15.3%)
 * @param decimals  Number of decimal places (default: 1)
 * @returns         Formatted string with "%" suffix, or "--" for invalid input
 */
export function formatPercent(
  value: number | null | undefined,
  decimals: number = 1,
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return "--";
  }
  return `${(value * 100).toFixed(decimals)}%`;
}

/* ──────────────────────────────────────────────────────────────
   Number Formatter (with thousands separator)
   formatNumber(1234.5678)     => "1,234.57"
   formatNumber(1234.5678, 0)  => "1,235"
   ────────────────────────────────────────────────────────────── */

/**
 * Format a number with comma-separated thousands.
 *
 * @param value     Numeric value
 * @param decimals  Number of decimal places (default: 2)
 * @returns         Formatted string, or "--" for invalid input
 */
export function formatNumber(
  value: number | null | undefined,
  decimals: number = 2,
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return "--";
  }
  return value.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/* ──────────────────────────────────────────────────────────────
   Ratio Formatter (no suffix, fixed decimals)
   formatRatio(0.6823)  => "0.68"
   formatRatio(-1.234)  => "-1.23"
   ────────────────────────────────────────────────────────────── */

/**
 * Format a ratio value to 2 decimal places.
 *
 * @param value     Numeric ratio
 * @param decimals  Number of decimal places (default: 2)
 * @returns         Formatted string, or "--" for invalid input
 */
export function formatRatio(
  value: number | null | undefined,
  decimals: number = 2,
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return "--";
  }
  return value.toFixed(decimals);
}

/* ──────────────────────────────────────────────────────────────
   Currency Formatter
   formatCurrency(1.53)     => "$1.53"
   formatCurrency(1234.5)   => "$1,234.50"
   formatCurrency(-42.1)    => "-$42.10"
   ────────────────────────────────────────────────────────────── */

/**
 * Format a number as a USD currency string.
 *
 * @param value     Numeric value
 * @param decimals  Number of decimal places (default: 2)
 * @returns         Formatted string, or "--" for invalid input
 */
export function formatCurrency(
  value: number | null | undefined,
  decimals: number = 2,
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return "--";
  }
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/* ──────────────────────────────────────────────────────────────
   Date Formatter
   formatDate("2026-03-06")  => "Mar 6, 2026"
   formatDate("2014-01-15")  => "Jan 15, 2014"
   ────────────────────────────────────────────────────────────── */

/**
 * Format an ISO date string into a human-readable format.
 *
 * @param dateStr  ISO date string (YYYY-MM-DD) or Date-parseable string
 * @returns        Formatted date, or "--" for invalid input
 */
export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) {
    return "--";
  }

  try {
    // Parse as UTC to avoid timezone offset issues with YYYY-MM-DD strings
    const parts = dateStr.split("-");
    if (parts.length === 3) {
      const date = new Date(
        Date.UTC(
          parseInt(parts[0], 10),
          parseInt(parts[1], 10) - 1,
          parseInt(parts[2], 10),
        ),
      );
      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        timeZone: "UTC",
      });
    }

    // Fallback for other date formats
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) {
      return "--";
    }
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return "--";
  }
}

/* ──────────────────────────────────────────────────────────────
   Compact Number Formatter
   formatCompact(1234)       => "1.2K"
   formatCompact(1234567)    => "1.2M"
   formatCompact(45)         => "45"
   ────────────────────────────────────────────────────────────── */

/**
 * Format large numbers with K/M/B suffixes.
 *
 * @param value     Numeric value
 * @param decimals  Number of decimal places (default: 1)
 * @returns         Compact formatted string, or "--" for invalid input
 */
export function formatCompact(
  value: number | null | undefined,
  decimals: number = 1,
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return "--";
  }

  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";

  if (abs >= 1_000_000_000) {
    return `${sign}${(abs / 1_000_000_000).toFixed(decimals)}B`;
  }
  if (abs >= 1_000_000) {
    return `${sign}${(abs / 1_000_000).toFixed(decimals)}M`;
  }
  if (abs >= 1_000) {
    return `${sign}${(abs / 1_000).toFixed(decimals)}K`;
  }
  return `${sign}${abs.toFixed(decimals === 1 ? 0 : decimals)}`;
}

/* ──────────────────────────────────────────────────────────────
   Signed Value Formatter (with + prefix for positives)
   formatSigned(0.04, formatPercent)   => "+4.0%"
   formatSigned(-0.02, formatPercent)  => "-2.0%"
   ────────────────────────────────────────────────────────────── */

/**
 * Prepend a "+" sign if the value is positive, using a provided formatter.
 *
 * @param value      Numeric value
 * @param formatter  Formatting function to apply
 * @returns          Formatted string with sign prefix
 */
export function formatSigned(
  value: number | null | undefined,
  formatter: (v: number | null | undefined) => string,
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return "--";
  }
  const formatted = formatter(value);
  if (value > 0 && !formatted.startsWith("+")) {
    return `+${formatted}`;
  }
  return formatted;
}

/* ──────────────────────────────────────────────────────────────
   Basis Points Formatter
   formatBps(0.0005)  => "5 bps"
   formatBps(0.0123)  => "123 bps"
   ────────────────────────────────────────────────────────────── */

/**
 * Format a decimal value as basis points.
 *
 * @param value  Decimal fraction (e.g., 0.0005 for 5 bps)
 * @returns      Formatted string with "bps" suffix
 */
export function formatBps(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value)) {
    return "--";
  }
  return `${Math.round(value * 10_000)} bps`;
}
