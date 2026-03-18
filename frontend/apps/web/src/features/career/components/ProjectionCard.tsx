"use client";

// ProjectionCard — FE-13.3
// Displays a single career path projection with skill milestones and resources.

import DOMPurify from "dompurify";
import type { PathProjection } from "../types";

interface ProjectionCardProps {
  projection: PathProjection;
}

function sanitize(text: string): string {
  return DOMPurify.sanitize(text);
}

export function ProjectionCard({ projection }: ProjectionCardProps) {
  return (
    <div
      data-testid={`projection-card-${projection.roleTitle}`}
      className="rounded-lg border border-border p-4 space-y-3"
    >
      <h3 className="text-base font-semibold">
        {sanitize(projection.roleTitle)}
      </h3>

      <div data-testid="transition-timeline" className="text-sm text-muted-foreground">
        Estimated transition: {projection.transitionMonths} months
      </div>

      {projection.milestones.length > 0 && (
        <div>
          <h4 className="text-sm font-medium mb-1">Skill Milestones</h4>
          <ul className="space-y-1">
            {projection.milestones.map((milestone, index) => (
              <li
                key={milestone.skill}
                data-testid={`skill-milestone-${index}`}
                className="text-sm flex justify-between"
              >
                <span>{sanitize(milestone.skill)}</span>
                <span className="text-muted-foreground">
                  ~{milestone.estimatedMonths}mo
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {projection.resources.length > 0 && (
        <div data-testid="resources-list">
          <h4 className="text-sm font-medium mb-1">Resources</h4>
          <ul className="list-disc list-inside text-sm space-y-0.5">
            {projection.resources.map((resource, index) => (
              <li key={index} className="text-muted-foreground">
                {sanitize(resource)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
