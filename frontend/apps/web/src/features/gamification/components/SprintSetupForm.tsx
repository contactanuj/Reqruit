"use client";

// SprintSetupForm — FE-14.2
// Dynamic form for setting up sprint goals with add/remove controls.

import { useState, useCallback } from "react";
import { Trash2, Plus } from "lucide-react";
import { useCreateSprint } from "../hooks/useSprints";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface GoalInput {
  description: string;
  targetCount: number | "";
}

interface SprintSetupFormProps {
  onSprintCreated?: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function SprintSetupForm({ onSprintCreated }: SprintSetupFormProps) {
  const [goals, setGoals] = useState<GoalInput[]>([
    { description: "", targetCount: "" },
  ]);

  const createSprint = useCreateSprint();

  const updateGoal = useCallback(
    (index: number, field: keyof GoalInput, value: string | number) => {
      setGoals((prev) =>
        prev.map((g, i) => (i === index ? { ...g, [field]: value } : g)),
      );
    },
    [],
  );

  const addGoal = useCallback(() => {
    setGoals((prev) => [...prev, { description: "", targetCount: "" }]);
  }, []);

  const removeGoal = useCallback(
    (index: number) => {
      if (goals.length <= 1) return;
      setGoals((prev) => prev.filter((_, i) => i !== index));
    },
    [goals.length],
  );

  const isGoalValid = (goal: GoalInput): boolean =>
    goal.description.trim().length > 0 &&
    typeof goal.targetCount === "number" &&
    goal.targetCount > 0;

  const allGoalsValid = goals.every(isGoalValid);

  // Last goal must be valid before allowing add
  const canAddGoal = goals.length > 0 && isGoalValid(goals[goals.length - 1]);

  const handleSubmit = () => {
    if (!allGoalsValid) return;

    const payload = {
      goals: goals.map((g) => ({
        description: g.description.trim(),
        targetCount: g.targetCount as number,
      })),
    };

    createSprint.mutate(payload, {
      onSuccess: () => {
        setGoals([{ description: "", targetCount: "" }]);
        onSprintCreated?.();
      },
    });
  };

  return (
    <div data-testid="sprint-setup" className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Set Up Sprint</h3>
        <span
          data-testid="sprint-duration"
          className="rounded-full bg-muted px-3 py-1 text-xs font-medium text-muted-foreground"
        >
          14-day sprint
        </span>
      </div>

      <div className="space-y-3">
        {goals.map((goal, index) => (
          <div
            key={index}
            className="flex items-start gap-2"
          >
            <div className="flex-1 space-y-1">
              <label
                htmlFor={`goal-desc-${index}`}
                className="text-sm font-medium"
              >
                Goal {index + 1}
              </label>
              <input
                id={`goal-desc-${index}`}
                data-testid={`goal-input-${index}`}
                type="text"
                placeholder="e.g., Apply to 5 jobs"
                value={goal.description}
                onChange={(e) =>
                  updateGoal(index, "description", e.target.value)
                }
                className="w-full rounded-md border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            <div className="w-24 space-y-1">
              <label
                htmlFor={`goal-target-${index}`}
                className="text-sm font-medium"
              >
                Target
              </label>
              <input
                id={`goal-target-${index}`}
                data-testid={`goal-target-${index}`}
                type="number"
                min={1}
                placeholder="Count"
                value={goal.targetCount}
                onChange={(e) => {
                  const val = e.target.value;
                  updateGoal(
                    index,
                    "targetCount",
                    val === "" ? "" : parseInt(val, 10),
                  );
                }}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            {goals.length > 1 && (
              <button
                data-testid={`remove-goal-${index}`}
                type="button"
                onClick={() => removeGoal(index)}
                aria-label={`Remove goal ${index + 1}`}
                className="mt-6 rounded-md p-2 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
              </button>
            )}
          </div>
        ))}
      </div>

      <div className="flex items-center gap-3">
        <button
          data-testid="add-goal-button"
          type="button"
          onClick={addGoal}
          disabled={!canAddGoal}
          className="inline-flex items-center gap-1.5 rounded-md border px-3 py-2 text-sm font-medium transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          Add goal
        </button>

        <button
          data-testid="start-sprint-button"
          type="button"
          onClick={handleSubmit}
          disabled={!allGoalsValid || createSprint.isPending}
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {createSprint.isPending ? "Starting…" : "Start sprint"}
        </button>
      </div>
    </div>
  );
}
