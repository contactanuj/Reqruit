"use client";

// SprintTracker — FE-14.2
// Shows active sprint goals with progress bars, and triggers AI retrospective
// generation when a sprint has ended without one.

import { useEffect, useRef } from "react";
import DOMPurify from "dompurify";
import { useSprintsQuery } from "../hooks/useSprints";
import { useGenerateRetrospective } from "../hooks/useSprints";
import { formatDate } from "@repo/ui/lib/locale";
import { useLocale } from "@repo/ui/hooks";
import type { Sprint, SprintGoal } from "../types";

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function GoalProgressBar({ goal }: { goal: SprintGoal }) {
  const percentage = Math.min(
    Math.round((goal.currentCount / goal.targetCount) * 100),
    100,
  );

  return (
    <div data-testid={`sprint-goal-${goal.id}`} className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{goal.description}</span>
        <span className="tabular-nums text-muted-foreground">
          {goal.currentCount}/{goal.targetCount} ({percentage}%)
        </span>
      </div>
      <div
        data-testid={`goal-progress-${goal.id}`}
        className="h-2.5 w-full overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-valuenow={goal.currentCount}
        aria-valuemin={0}
        aria-valuemax={goal.targetCount}
        aria-label={`${goal.description}: ${percentage}% complete`}
      >
        <div
          className={`h-full rounded-full transition-all duration-300 ${
            percentage >= 100
              ? "bg-emerald-500"
              : percentage >= 50
                ? "bg-primary"
                : "bg-amber-500"
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

function RetrospectiveCard({ retrospective }: { retrospective: string }) {
  const sanitized = DOMPurify.sanitize(retrospective);

  return (
    <div
      data-testid="retrospective-card"
      className="rounded-lg border bg-muted/30 p-4 space-y-2"
    >
      <h4 className="text-sm font-semibold">AI Retrospective</h4>
      <div
        className="prose prose-sm dark:prose-invert max-w-none text-sm text-muted-foreground"
        dangerouslySetInnerHTML={{ __html: sanitized }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// SprintTrackerInner — renders a single sprint
// ---------------------------------------------------------------------------

function SprintTrackerInner({ sprint }: { sprint: Sprint }) {
  const locale = useLocale();
  const generateRetro = useGenerateRetrospective(sprint.id);
  const retriedRef = useRef(false);
  const mountedRef = useRef(false);

  // Auto-trigger retrospective generation for completed sprints without one.
  // Guard against React StrictMode double-mount by tracking mount state.
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (
      mountedRef.current &&
      sprint.status === "completed" &&
      !sprint.retrospective &&
      !retriedRef.current &&
      !generateRetro.isPending
    ) {
      retriedRef.current = true;
      generateRetro.mutate();
    }
  }, [sprint.status, sprint.retrospective, generateRetro]);

  const startDate = formatDate(sprint.startDate, locale);
  const endDate = formatDate(sprint.endDate, locale);

  return (
    <div data-testid="sprint-tracker" className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">
          {sprint.status === "active" ? "Active Sprint" : "Completed Sprint"}
        </h3>
        <span className="text-xs text-muted-foreground">
          {startDate} — {endDate}
        </span>
      </div>

      <div className="space-y-3">
        {sprint.goals.map((goal) => (
          <GoalProgressBar key={goal.id} goal={goal} />
        ))}
      </div>

      {sprint.retrospective && (
        <RetrospectiveCard retrospective={sprint.retrospective} />
      )}

      {sprint.status === "completed" &&
        !sprint.retrospective &&
        generateRetro.isPending && (
          <div
            data-testid="loading-state"
            className="flex items-center gap-2 text-sm text-muted-foreground"
            role="status"
          >
            <span className="animate-pulse">Generating retrospective…</span>
          </div>
        )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function SprintTracker() {
  const { data: sprints, isLoading } = useSprintsQuery();

  if (isLoading) {
    return (
      <div
        data-testid="loading-state"
        className="flex items-center justify-center py-12 text-muted-foreground"
        role="status"
        aria-label="Loading sprint data"
      >
        <span className="animate-pulse">Loading sprint data…</span>
      </div>
    );
  }

  // Find the most relevant sprint: active first, then most recent completed
  const activeSprint = sprints?.find((s) => s.status === "active");
  const completedSprint = sprints
    ?.filter((s) => s.status === "completed")
    .sort(
      (a, b) =>
        new Date(b.endDate).getTime() - new Date(a.endDate).getTime(),
    )[0];

  const sprint = activeSprint ?? completedSprint;

  if (!sprint) {
    return (
      <div
        data-testid="no-sprint-state"
        className="flex flex-col items-center justify-center py-12 text-muted-foreground"
      >
        <p>No active sprint. Create one to start tracking your goals!</p>
      </div>
    );
  }

  return <SprintTrackerInner sprint={sprint} />;
}
