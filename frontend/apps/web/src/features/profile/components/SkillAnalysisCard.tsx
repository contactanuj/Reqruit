"use client";

// SkillAnalysisCard.tsx — FE-4.6: AI skill analysis display

import * as React from "react";
import { useSkillAnalysis, useGenerateSkillAnalysis } from "../hooks/useSkillAnalysis";
import { SkeletonSkillAnalysis } from "./SkeletonSkillAnalysis";
import type { SkillGap, TrendingSkill, SkillWithProficiency } from "../types";

const DEMAND_CLASSES: Record<string, string> = {
  high: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  medium: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  low: "bg-muted text-muted-foreground",
};

function ProficiencyBar({ skill }: { skill: SkillWithProficiency }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{skill.name}</span>
        <span className="text-xs text-muted-foreground">{skill.proficiency}%</span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={skill.proficiency}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${skill.name} proficiency: ${skill.proficiency}%`}
        className="h-2 w-full overflow-hidden rounded-full bg-muted"
      >
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${skill.proficiency}%` }}
        />
      </div>
    </div>
  );
}

function TrendingSkillBadge({ skill }: { skill: TrendingSkill }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${DEMAND_CLASSES[skill.demand] ?? ""}`}
    >
      {skill.name}
      <span className="text-xs opacity-70">({skill.demand})</span>
    </span>
  );
}

function Tooltip({ content, children }: { content: React.ReactNode; children: React.ReactNode }) {
  const [open, setOpen] = React.useState(false);
  const tooltipId = React.useId();

  return (
    <div
      className="relative inline-block"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <div aria-describedby={open ? tooltipId : undefined}>
        {children}
      </div>
      {open && (
        <div
          id={tooltipId}
          role="tooltip"
          className="absolute bottom-full left-0 z-10 mb-2 w-64 rounded-lg border border-border bg-popover p-3 shadow-lg text-sm"
        >
          {content}
        </div>
      )}
    </div>
  );
}

function SkillGapItem({ gap }: { gap: SkillGap }) {
  const hasTooltipContent = !!(gap.exampleJD || gap.learningResource);

  const tooltipContent = hasTooltipContent ? (
    <>
      {gap.exampleJD && (
        <div className="mb-2">
          <p className="font-medium text-xs text-muted-foreground uppercase mb-1">
            Example JD mention
          </p>
          <p className="text-xs">{gap.exampleJD}</p>
        </div>
      )}
      {gap.learningResource && (
        <div>
          <p className="font-medium text-xs text-muted-foreground uppercase mb-1">
            Learn more
          </p>
          <a
            href={gap.learningResource}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-primary hover:underline"
          >
            {gap.learningResource}
          </a>
        </div>
      )}
    </>
  ) : null;

  const button = (
    <button
      type="button"
      aria-label={`${gap.name} — click for details`}
      tabIndex={0}
      className="inline-flex items-center gap-1.5 rounded-md border border-dashed border-muted-foreground/40 px-3 py-1.5 text-sm text-muted-foreground hover:border-primary hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary transition-colors"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="10" />
        <line x1="12" x2="12" y1="8" y2="12" />
        <line x1="12" x2="12.01" y1="16" y2="16" />
      </svg>
      {gap.name}
    </button>
  );

  if (!hasTooltipContent) return button;

  return (
    <Tooltip content={tooltipContent}>
      {button}
    </Tooltip>
  );
}

export function SkillAnalysisCard() {
  const { data, isPending } = useSkillAnalysis();
  const { mutate: generate, isPending: isGenerating } = useGenerateSkillAnalysis();

  if (isPending || isGenerating) {
    return <SkeletonSkillAnalysis />;
  }

  // Analysis not yet generated
  if (data === null || data === undefined) {
    return (
      <div className="flex flex-col items-center gap-4 py-8 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-primary"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="10" />
            <path d="M12 8v4" />
            <path d="M12 16h.01" />
          </svg>
        </div>
        <div>
          <p className="font-semibold">No skill analysis yet</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Generate an AI-powered analysis of your skills vs. your target roles.
          </p>
        </div>
        <button
          type="button"
          onClick={() => generate()}
          disabled={isGenerating}
          className="rounded-md bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isGenerating ? "Generating…" : "Generate skill analysis"}
        </button>
      </div>
    );
  }

  // Analysis exists — show all three sections
  return (
    <div className="flex flex-col gap-8">
      {/* Your Skills */}
      <section aria-label="Your skills">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Your Skills
        </h3>
        <div className="flex flex-col gap-3">
          {data.yourSkills.map((skill) => (
            <ProficiencyBar key={skill.name} skill={skill} />
          ))}
        </div>
      </section>

      {/* Trending in Target Roles */}
      <section aria-label="Trending in target roles">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Trending in Your Target Roles
        </h3>
        <div className="flex flex-wrap gap-2">
          {data.trendingInTargetRoles.map((skill) => (
            <TrendingSkillBadge key={skill.name} skill={skill} />
          ))}
        </div>
      </section>

      {/* Skill Gaps */}
      <section aria-label="Skill gaps">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Skill Gaps
        </h3>
        <div className="flex flex-wrap gap-2">
          {data.skillGaps.map((gap) => (
            <SkillGapItem key={gap.name} gap={gap} />
          ))}
        </div>
      </section>
    </div>
  );
}
