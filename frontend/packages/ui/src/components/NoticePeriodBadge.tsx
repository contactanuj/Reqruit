// NoticePeriodBadge.tsx — Notice period display for Indian context (FE-5.8)

import * as React from "react";

export interface NoticePeriodBadgeProps {
  /** Notice period in days */
  days: number;
}

function formatNoticePeriod(days: number): string {
  if (days === 0) return "Immediate joiner";
  if (days <= 15) return `${days} days`;
  if (days === 30) return "30 days / 1 month";
  if (days === 45) return "45 days / 1.5 months";
  if (days === 60) return "60 days / 2 months";
  if (days === 90) return "90 days / 3 months";
  const months = Math.round(days / 30);
  return `${days} days / ${months} month${months !== 1 ? "s" : ""}`;
}

export function NoticePeriodBadge({ days }: NoticePeriodBadgeProps) {
  const label = formatNoticePeriod(days);

  return (
    <span
      aria-label={`Notice period: ${label}`}
      className="inline-flex items-center rounded-full border border-border px-2.5 py-0.5 text-xs font-medium"
    >
      {label}
    </span>
  );
}
