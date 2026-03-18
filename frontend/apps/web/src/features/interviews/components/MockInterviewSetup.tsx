"use client";

// MockInterviewSetup.tsx — FE-11.4: Configure and start a mock interview session
// Credit-gated: requires dailyCredits >= 1 to start.

import { useState } from "react";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import { useStartSession } from "../hooks/useMockInterview";
import type { InterviewType, SessionDuration } from "../types";

interface MockInterviewSetupProps {
  onSessionStart?: () => void;
}

const INTERVIEW_TYPES: { value: InterviewType; label: string }[] = [
  { value: "behavioral", label: "Behavioral" },
  { value: "technical", label: "Technical" },
  { value: "system_design", label: "System Design" },
];

const DURATION_OPTIONS: { value: SessionDuration; label: string }[] = [
  { value: 30, label: "30 min" },
  { value: 45, label: "45 min" },
  { value: 60, label: "60 min" },
];

export function MockInterviewSetup({ onSessionStart }: MockInterviewSetupProps) {
  const [selectedType, setSelectedType] = useState<InterviewType>("behavioral");
  const [selectedDuration, setSelectedDuration] = useState<SessionDuration>(30);

  const dailyCredits = useCreditsStore((s) => s.dailyCredits);
  const { mutate: startSession, isPending } = useStartSession();

  const hasCredits = dailyCredits >= 1;
  const isDisabled = !hasCredits || isPending;

  const handleStart = () => {
    if (isDisabled) return;
    startSession(
      { type: selectedType, duration: selectedDuration },
      { onSuccess: onSessionStart },
    );
  };

  return (
    <div data-testid="mock-setup" className="flex flex-col gap-6">
      {/* Interview type selection */}
      <fieldset className="flex flex-col gap-2">
        <legend className="text-sm font-semibold text-foreground">
          Interview type
        </legend>
        <div className="flex flex-wrap gap-3">
          {INTERVIEW_TYPES.map(({ value, label }) => (
            <label
              key={value}
              className={`inline-flex cursor-pointer items-center gap-2 rounded-md border px-4 py-2 text-sm transition-colors ${
                selectedType === value
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border bg-card text-foreground hover:bg-muted"
              }`}
            >
              <input
                type="radio"
                name="interview-type"
                value={value}
                checked={selectedType === value}
                onChange={() => setSelectedType(value)}
                data-testid={`type-${value}`}
                className="sr-only"
              />
              {label}
            </label>
          ))}
        </div>
      </fieldset>

      {/* Duration selection */}
      <fieldset className="flex flex-col gap-2">
        <legend className="text-sm font-semibold text-foreground">
          Duration
        </legend>
        <div className="flex flex-wrap gap-3">
          {DURATION_OPTIONS.map(({ value, label }) => (
            <label
              key={value}
              className={`inline-flex cursor-pointer items-center gap-2 rounded-md border px-4 py-2 text-sm transition-colors ${
                selectedDuration === value
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border bg-card text-foreground hover:bg-muted"
              }`}
            >
              <input
                type="radio"
                name="interview-duration"
                value={value}
                checked={selectedDuration === value}
                onChange={() => setSelectedDuration(value)}
                data-testid={`duration-${value}`}
                className="sr-only"
              />
              {label}
            </label>
          ))}
        </div>
      </fieldset>

      {/* Start button */}
      <div className="flex flex-col items-start gap-2">
        <button
          type="button"
          onClick={handleStart}
          disabled={isDisabled}
          aria-disabled={isDisabled}
          data-testid="start-button"
          className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md bg-primary px-6 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isPending ? "Starting..." : "Start interview"}
        </button>
        {!hasCredits && (
          <p className="text-sm text-muted-foreground">
            Insufficient credits ({dailyCredits} remaining)
          </p>
        )}
      </div>
    </div>
  );
}
