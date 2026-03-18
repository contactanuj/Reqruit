"use client";

// SkeletonMorningBriefing — Shape-accurate loading skeleton for MorningBriefingCard (FE-8.1)

export function SkeletonMorningBriefing() {
  return (
    <div
      aria-busy="true"
      aria-label="Loading morning briefing"
      className="rounded-xl border border-border bg-card p-6 space-y-4 animate-pulse motion-reduce:animate-none"
    >
      {/* Header */}
      <div className="h-6 w-48 rounded bg-muted" />
      {/* Job matches */}
      <div className="flex items-center gap-3">
        <div className="h-10 w-16 rounded bg-muted" />
        <div className="h-4 w-40 rounded bg-muted" />
      </div>
      {/* Streak */}
      <div className="h-4 w-32 rounded bg-muted" />
      {/* Action items */}
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="h-4 w-4 rounded bg-muted" />
            <div className="h-4 flex-1 rounded bg-muted" />
            <div className="h-8 w-24 rounded bg-muted" />
          </div>
        ))}
      </div>
    </div>
  );
}
