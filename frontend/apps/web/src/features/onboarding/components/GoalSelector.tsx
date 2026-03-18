"use client";

// GoalSelector.tsx — Goal selection cards for onboarding (FE-3.1)
// Renders four goal options as radio-style cards. Min tap target 44×44px (NFR-A5).

import { useState, useRef, useCallback } from "react";
import { GOAL_OPTIONS } from "../types";
import type { OnboardingGoal } from "../types";

interface GoalSelectorProps {
  onSelect: (goal: OnboardingGoal) => void;
  onSkip: () => void;
  isPending?: boolean;
}

export function GoalSelector({ onSelect, onSkip, isPending }: GoalSelectorProps) {
  const [selected, setSelected] = useState<OnboardingGoal | null>(null);
  const groupRef = useRef<HTMLDivElement>(null);

  const handleContinue = () => {
    if (selected) {
      onSelect(selected);
    }
  };

  const handleRadioKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLButtonElement>) => {
      const isArrow =
        e.key === "ArrowDown" ||
        e.key === "ArrowUp" ||
        e.key === "ArrowLeft" ||
        e.key === "ArrowRight";
      if (!isArrow) return;
      e.preventDefault();

      const group = groupRef.current;
      if (!group) return;

      const radios = Array.from(
        group.querySelectorAll<HTMLButtonElement>('[role="radio"]'),
      );
      const currentIdx = radios.indexOf(e.currentTarget);
      if (currentIdx === -1) return;

      const direction =
        e.key === "ArrowDown" || e.key === "ArrowRight" ? 1 : -1;
      const nextIdx =
        (currentIdx + direction + radios.length) % radios.length;
      const nextRadio = radios[nextIdx];
      nextRadio.focus();

      // Select the focused option per WAI-ARIA radio group pattern
      const goalId = nextRadio.dataset.goalId as OnboardingGoal | undefined;
      if (goalId) {
        setSelected(goalId);
      }
    },
    [],
  );

  return (
    <div className="flex flex-col items-center gap-6 p-6">
      <div className="text-center">
        <h1 className="text-2xl font-bold">What is your primary goal?</h1>
        <p className="mt-2 text-muted-foreground">
          We will tailor your workspace to what matters most right now.
        </p>
      </div>

      {/* Goal cards — radio group pattern (NFR-A1) */}
      <div
        ref={groupRef}
        role="radiogroup"
        aria-label="Job search goal"
        className="grid grid-cols-1 gap-3 w-full max-w-lg sm:grid-cols-2"
      >
        {GOAL_OPTIONS.map((option, idx) => {
          const isChecked = selected === option.id;
          return (
            <button
              key={option.id}
              type="button"
              role="radio"
              aria-checked={isChecked}
              tabIndex={isChecked || (selected === null && idx === 0) ? 0 : -1}
              onClick={() => setSelected(option.id)}
              onKeyDown={handleRadioKeyDown}
              data-goal-id={option.id}
              data-testid={`goal-card-${option.id}`}
              className={[
                "min-h-[44px] min-w-[44px] rounded-lg border-2 p-4 text-start transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
                isChecked
                  ? "border-primary bg-primary/10 text-foreground"
                  : "border-border hover:border-primary/50 text-muted-foreground hover:text-foreground",
              ].join(" ")}
            >
              <span className="block font-semibold text-sm">{option.label}</span>
              <span className="block text-xs mt-1">{option.description}</span>
            </button>
          );
        })}
      </div>

      {/* Actions */}
      <div className="flex flex-col gap-3 w-full max-w-lg">
        <button
          type="button"
          onClick={handleContinue}
          disabled={!selected || isPending}
          data-testid="continue-button"
          className={[
            "w-full rounded-md px-4 py-3 text-sm font-semibold transition-colors",
            "bg-primary text-primary-foreground",
            "hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
            "disabled:opacity-50 disabled:cursor-not-allowed",
          ].join(" ")}
        >
          {isPending ? "Saving…" : "Continue"}
        </button>

        <button
          type="button"
          onClick={onSkip}
          disabled={isPending}
          data-testid="skip-button"
          className="w-full rounded-md px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          {"I'll set this later"}
        </button>
      </div>
    </div>
  );
}
