"use client";

// Jobs page — Discover + Saved tabs (FE-5.1, FE-5.3)
// N shortcut opens Add Job dialog (FE-5.2)

import { useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useKeyboardShortcuts, useLocale } from "@repo/ui/hooks";
import { EmptyState } from "@repo/ui/components";
import { SkeletonJobCard } from "@repo/ui/components";
import { useSavedJobs } from "@/features/jobs/hooks/useJobList";
import { JobDiscoveryList } from "@/features/jobs/components/JobDiscoveryList";
import { JobsKanbanView } from "@/features/jobs/components/JobsKanbanView";
import { JobTable } from "@/features/jobs/components/JobTable";
import { JobFilters, applyJobFilters } from "@/features/jobs/components/JobFilters";
import { AddJobDialog } from "@/features/jobs/components/AddJobDialog";
import { JobDetailPanel } from "@/features/jobs/components/JobDetailPanel";
import { useJobsStore } from "@/features/jobs/store/jobs-store";
import type { JobFilters as JobFiltersType, SavedJob } from "@/features/jobs/types";
import { ErrorBoundary } from "@/shared/ErrorBoundary";

type PageTab = "discover" | "saved";

export default function JobsPage() {
  const [pageTab, setPageTab] = useState<PageTab>("discover");
  const [addJobOpen, setAddJobOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<SavedJob | null>(null);
  const [filters, setFilters] = useState<JobFiltersType>({});

  const router = useRouter();
  const pathname = usePathname();
  const locale = useLocale();
  const { viewMode, setViewMode } = useJobsStore();
  const { data: savedJobs, isPending } = useSavedJobs();

  // N shortcut to open Add Job dialog
  useKeyboardShortcuts([
    {
      key: "n",
      description: "Add job",
      action: () => setAddJobOpen(true),
    },
  ]);

  const filteredJobs = useMemo(
    () => applyJobFilters(savedJobs ?? [], filters),
    [savedJobs, filters]
  );

  return (
    <div className="flex flex-col h-full">
      {/* Page header */}
      <div className="flex items-center justify-between border-b border-border px-6 py-4">
        <h1 className="text-2xl font-bold">Jobs</h1>
        <button
          type="button"
          onClick={() => setAddJobOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
        >
          Add job
          <kbd className="ml-1 rounded border border-primary-foreground/30 px-1 py-0.5 text-xs opacity-70">
            N
          </kbd>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border px-6">
        {(["discover", "saved"] as PageTab[]).map((tab) => (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={pageTab === tab}
            onClick={() => setPageTab(tab)}
            className={[
              "px-4 py-3 text-sm font-medium capitalize transition-colors",
              pageTab === tab
                ? "border-b-2 border-primary text-primary"
                : "text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <ErrorBoundary section="jobs">
        {pageTab === "discover" && <JobDiscoveryList locale={locale} />}

        {pageTab === "saved" && (
          <div className="flex flex-col gap-4">
            {/* View toggle */}
            <div className="flex items-center justify-between">
              <JobFilters onFiltersChange={setFilters} />
              <div className="flex rounded-md border border-border" role="group" aria-label="View mode">
                <button
                  type="button"
                  aria-pressed={viewMode === "kanban"}
                  onClick={() => setViewMode("kanban")}
                  className={[
                    "px-3 py-1.5 text-xs font-medium rounded-l-md transition-colors",
                    viewMode === "kanban"
                      ? "bg-primary text-primary-foreground"
                      : "hover:bg-muted/50",
                  ].join(" ")}
                >
                  Kanban
                </button>
                <button
                  type="button"
                  aria-pressed={viewMode === "table"}
                  onClick={() => setViewMode("table")}
                  className={[
                    "px-3 py-1.5 text-xs font-medium rounded-r-md transition-colors",
                    viewMode === "table"
                      ? "bg-primary text-primary-foreground"
                      : "hover:bg-muted/50",
                  ].join(" ")}
                >
                  Table
                </button>
              </div>
            </div>

            {/* Empty state for no matching jobs */}
            {!isPending && filteredJobs.length === 0 && (
              <EmptyState
                aria-label="No matching jobs"
                title="No jobs match your filters"
                ctaLabel="Clear filters"
                onCta={() => {
                  setFilters({});
                  router.replace(pathname);
                }}
              />
            )}

            {/* Kanban / Table views */}
            {viewMode === "kanban" && (
              <JobsKanbanView
                jobs={filteredJobs}
                isPending={isPending}
                locale={locale}
                onJobClick={setSelectedJob}
              />
            )}
            {viewMode === "table" && !isPending && (
              <JobTable jobs={filteredJobs} locale={locale} onJobClick={setSelectedJob} />
            )}
            {viewMode === "table" && isPending && (
              <div className="flex flex-col gap-3">
                {Array.from({ length: 5 }, (_, i) => <SkeletonJobCard key={i} />)}
              </div>
            )}
          </div>
        )}
        </ErrorBoundary>
      </div>

      {/* Modals / panels */}
      <AddJobDialog open={addJobOpen} onClose={() => setAddJobOpen(false)} />
      <JobDetailPanel job={selectedJob} onClose={() => setSelectedJob(null)} />
    </div>
  );
}
