"use client";

// CompanyResearchCard.tsx — Company research display in job detail panel (FE-5.5)

import { useCompanyResearch, useGenerateCompanyResearch } from "../hooks/useJobDetail";
import type { CompanyResearch } from "../types";

interface CompanyResearchCardProps {
  jobId: string;
}

function SkeletonCompanyResearch() {
  return (
    <div className="flex flex-col gap-4 animate-pulse" aria-hidden="true">
      <div className="h-4 w-32 rounded bg-muted" />
      <div className="h-20 rounded bg-muted" />
      <div className="flex gap-2">
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="h-6 w-16 rounded-full bg-muted" />
        ))}
      </div>
      <div className="h-4 w-24 rounded bg-muted" />
      <div className="flex flex-col gap-2">
        {Array.from({ length: 3 }, (_, i) => (
          <div key={i} className="h-4 rounded bg-muted" />
        ))}
      </div>
    </div>
  );
}

export function CompanyResearchCard({ jobId }: CompanyResearchCardProps) {
  const { data: research, isPending } = useCompanyResearch(jobId);
  const generate = useGenerateCompanyResearch(jobId);

  if (isPending) {
    return <SkeletonCompanyResearch />;
  }

  if (!research || generate.isPending) {
    return (
      <div className="flex flex-col items-center gap-4 py-8">
        {generate.isPending ? (
          <SkeletonCompanyResearch />
        ) : (
          <>
            <p className="text-sm text-muted-foreground">No company research yet.</p>
            <button
              type="button"
              onClick={() => generate.mutate()}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
            >
              Research this company
            </button>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5" data-testid="company-research">
      {/* Culture summary */}
      {research.culture_summary && (
        <section aria-label="Culture">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            Culture
          </h4>
          <p className="text-sm leading-relaxed">{research.culture_summary}</p>
        </section>
      )}

      {/* Tech stack */}
      {research.tech_stack && research.tech_stack.length > 0 && (
        <section aria-label="Tech Stack">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            Tech Stack
          </h4>
          <div className="flex flex-wrap gap-2">
            {research.tech_stack.map((tech) => (
              <span
                key={tech}
                className="inline-flex items-center rounded-full border border-border px-2.5 py-0.5 text-xs font-semibold"
              >
                {tech}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Glassdoor rating */}
      {research.glassdoor_rating != null && (
        <section aria-label="Glassdoor Rating">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            Glassdoor Rating
          </h4>
          <div
            className="flex items-center gap-2"
            aria-label={`Glassdoor rating: ${research.glassdoor_rating} out of 5`}
          >
            <span className="text-lg font-bold">{research.glassdoor_rating.toFixed(1)}</span>
            <span className="text-muted-foreground text-sm">/ 5</span>
            <div className="flex gap-0.5" aria-hidden="true">
              {Array.from({ length: 5 }, (_, i) => (
                <span
                  key={i}
                  className={
                    i < Math.floor(research.glassdoor_rating!)
                      ? "text-amber-400"
                      : "text-muted"
                  }
                >
                  ★
                </span>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Interview patterns */}
      {research.interview_patterns && research.interview_patterns.length > 0 && (
        <section aria-label="Interview Patterns">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            Interview Patterns
          </h4>
          <ul className="flex flex-col gap-2">
            {research.interview_patterns.slice(0, 5).map((pattern, i) => (
              <li key={i} className="text-sm">
                <span className="font-medium">{pattern.theme}</span>
                {pattern.description && (
                  <p className="text-xs text-muted-foreground mt-0.5">{pattern.description}</p>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
