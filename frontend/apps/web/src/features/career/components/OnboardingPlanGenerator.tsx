"use client";

// OnboardingPlanGenerator — FE-13.1
// Form to generate an AI-powered 90-day onboarding plan.

import { useState } from "react";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import { useOnboardingPlanMutation } from "../hooks/useOnboardingPlan";
import { OnboardingPlanView } from "./OnboardingPlanView";
import { useToggleMilestone } from "../hooks/useOnboardingPlan";

export function OnboardingPlanGenerator() {
  const [roleTitle, setRoleTitle] = useState("");
  const [company, setCompany] = useState("");
  const [startDate, setStartDate] = useState("");

  const dailyCredits = useCreditsStore((s) => s.dailyCredits);
  const hasCredits = dailyCredits > 0;

  const mutation = useOnboardingPlanMutation();
  const plan = mutation.data;
  const toggleMilestone = useToggleMilestone(plan?.id ?? "");

  // Start date must be today or in the future
  const today = new Date().toISOString().split("T")[0];
  const isStartDateValid = startDate >= today;
  const showDateError = startDate !== "" && !isStartDateValid;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!roleTitle.trim() || !company.trim() || !startDate || !isStartDateValid) return;
    mutation.mutate({ roleTitle: roleTitle.trim(), company: company.trim(), startDate });
  }

  function handleToggle(milestoneId: string) {
    if (!plan) return;
    const milestone = plan.milestones.find((m) => m.id === milestoneId);
    if (!milestone) return;
    toggleMilestone.mutate({ milestoneId, completed: !milestone.completed });
  }

  return (
    <div data-testid="onboarding-generator">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="field-role" className="block text-sm font-medium mb-1">
            Role Title
          </label>
          <input
            id="field-role"
            data-testid="field-role"
            type="text"
            value={roleTitle}
            onChange={(e) => setRoleTitle(e.target.value)}
            placeholder="e.g. Senior Frontend Engineer"
            className="w-full rounded-md border border-border px-3 py-2 text-sm"
            required
          />
        </div>

        <div>
          <label htmlFor="field-company" className="block text-sm font-medium mb-1">
            Company
          </label>
          <input
            id="field-company"
            data-testid="field-company"
            type="text"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="e.g. Acme Corp"
            className="w-full rounded-md border border-border px-3 py-2 text-sm"
            required
          />
        </div>

        <div>
          <label htmlFor="field-start-date" className="block text-sm font-medium mb-1">
            Start Date
          </label>
          <input
            id="field-start-date"
            data-testid="field-start-date"
            type="date"
            value={startDate}
            min={today}
            onChange={(e) => setStartDate(e.target.value)}
            aria-invalid={showDateError}
            aria-describedby={showDateError ? "start-date-error" : undefined}
            className="w-full rounded-md border border-border px-3 py-2 text-sm"
            required
          />
          {showDateError && (
            <p id="start-date-error" className="mt-1 text-xs text-destructive" role="alert">
              Start date must be today or in the future.
            </p>
          )}
        </div>

        <button
          type="submit"
          data-testid="generate-button"
          disabled={!hasCredits || mutation.isPending || !isStartDateValid}
          aria-disabled={!hasCredits || mutation.isPending || !isStartDateValid}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
        >
          {mutation.isPending ? "Generating\u2026" : "Generate plan"}
        </button>

        {!hasCredits && (
          <p className="text-sm text-destructive">Insufficient credits</p>
        )}
      </form>

      {mutation.isPending && (
        <div data-testid="generating-state" className="mt-4 text-sm text-muted-foreground animate-pulse">
          Generating onboarding plan...
        </div>
      )}

      {plan && (
        <div className="mt-6">
          <OnboardingPlanView plan={plan} onToggleMilestone={handleToggle} />
        </div>
      )}
    </div>
  );
}
