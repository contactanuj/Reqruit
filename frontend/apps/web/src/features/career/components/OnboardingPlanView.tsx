"use client";

// OnboardingPlanView — FE-13.1
// Displays a 90-day onboarding plan with three phases and interactive milestones.

import type { OnboardingPlan, OnboardingMilestone } from "../types";

interface OnboardingPlanViewProps {
  plan: OnboardingPlan;
  onToggleMilestone: (milestoneId: string) => void;
}

const PHASE_LABELS: Record<OnboardingMilestone["phase"], string> = {
  days_1_30: "Days 1-30",
  days_31_60: "Days 31-60",
  days_61_90: "Days 61-90",
};

const PHASES: OnboardingMilestone["phase"][] = ["days_1_30", "days_31_60", "days_61_90"];

export function OnboardingPlanView({ plan, onToggleMilestone }: OnboardingPlanViewProps) {
  return (
    <div data-testid="onboarding-plan" className="space-y-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold">{plan.roleTitle}</h3>
        <p className="text-sm text-muted-foreground">
          {plan.company} &middot; Starting {plan.startDate}
        </p>
      </div>

      {PHASES.map((phase) => {
        const milestones = plan.milestones.filter((m) => m.phase === phase);

        return (
          <section key={phase} data-testid={`phase-${phase}`} className="space-y-2">
            <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
              {PHASE_LABELS[phase]}
            </h4>

            {milestones.length === 0 ? (
              <p className="text-sm text-muted-foreground italic">No milestones</p>
            ) : (
              <ul className="space-y-1">
                {milestones.map((milestone) => (
                  <li
                    key={milestone.id}
                    data-testid={`milestone-${milestone.id}`}
                    className="flex items-start gap-2"
                  >
                    <input
                      type="checkbox"
                      data-testid={`milestone-checkbox-${milestone.id}`}
                      checked={milestone.completed}
                      onChange={() => onToggleMilestone(milestone.id)}
                      aria-label={`Toggle milestone: ${milestone.text}`}
                      className="mt-0.5 h-4 w-4 shrink-0 cursor-pointer rounded border-border accent-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    />
                    <span
                      className={
                        milestone.completed
                          ? "text-sm line-through text-muted-foreground"
                          : "text-sm"
                      }
                    >
                      {milestone.text}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        );
      })}
    </div>
  );
}
