"use client";

// JobsKanbanView.tsx — Kanban board for saved jobs grouped by status (FE-5.3)

import { SkeletonJobCard } from "@repo/ui/components";
import type { LocaleCode } from "@repo/ui/lib/locale";
import { JobCard } from "./JobCard";
import type { SavedJob, JobStatus } from "../types";

const KANBAN_COLUMNS: { status: JobStatus; label: string }[] = [
  { status: "saved", label: "Saved" },
  { status: "applied", label: "Applied" },
  { status: "phone_screen", label: "Phone Screen" },
  { status: "interview", label: "Interview" },
  { status: "offer", label: "Offer" },
  { status: "rejected", label: "Rejected" },
  { status: "withdrawn", label: "Withdrawn" },
];

interface JobsKanbanViewProps {
  jobs: SavedJob[];
  isPending?: boolean;
  locale?: LocaleCode;
  onJobClick?: (job: SavedJob) => void;
}

export function JobsKanbanView({
  jobs,
  isPending,
  locale = "US",
  onJobClick,
}: JobsKanbanViewProps) {
  if (isPending) {
    return (
      <div className="flex gap-4 overflow-x-auto pb-4" aria-label="Loading kanban board">
        {KANBAN_COLUMNS.map((col) => (
          <div
            key={col.status}
            className="flex-shrink-0 w-64 rounded-lg bg-muted/30 p-3"
          >
            <h3 className="text-sm font-semibold mb-3 text-muted-foreground">{col.label}</h3>
            <SkeletonJobCard />
          </div>
        ))}
      </div>
    );
  }

  const grouped = KANBAN_COLUMNS.reduce<Record<JobStatus, SavedJob[]>>(
    (acc, col) => {
      acc[col.status] = jobs.filter((j) => j.status === col.status);
      return acc;
    },
    {} as Record<JobStatus, SavedJob[]>
  );

  return (
    <div
      className="flex gap-4 overflow-x-auto pb-4"
      aria-label="Saved jobs kanban board"
      data-testid="kanban-board"
    >
      {KANBAN_COLUMNS.map((col) => (
        <div
          key={col.status}
          className="flex-shrink-0 w-64 rounded-lg bg-muted/30 p-3"
          aria-label={`${col.label} column`}
          data-status={col.status}
        >
          <h3 className="text-sm font-semibold mb-3 text-muted-foreground flex items-center justify-between">
            {col.label}
            <span className="ml-2 rounded-full bg-muted px-1.5 py-0.5 text-xs">
              {grouped[col.status].length}
            </span>
          </h3>
          <div className="flex flex-col gap-2">
            {grouped[col.status].map((job) => (
              <JobCard
                key={job.id}
                job={job}
                locale={locale}
                onClick={onJobClick}
              />
            ))}
            {grouped[col.status].length === 0 && (
              <p className="text-xs text-muted-foreground py-4 text-center">No jobs</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
