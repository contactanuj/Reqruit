"use client";

// MorningBriefingCard — FE-8.1
// Shows new job matches, streak status, and ranked pending actions.

import Link from "next/link";
import { Flame, Clock, Calendar, FileText, Briefcase } from "lucide-react";
import { useMorningBriefing } from "../hooks/useDashboard";
import { SkeletonMorningBriefing } from "./SkeletonMorningBriefing";
import type { PendingAction, ActionUrgency } from "../hooks/useDashboard";

const URGENCY_ICON: Record<ActionUrgency, React.ElementType> = {
  deadline: Clock,
  interview: Calendar,
  document: FileText,
  match: Briefcase,
};

const MAX_ACTIONS = 5;

interface ActionItemProps {
  action: PendingAction;
}

function ActionItem({ action }: ActionItemProps) {
  const Icon = URGENCY_ICON[action.urgency] ?? Briefcase;
  return (
    <li className="flex items-center gap-3 py-1.5">
      <Icon className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
      <span className="flex-1 text-sm">{action.description}</span>
      <Link
        href={action.ctaHref}
        className="shrink-0 rounded-md bg-primary px-3 py-1 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
      >
        {action.ctaLabel}
      </Link>
    </li>
  );
}

export function MorningBriefingCard() {
  const { data, isPending, isError, refetch } = useMorningBriefing();

  if (isPending) {
    return <SkeletonMorningBriefing />;
  }

  if (isError || !data) {
    return (
      <div
        role="region"
        aria-label="Morning briefing"
        className="rounded-xl border border-border bg-card p-6 text-center text-muted-foreground text-sm space-y-2"
      >
        <p>Could not load morning briefing.</p>
        <button
          type="button"
          onClick={() => void refetch()}
          className="text-sm text-primary underline hover:text-primary/80"
          data-testid="briefing-retry-button"
        >
          Try again
        </button>
      </div>
    );
  }

  const visibleActions = data.pendingActions.slice(0, MAX_ACTIONS);
  const hasMore = data.pendingActions.length > MAX_ACTIONS;

  return (
    <section
      role="region"
      aria-label="Morning briefing"
      className="rounded-xl border border-border bg-card p-6 space-y-4"
    >
      <h2 className="text-lg font-semibold">Good morning!</h2>

      {/* New job matches */}
      <div className="flex items-baseline gap-2">
        <span className="text-4xl font-bold tabular-nums">
          {data.newJobMatchCount}
        </span>
        <span className="text-sm text-muted-foreground">
          new jobs since your last visit
        </span>
      </div>

      {/* Streak */}
      <div className="flex items-center gap-2 text-sm">
        <Flame className="h-4 w-4 text-orange-500" aria-hidden="true" />
        <span>
          <span className="font-semibold">{data.streakDays}</span>
          {" day streak"}
        </span>
      </div>

      {/* Pending actions */}
      {visibleActions.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-muted-foreground mb-2">
            Pending actions
          </h3>
          <ul className="divide-y divide-border">
            {visibleActions.map((action) => (
              <ActionItem key={action.id} action={action} />
            ))}
          </ul>
          {hasMore && (
            <Link
              href="/dashboard"
              className="mt-2 block text-xs text-primary hover:underline"
            >
              See all actions
            </Link>
          )}
        </div>
      )}

      {/* IST reset indicator */}
      <p className="text-xs text-muted-foreground text-end">
        Resets at midnight IST
      </p>
    </section>
  );
}
