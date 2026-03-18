"use client";

// GhostJobFreshnessIndicator.tsx — Visual freshness indicator for job cards (FE-5.6)
// Colour is never sole indicator — label text always present (UX-8, NFR-A4).
// Keyboard-accessible tooltip via focus/hover handlers (replaces title attribute).

import { useState, useId } from "react";
import { formatDate } from "@repo/ui/lib/locale";
import type { LocaleCode } from "@repo/ui/lib/locale";

export interface GhostJobFreshnessIndicatorProps {
  stalenessScore: number; // days since last activity
  postedAt?: string; // ISO date
  lastVerifiedAt?: string; // ISO date
  locale?: LocaleCode;
}

type FreshnessStatus = "Fresh" | "Ageing" | "Stale";

function getStatus(days: number): FreshnessStatus {
  if (days < 14) return "Fresh";
  if (days <= 30) return "Ageing";
  return "Stale";
}

const STATUS_STYLES: Record<FreshnessStatus, { dot: string; text: string }> = {
  Fresh: { dot: "bg-green-500", text: "text-green-700 dark:text-green-400" },
  Ageing: { dot: "bg-amber-500", text: "text-amber-700 dark:text-amber-400" },
  Stale: { dot: "bg-red-500", text: "text-red-700 dark:text-red-400" },
};

export function GhostJobFreshnessIndicator({
  stalenessScore,
  postedAt,
  lastVerifiedAt,
  locale = "US",
}: GhostJobFreshnessIndicatorProps) {
  const [tooltipVisible, setTooltipVisible] = useState(false);
  const tooltipId = useId();

  const status = getStatus(stalenessScore);
  const styles = STATUS_STYLES[status];

  const tooltipParts: string[] = [];
  if (postedAt) {
    tooltipParts.push(`Posted ${formatDate(postedAt, locale)}`);
  }
  tooltipParts.push(`last verified ${stalenessScore} days ago`);
  const tooltipText = tooltipParts.join(" — ");

  return (
    <span
      aria-label={`Freshness: ${status}`}
      aria-describedby={tooltipText ? tooltipId : undefined}
      title={tooltipText || undefined}
      tabIndex={0}
      className="relative inline-flex items-center gap-1 text-xs font-medium"
      onMouseEnter={() => setTooltipVisible(true)}
      onMouseLeave={() => setTooltipVisible(false)}
      onFocus={() => setTooltipVisible(true)}
      onBlur={() => setTooltipVisible(false)}
    >
      <span
        className={`inline-block h-2 w-2 rounded-full ${styles.dot}`}
        aria-hidden="true"
      />
      <span className={styles.text}>{status}</span>
      {tooltipVisible && tooltipText && (
        <span
          id={tooltipId}
          role="tooltip"
          className="absolute bottom-full left-1/2 z-50 mb-1.5 -translate-x-1/2 whitespace-nowrap rounded bg-popover px-2 py-1 text-xs text-popover-foreground shadow-md border border-border"
        >
          {tooltipText}
        </span>
      )}
    </span>
  );
}
