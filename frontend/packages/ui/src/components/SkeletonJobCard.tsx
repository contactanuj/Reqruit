// SkeletonJobCard.tsx — Skeleton placeholder for JobCard (FE-5.1, UX-14)
// Matches real JobCard dimensions to prevent CLS.
// Shimmer animation respects prefers-reduced-motion.

import * as React from "react";

export function SkeletonJobCard() {
  return (
    <div
      aria-hidden="true"
      className={[
        "rounded-lg border border-border bg-card p-4",
        "animate-pulse motion-reduce:animate-none",
      ].join(" ")}
      data-testid="skeleton-job-card"
    >
      {/* Company + freshness indicator row */}
      <div className="flex items-center justify-between mb-2">
        <div className="h-4 w-28 rounded bg-muted" />
        <div className="h-5 w-12 rounded-full bg-muted" />
      </div>

      {/* Role title */}
      <div className="h-5 w-48 rounded bg-muted mb-1" />

      {/* Location */}
      <div className="h-4 w-32 rounded bg-muted mb-3" />

      {/* Fit score + CTC row */}
      <div className="flex items-center gap-2">
        <div className="h-5 w-16 rounded-full bg-muted" />
        <div className="h-4 w-20 rounded bg-muted" />
      </div>
    </div>
  );
}
