"use client";

// NudgeCardList — FE-8.5
// Shows up to 3 nudge cards (pre-ranked by backend) with "See all" link.

import Link from "next/link";
import { NudgeCard } from "./NudgeCard";
import { useNudges, useDismissNudge } from "../hooks/useDashboard";

const MAX_NUDGES = 3;

export function NudgeCardList() {
  const { data: nudges, isPending } = useNudges();
  const dismissMutation = useDismissNudge();

  if (isPending) {
    return (
      <div className="space-y-2">
        {[1, 2].map((i) => (
          <div
            key={i}
            className="h-20 rounded-lg bg-muted animate-pulse motion-reduce:animate-none"
          />
        ))}
      </div>
    );
  }

  if (!nudges || nudges.length === 0) {
    return null;
  }

  const visibleNudges = nudges.slice(0, MAX_NUDGES);
  const hasMore = nudges.length > MAX_NUDGES;

  return (
    <div className="space-y-2">
      {visibleNudges.map((nudge) => (
        <NudgeCard
          key={nudge.id}
          nudge={nudge}
          onDismiss={(id) => dismissMutation.mutate(id)}
          isDismissing={dismissMutation.isPending && dismissMutation.variables === nudge.id}
        />
      ))}
      {hasMore && (
        <Link
          href="/dashboard"
          className="block text-center text-sm text-primary hover:underline py-1"
        >
          See all nudges
        </Link>
      )}
    </div>
  );
}
