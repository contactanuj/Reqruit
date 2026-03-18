"use client";

// JobCard.tsx — Job card for shortlist and saved views (FE-5.1, FE-5.6, FE-5.8)

import { useState } from "react";
import { formatLPA, formatCTC } from "@repo/ui/lib/locale";
import type { LocaleCode } from "@repo/ui/lib/locale";
import { CTCDecoder } from "@repo/ui/components";
import { GhostJobFreshnessIndicator } from "./GhostJobFreshnessIndicator";
import type { SavedJob } from "../types";

export interface JobCardProps {
  job: SavedJob;
  locale?: LocaleCode;
  onClick?: (job: SavedJob) => void;
  isNew?: boolean;
}

export function JobCard({ job, locale = "US", onClick, isNew }: JobCardProps) {
  const [ctcOpen, setCtcOpen] = useState(false);

  const hasSalary = job.salary_min != null || job.salary_max != null;
  const salaryMin = job.salary_min ?? 0;
  const salaryMax = job.salary_max ?? salaryMin;

  function renderSalary() {
    if (!hasSalary) return null;

    if (locale === "IN") {
      const display = salaryMax > salaryMin
        ? `${formatLPA(salaryMin, "IN")}–${formatLPA(salaryMax, "IN")}`
        : formatLPA(salaryMin, "IN");

      return (
        <>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setCtcOpen(true);
            }}
            className="text-xs font-mono text-primary underline decoration-dotted cursor-pointer hover:no-underline"
            aria-label={`CTC: ${display}. Click to decode`}
          >
            {display}
          </button>
          <CTCDecoder
            salaryMin={salaryMin}
            salaryMax={salaryMax}
            locale="IN"
            open={ctcOpen}
            onClose={() => setCtcOpen(false)}
          />
        </>
      );
    }

    // US locale — static display
    const display = salaryMax > salaryMin
      ? `${formatCTC(salaryMin, "US")}–${formatCTC(salaryMax, "US")}`
      : formatCTC(salaryMin, "US");
    return <span className="text-xs font-mono text-muted-foreground">{display}</span>;
  }

  return (
    <div
      role="article"
      className={[
        "relative rounded-lg border bg-card p-4 cursor-pointer",
        "hover:border-primary/50 hover:shadow-sm transition-all duration-150",
        "focus-within:ring-2 focus-within:ring-primary",
      ].join(" ")}
      onClick={() => onClick?.(job)}
      data-testid="job-card"
    >
      {/* New indicator */}
      {isNew && (
        <span className="absolute top-2 right-2 rounded-full bg-primary px-2 py-0.5 text-xs text-primary-foreground">
          Updated
        </span>
      )}

      {/* Company + freshness */}
      <div className="flex items-start justify-between gap-2 mb-1">
        <span className="text-sm font-medium text-muted-foreground">{job.company}</span>
        {job.staleness_score != null && (
          <GhostJobFreshnessIndicator
            stalenessScore={job.staleness_score}
            postedAt={job.posted_at}
            lastVerifiedAt={job.last_verified_at}
            locale={locale}
          />
        )}
      </div>

      {/* Role title */}
      <h3 className="text-base font-semibold leading-tight mb-1">{job.title}</h3>

      {/* Location */}
      {job.location && (
        <p className="text-xs text-muted-foreground mb-2">{job.location}</p>
      )}

      {/* Fit score + salary row */}
      <div className="flex flex-wrap items-center gap-2">
        {job.fit_score != null && (
          <span
            className="inline-flex items-center rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary"
            aria-label={`Fit score: ${job.fit_score}%`}
          >
            {job.fit_score}% fit
          </span>
        )}
        {job.roi_prediction && (
          <span className="text-xs text-muted-foreground">{job.roi_prediction}</span>
        )}
        {renderSalary()}
      </div>
    </div>
  );
}
