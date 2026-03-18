"use client";

// ResumeParseStatus.tsx — FE-4.2: Real-time parse status with polling

import { useEffect, useRef } from "react";
import { toast } from "sonner";
import { useResumeParseStatus } from "../hooks/useProfile";
import type { ResumeParseStatus as ParseStatus } from "../types";

interface ResumeParseStatusProps {
  resumeId: string;
  onComplete?: () => void;
  onRetry?: () => void;
}

type Step = { id: ParseStatus | "idle"; label: string };

const STEPS: Step[] = [
  { id: "pending", label: "Pending" },
  { id: "processing", label: "Processing" },
  { id: "completed", label: "Completed" },
];

function getStepIndex(status: ParseStatus): number {
  if (status === "failed") return -1;
  return STEPS.findIndex((s) => s.id === status);
}

export function ResumeParseStatus({ resumeId, onComplete, onRetry }: ResumeParseStatusProps) {
  const { data, isPending } = useResumeParseStatus(resumeId);

  const status = data?.status;

  // Ref to avoid stale closure: onComplete may change on every parent render
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  useEffect(() => {
    if (status === "completed") {
      toast.success("Resume parsed successfully", { duration: 3000 });
      onCompleteRef.current?.();
    }
  }, [status]);

  if (isPending) {
    // Show all steps in "pending" state as the loading indicator (no spinner)
    return (
      <div className="flex flex-col items-center gap-6 py-8">
        <div aria-live="polite" className="sr-only">
          Checking resume parse status
        </div>
        <ol className="flex items-center gap-4">
          {STEPS.map((step, index) => (
            <li key={step.id} className="flex items-center gap-2">
              <div
                className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-border text-sm font-semibold text-muted-foreground"
              >
                {index + 1}
              </div>
              <span className="text-sm font-medium text-muted-foreground">
                {step.label}
              </span>
              {index < STEPS.length - 1 && (
                <div className="h-px w-8 bg-border" />
              )}
            </li>
          ))}
        </ol>
        <p className="text-sm text-muted-foreground">Checking parse status…</p>
      </div>
    );
  }

  if (status === "failed") {
    return (
      <div className="flex flex-col items-center gap-4 py-8 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            className="text-destructive"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" x2="12" y1="8" y2="12" />
            <line x1="12" x2="12.01" y1="16" y2="16" />
          </svg>
        </div>
        <div>
          <p className="font-medium text-destructive">We couldn&apos;t parse this resume</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Try a different format (PDF or DOCX recommended)
          </p>
        </div>
        <button
          type="button"
          onClick={onRetry}
          className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          Try again
        </button>
      </div>
    );
  }

  const currentIndex = status ? getStepIndex(status) : 0;

  return (
    <div className="flex flex-col items-center gap-6 py-8">
      <div aria-live="polite" className="sr-only">
        {status ? `Resume parse status: ${status}` : "Checking resume parse status"}
      </div>

      {/* Step indicator */}
      <ol className="flex items-center gap-4">
        {STEPS.map((step, index) => {
          const isActive = index === currentIndex;
          const isComplete = index < currentIndex || status === "completed";

          return (
            <li key={step.id} className="flex items-center gap-2">
              <div
                aria-current={isActive ? "step" : undefined}
                className={[
                  "flex h-8 w-8 items-center justify-center rounded-full border-2 text-sm font-semibold transition-colors",
                  isComplete
                    ? "border-primary bg-primary text-primary-foreground"
                    : isActive
                    ? "border-primary bg-primary/10 text-primary @motion-reduce:animate-none animate-pulse"
                    : "border-border text-muted-foreground",
                ].join(" ")}
              >
                {isComplete ? (
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  index + 1
                )}
              </div>
              <span
                className={[
                  "text-sm font-medium",
                  isActive || isComplete ? "text-foreground" : "text-muted-foreground",
                ].join(" ")}
              >
                {step.label}
              </span>
              {index < STEPS.length - 1 && (
                <div
                  className={[
                    "h-px w-8 transition-colors",
                    isComplete ? "bg-primary" : "bg-border",
                  ].join(" ")}
                />
              )}
            </li>
          );
        })}
      </ol>

      <p className="text-sm text-muted-foreground">
        {status === "completed"
          ? "Your resume has been parsed successfully!"
          : status === "processing"
          ? "Extracting information from your resume…"
          : "Waiting to start processing…"}
      </p>
    </div>
  );
}
