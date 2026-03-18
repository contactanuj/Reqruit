"use client";

// GenerateButton.tsx — FE-7.1: Initiate cover letter generation
// UX-18: The Generate button is an explicit user action — never auto-trigger.

import { useState, useRef, useCallback } from "react";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import { useCoverLetterGeneration } from "../hooks/useCoverLetterGeneration";

interface GenerateButtonProps {
  applicationId: string;
  hasMasterResume: boolean;
  /** Called after generation is successfully initiated (transitions to visualizer). */
  onGenerated?: () => void;
}

export function GenerateButton({
  applicationId,
  hasMasterResume,
  onGenerated,
}: GenerateButtonProps) {
  const dailyCredits = useCreditsStore((s) => s.dailyCredits);
  const { mutate: generate, isPending } = useCoverLetterGeneration(applicationId);

  const hasCredits = dailyCredits > 0;
  const isDisabled = !hasMasterResume || !hasCredits || isPending;

  const handleClick = () => {
    if (isDisabled) return;
    generate(undefined, { onSuccess: onGenerated });
  };

  // No master resume — disabled with accessible tooltip
  if (!hasMasterResume) {
    return <DisabledWithTooltip />;
  }

  // No credits — show upgrade CTA
  if (!hasCredits) {
    return (
      <div className="flex flex-col items-start gap-2">
        <button
          type="button"
          disabled
          aria-disabled="true"
          data-testid="generate-button"
          className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground opacity-50 cursor-not-allowed"
        >
          Generate Cover Letter
        </button>
        <p className="text-sm text-muted-foreground" data-testid="no-credits-message">
          0 credits remaining —{" "}
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
    <div className="flex flex-col items-start gap-1">
      <button
        type="button"
        onClick={handleClick}
        disabled={isPending}
        data-testid="generate-button"
        className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50"
      >
        {isPending ? "Starting…" : "Generate Cover Letter"}
      </button>
      {dailyCredits === 1 && (
        <p className="text-xs text-amber-600" data-testid="low-credits-warning">
          1 credit remaining
        </p>
      )}
    </div>
  );
}

/**
 * Accessible tooltip for the disabled "no master resume" state.
 * Uses state-driven visibility for hover, focus, and touch — no CSS-only hover
 * which fails on touch devices and has no keyboard support.
 */
function DisabledWithTooltip() {
  const [showTooltip, setShowTooltip] = useState(false);
  const tooltipId = "generate-tooltip";
  const hideTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = useCallback(() => {
    if (hideTimeout.current) clearTimeout(hideTimeout.current);
    setShowTooltip(true);
  }, []);

  const hide = useCallback(() => {
    hideTimeout.current = setTimeout(() => setShowTooltip(false), 150);
  }, []);

  const handleTouchStart = useCallback(() => {
    // Toggle on touch so tap-to-reveal works
    setShowTooltip((prev) => !prev);
  }, []);

  return (
    <div
      className="relative inline-block"
      onMouseEnter={show}
      onMouseLeave={hide}
    >
      <button
        type="button"
        disabled
        aria-disabled="true"
        aria-describedby={tooltipId}
        data-testid="generate-button"
        onFocus={show}
        onBlur={hide}
        onTouchStart={handleTouchStart}
        className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground opacity-50 cursor-not-allowed"
      >
        Generate Cover Letter
      </button>
      {showTooltip && (
        <span
          id={tooltipId}
          role="tooltip"
          className="pointer-events-none absolute bottom-full left-1/2 mb-2 -translate-x-1/2 whitespace-nowrap rounded bg-foreground px-2 py-1 text-xs text-background"
        >
          Upload and set a master resume first
        </span>
      )}
    </div>
  );
}
