"use client";

// AssemblyWorkflow.tsx — FE-10.2: Full Application Assembly Workflow
// "Assemble application" trigger button + progress banner + nudge card integration.

import * as React from "react";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import {
  useStartAssembly,
  useAssemblyStatus,
  useRetryAssemblyStep,
  ASSEMBLY_CREDIT_COST,
} from "../hooks/useApplicationAssembly";
import { AssemblyProgressBanner } from "./AssemblyProgressBanner";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AssemblyWorkflowProps {
  applicationId: string;
  hasMasterResume: boolean;
  /** Called when a HITL-requiring step completes (cover_letter or outreach) */
  onStepNeedsReview?: (step: string, applicationId: string) => void;
}

// Default assembly steps shown in the progress banner
const DEFAULT_STEPS = [
  { step: "resume_tailoring", label: "Resume tailoring", status: "pending" as const },
  { step: "cover_letter", label: "Cover letter", status: "pending" as const },
  { step: "outreach", label: "Outreach", status: "pending" as const },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function AssemblyWorkflow({
  applicationId,
  hasMasterResume,
  onStepNeedsReview,
}: AssemblyWorkflowProps) {
  const [assemblyId, setAssemblyId] = React.useState<string | null>(null);
  const [dismissed, setDismissed] = React.useState(false);
  const [notifiedSteps, setNotifiedSteps] = React.useState<Set<string>>(new Set());

  const dailyCredits = useCreditsStore((s) => s.dailyCredits);

  const { mutate: startAssembly, isPending: isStarting } = useStartAssembly(applicationId);
  const { data: statusData } = useAssemblyStatus(applicationId, assemblyId);
  const { mutate: retryStep, isPending: isRetrying } = useRetryAssemblyStep(applicationId);

  const hasCredits = dailyCredits >= ASSEMBLY_CREDIT_COST;
  const isDisabled = !hasMasterResume || !hasCredits || isStarting;
  const isAssembling = !!assemblyId;
  const steps = statusData?.steps ?? DEFAULT_STEPS;
  const allComplete = steps.every((s) => s.status === "complete");

  // Notify parent when HITL-requiring steps complete (AC #3)
  React.useEffect(() => {
    if (!statusData?.steps || !onStepNeedsReview) return;

    for (const step of statusData.steps) {
      if (
        step.status === "complete" &&
        !notifiedSteps.has(step.step) &&
        (step.step === "cover_letter" || step.step === "outreach")
      ) {
        onStepNeedsReview(step.step, applicationId);
        setNotifiedSteps((prev) => new Set(prev).add(step.step));
      }
    }
  }, [statusData?.steps, onStepNeedsReview, applicationId, notifiedSteps]);

  const handleStart = () => {
    if (isDisabled) return;
    startAssembly(undefined, {
      onSuccess: (data) => {
        setAssemblyId(data.assembly_id);
        setDismissed(false);
        setNotifiedSteps(new Set());
      },
    });
  };

  const handleRetry = (stepName: string) => {
    retryStep({ stepName });
  };

  // Show progress banner when assembly is active
  if (isAssembling && !dismissed) {
    return (
      <div data-testid="assembly-workflow">
        <AssemblyProgressBanner
          steps={steps}
          onRetry={handleRetry}
          isRetrying={isRetrying}
          onDismiss={allComplete ? () => setDismissed(true) : undefined}
        />
      </div>
    );
  }

  // No master resume — disabled with tooltip
  if (!hasMasterResume) {
    return (
      <div className="relative inline-block group" data-testid="assembly-workflow">
        <button
          type="button"
          disabled
          aria-disabled="true"
          data-testid="assemble-button"
          className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground opacity-50 cursor-not-allowed"
        >
          Assemble application
        </button>
        <span
          role="tooltip"
          className="pointer-events-none absolute bottom-full left-1/2 mb-2 -translate-x-1/2 whitespace-nowrap rounded bg-foreground px-2 py-1 text-xs text-background opacity-0 transition-opacity group-hover:opacity-100"
        >
          Upload and set a master resume first
        </span>
      </div>
    );
  }

  // No credits — disabled with message
  if (!hasCredits) {
    return (
      <div className="flex flex-col items-start gap-2" data-testid="assembly-workflow">
        <button
          type="button"
          disabled
          aria-disabled="true"
          data-testid="assemble-button"
          className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground opacity-50 cursor-not-allowed"
        >
          Assemble application
        </button>
        <p className="text-sm text-muted-foreground" data-testid="insufficient-credits-message">
          Requires {ASSEMBLY_CREDIT_COST} credits ({dailyCredits} remaining) —{" "}
          <a
            href="/pricing"
            className="font-medium text-primary underline-offset-2 hover:underline"
          >
            upgrade for more
          </a>
        </p>
      </div>
    );
  }

  // Normal enabled state
  return (
    <div className="flex flex-col items-start gap-1" data-testid="assembly-workflow">
      <button
        type="button"
        onClick={handleStart}
        disabled={isStarting}
        data-testid="assemble-button"
        className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50"
      >
        {isStarting ? "Starting…" : "Assemble application"}
      </button>
      {dailyCredits <= ASSEMBLY_CREDIT_COST * 2 && (
        <p className="text-xs text-amber-600" data-testid="low-credits-warning">
          Low credits — {dailyCredits} credits remaining
        </p>
      )}
    </div>
  );
}
