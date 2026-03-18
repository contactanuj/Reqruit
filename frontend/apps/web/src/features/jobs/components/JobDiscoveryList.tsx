"use client";

// JobDiscoveryList.tsx — Daily job shortlist display (FE-5.1)

import { useRouter } from "next/navigation";
import { SkeletonJobCard } from "@repo/ui/components";
import { EmptyState } from "@repo/ui/components";
import type { LocaleCode } from "@repo/ui/lib/locale";
import { useJobShortlist } from "../hooks/useJobList";
import { JobCard } from "./JobCard";
import type { SavedJob } from "../types";

export interface JobDiscoveryListProps {
  locale?: LocaleCode;
  onJobClick?: (job: SavedJob) => void;
}

export function JobDiscoveryList({ locale = "US", onJobClick }: JobDiscoveryListProps) {
  const router = useRouter();
  const { data: jobs, isPending, isError } = useJobShortlist();

  if (isPending) {
    return (
      <div className="flex flex-col gap-3" aria-label="Loading job shortlist">
        {Array.from({ length: 5 }, (_, i) => (
          <SkeletonJobCard key={i} />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center gap-4 py-8 text-center" role="alert">
        <p className="text-sm text-destructive font-medium">Failed to load job shortlist</p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!jobs || jobs.length === 0) {
    return (
      <EmptyState
        aria-label="No job shortlist"
        title="Add your target roles in your profile to get personalized job matches"
        ctaLabel="Update profile"
        onCta={() => router.push("/profile?edit=true")}
      />
    );
  }

  return (
    <div className="flex flex-col gap-3" aria-label="Daily job shortlist">
      {jobs.map((job) => (
        <JobCard
          key={job.id}
          job={job}
          locale={locale}
          isNew={job.is_new}
          onClick={onJobClick}
        />
      ))}
    </div>
  );
}
