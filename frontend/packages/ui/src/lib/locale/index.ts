export type LocaleCode = "IN" | "US";

/**
 * Format an annual salary amount for display.
 * IN: ₹12L, ₹1.2Cr | US: $180K, $1.2M
 * Rule 2: All currency formatting MUST use these functions — no inline formatting.
 */
export function formatLPA(amount: number, locale: LocaleCode): string {
  if (locale === "IN") {
    if (amount >= 10_000_000) {
      return `₹${(amount / 10_000_000).toFixed(1).replace(/\.0$/, "")}Cr`;
    }
    const lakhs = amount / 100_000;
    return `₹${lakhs % 1 === 0 ? lakhs.toFixed(0) : lakhs.toFixed(1)}L`;
  }
  // US locale
  if (amount >= 1_000_000) {
    return `$${(amount / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  }
  return `$${Math.round(amount / 1000)}K`;
}

/**
 * Format CTC (Cost to Company) — annual package.
 * IN: ₹25L p.a. | US: $180K/yr
 */
export function formatCTC(amount: number, locale: LocaleCode): string {
  if (locale === "IN") {
    if (amount >= 10_000_000) {
      return `₹${(amount / 10_000_000).toFixed(1).replace(/\.0$/, "")}Cr p.a.`;
    }
    const lakhs = amount / 100_000;
    return `₹${lakhs % 1 === 0 ? lakhs.toFixed(0) : lakhs.toFixed(1)}L p.a.`;
  }
  // US locale
  if (amount >= 1_000_000) {
    return `$${(amount / 1_000_000).toFixed(1).replace(/\.0$/, "")}M/yr`;
  }
  return `$${Math.round(amount / 1000)}K/yr`;
}

/**
 * Format a date for display.
 * IN: DD/MM/YYYY | US: MM/DD/YYYY
 * Always store raw ISO dates in cache — format at render using this function (Rule 10).
 */
export function formatDate(date: Date | string, locale: LocaleCode): string {
  // Parse date-only ISO strings (e.g. "2024-03-15") manually to avoid
  // timezone shifting — new Date("2024-03-15") is UTC midnight which shows
  // as the previous day in negative-offset timezones (US).
  let d: Date;
  if (typeof date === "string") {
    const dateStr = date.split("T")[0];
    const [y, m, day_] = dateStr.split("-").map(Number);
    d = new Date(y, m - 1, day_);
  } else {
    d = date;
  }
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const year = d.getFullYear();

  if (locale === "IN") {
    return `${day}/${month}/${year}`;
  }
  return `${month}/${day}/${year}`;
}

/**
 * Format a number using Indian numbering system (lakhs/crores) or Western (millions/billions).
 */
export function formatNumber(value: number, locale: LocaleCode): string {
  if (locale === "IN") {
    return new Intl.NumberFormat("en-IN").format(value);
  }
  return new Intl.NumberFormat("en-US").format(value);
}
