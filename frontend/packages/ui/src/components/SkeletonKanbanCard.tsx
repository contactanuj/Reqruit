// SkeletonKanbanCard.tsx — Skeleton placeholder for KanbanCard (FE-6.1, UX-14)
// Matches KanbanCard dimensions to prevent CLS.
// Shimmer animation respects prefers-reduced-motion.

import * as React from "react";

export function SkeletonKanbanCard() {
  return (
    <div
      aria-hidden="true"
      className={[
        "rounded-lg border border-border bg-card p-3",
        "animate-pulse motion-reduce:animate-none",
      ].join(" ")}
      data-testid="skeleton-kanban-card"
    >
      {/* Company name */}
      <div className="h-3 w-20 rounded bg-muted mb-1" />

      {/* Job title */}
      <div className="h-4 w-36 rounded bg-muted mb-2" />

      {/* Status badge + fit score row */}
      <div className="flex items-center gap-2">
        <div className="h-5 w-16 rounded-full bg-muted" />
        <div className="h-5 w-10 rounded-full bg-muted" />
      </div>
    </div>
  );
}
