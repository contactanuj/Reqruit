// EmptyState.tsx — Shared empty state component (FE-3.2)
// Used across features when confirmed zero-data state exists.
// Accessibility: role="region" + aria-label required (NFR-A1, WCAG landmark best practices).

import * as React from "react";

export interface EmptyStateProps {
  /** Lucide icon or SVG element used as illustration */
  illustration?: React.ReactNode;
  /** Primary heading */
  title: string;
  /** Optional supporting description */
  description?: string;
  /** CTA button label */
  ctaLabel?: string;
  /** CTA button click handler */
  onCta?: () => void;
  /** Required accessible label for the region landmark */
  "aria-label": string;
}

export function EmptyState({
  illustration,
  title,
  description,
  ctaLabel,
  onCta,
  "aria-label": ariaLabel,
}: EmptyStateProps) {
  return (
    <div
      role="region"
      aria-label={ariaLabel}
      className="flex flex-col items-center justify-center gap-4 py-12 ps-6 pe-6 text-center"
    >
      {illustration && (
        <div
          aria-hidden="true"
          className="text-muted-foreground"
        >
          {illustration}
        </div>
      )}

      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        {description && (
          <p className="text-sm text-muted-foreground">{description}</p>
        )}
      </div>

      {ctaLabel && onCta && (
        <button
          type="button"
          onClick={onCta}
          className={[
            "inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium",
            "bg-primary text-primary-foreground hover:bg-primary/90 transition-colors",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
          ].join(" ")}
        >
          {ctaLabel}
        </button>
      )}
    </div>
  );
}
