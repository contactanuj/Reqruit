"use client";

// AssemblyProgressBanner.tsx — FE-10.2 AC #2: Multi-step assembly progress indicator
// Shows horizontal progress for: Resume tailoring → Cover letter → Outreach

import * as React from "react";
import DOMPurify from "dompurify";
import type { AssemblyStep, AssemblyStepStatus } from "../hooks/useApplicationAssembly";

interface AssemblyProgressBannerProps {
  steps: AssemblyStep[];
  onRetry: (stepName: string) => void;
  isRetrying?: boolean;
  onDismiss?: () => void;
}

const STATUS_STYLES: Record<AssemblyStepStatus, string> = {
  pending: "border-muted-foreground/30 bg-muted/50 text-muted-foreground",
  running: "border-primary bg-primary/10 text-primary animate-pulse",
  complete: "border-green-500 bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400",
  error: "border-red-500 bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400",
};

function StepIcon({ status }: { status: AssemblyStepStatus }) {
  switch (status) {
    case "pending":
      return (
        <div
          className="h-5 w-5 rounded-full border-2 border-muted-foreground/30"
          aria-hidden="true"
        />
      );
    case "running":
      return (
        <div
          className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent"
          aria-hidden="true"
        />
      );
    case "complete":
      return (
        <svg
          className="h-5 w-5 text-green-600 dark:text-green-400"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
            clipRule="evenodd"
          />
        </svg>
      );
    case "error":
      return (
        <svg
          className="h-5 w-5 text-red-600 dark:text-red-400"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      );
  }
}

export function AssemblyProgressBanner({
  steps,
  onRetry,
  isRetrying = false,
  onDismiss,
}: AssemblyProgressBannerProps) {
  const completedCount = steps.filter((s) => s.status === "complete").length;
  const allComplete = completedCount === steps.length;

  return (
    <div
      className="sticky top-0 z-20 border-b border-border bg-background px-4 py-3"
      data-testid="assembly-progress-banner"
      role="progressbar"
      aria-valuenow={completedCount}
      aria-valuemax={steps.length}
      aria-label="Application assembly progress"
    >
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">
          {allComplete
            ? `Assembly complete — all ${steps.length} steps done`
            : `Assembly in progress — ${completedCount}/${steps.length} steps complete`}
        </p>
        {allComplete && onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            className="text-xs text-muted-foreground hover:text-foreground"
            aria-label="Dismiss assembly banner"
            data-testid="dismiss-banner-button"
          >
            Dismiss
          </button>
        )}
      </div>

      {/* Step indicators */}
      <div className="mt-3 flex gap-2" data-testid="assembly-steps">
        {steps.map((step, idx) => (
          <div
            key={step.step}
            className={`flex flex-1 flex-col items-center gap-1.5 rounded-md border px-3 py-2 ${STATUS_STYLES[step.status]}`}
            data-testid={`assembly-step-${step.step}`}
          >
            <div className="flex items-center gap-2">
              <StepIcon status={step.status} />
              <span className="text-xs font-medium">{step.label}</span>
            </div>

            {step.status === "error" && step.error && (
              <p className="text-xs" data-testid={`error-${step.step}`}>
                {DOMPurify.sanitize(step.error)}
              </p>
            )}

            {step.status === "error" && (
              <button
                type="button"
                onClick={() => onRetry(step.step)}
                disabled={isRetrying}
                className="mt-1 rounded-md border border-red-300 bg-white px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-50 disabled:opacity-50 dark:border-red-700 dark:bg-red-900/30 dark:text-red-300 dark:hover:bg-red-900/50"
                aria-label={`Retry ${step.label}`}
                data-testid={`retry-${step.step}`}
              >
                {isRetrying ? "Retrying…" : "Retry this step"}
              </button>
            )}

            {/* Connector line between steps */}
            {idx < steps.length - 1 && (
              <div className="hidden" aria-hidden="true" />
            )}
          </div>
        ))}
      </div>

      {/* Screen reader announcements */}
      <div aria-live="polite" className="sr-only" data-testid="assembly-sr-announcements">
        {steps.find((s) => s.status === "running") &&
          `Step ${steps.findIndex((s) => s.status === "running") + 1} of ${steps.length}: ${steps.find((s) => s.status === "running")?.label} in progress`}
        {allComplete && "Application assembly complete"}
      </div>
    </div>
  );
}
