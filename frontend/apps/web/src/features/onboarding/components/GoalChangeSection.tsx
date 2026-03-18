"use client";

// GoalChangeSection.tsx — Allow users to change their goal from settings (FE-3.1)

import { useOnboardingStore } from "../store/onboarding-store";
import { useSetGoal } from "../hooks/useOnboarding";
import { GOAL_OPTIONS } from "../types";
import type { OnboardingGoal } from "../types";

export function GoalChangeSection() {
  const { goal } = useOnboardingStore();
  const updateGoal = useSetGoal();

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newGoal = e.target.value as OnboardingGoal;
    if (newGoal && newGoal !== goal) {
      updateGoal.mutate(newGoal);
    }
  };

  return (
    <section aria-label="Goal selection">
      <h3 className="text-sm font-semibold text-foreground mb-2">Your goal</h3>
      <div className="flex flex-col gap-1.5">
        <label htmlFor="goal-select" className="text-sm text-muted-foreground">
          Choose what you want to focus on. This controls which features are visible.
        </label>
        <select
          id="goal-select"
          value={goal ?? ""}
          onChange={handleChange}
          disabled={updateGoal.isPending}
          data-testid="goal-select"
          className="rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 max-w-xs"
        >
          <option value="" disabled>
            Select a goal…
          </option>
          {GOAL_OPTIONS.map((opt) => (
            <option key={opt.id} value={opt.id}>
              {opt.label}
            </option>
          ))}
        </select>
        {goal && (
          <p className="text-xs text-muted-foreground mt-1">
            {GOAL_OPTIONS.find((o) => o.id === goal)?.description}
          </p>
        )}
      </div>
    </section>
  );
}
