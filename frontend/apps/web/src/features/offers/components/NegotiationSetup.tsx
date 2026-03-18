"use client";

// NegotiationSetup.tsx — FE-12.4: Negotiation configuration form
// Fields: target salary, constraints, competing offers (optional).

import * as React from "react";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import type { NegotiationConfig } from "../types";

interface NegotiationSetupProps {
  onStart: (config: NegotiationConfig) => void;
  isPending: boolean;
}

export function NegotiationSetup({ onStart, isPending }: NegotiationSetupProps) {
  const [targetSalary, setTargetSalary] = React.useState("");
  const [constraints, setConstraints] = React.useState("");
  const [competingOffers, setCompetingOffers] = React.useState("");

  const dailyCredits = useCreditsStore((s) => s.dailyCredits);
  const hasCredits = dailyCredits >= 1;

  const parsedSalary = Number(targetSalary.replace(/[^0-9]/g, ""));
  const isValid = parsedSalary > 0 && constraints.trim().length > 0;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid || !hasCredits) return;
    onStart({
      targetSalary: parsedSalary,
      constraints: constraints.trim(),
      competingOffers: competingOffers.trim() || undefined,
    });
  };

  return (
    <form
      data-testid="negotiation-setup"
      onSubmit={handleSubmit}
      className="space-y-4"
    >
      <h3 className="text-base font-semibold text-foreground">
        Negotiation Setup
      </h3>

      {/* Target salary */}
      <div>
        <label
          htmlFor="target-salary-input"
          className="mb-1 block text-sm font-medium text-foreground"
        >
          Target salary
        </label>
        <input
          id="target-salary-input"
          data-testid="target-salary-input"
          type="text"
          inputMode="numeric"
          value={targetSalary}
          onChange={(e) => setTargetSalary(e.target.value)}
          placeholder="e.g. 150000"
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        />
      </div>

      {/* Constraints */}
      <div>
        <label
          htmlFor="constraints-input"
          className="mb-1 block text-sm font-medium text-foreground"
        >
          Constraints & priorities
        </label>
        <textarea
          id="constraints-input"
          data-testid="constraints-input"
          value={constraints}
          onChange={(e) => setConstraints(e.target.value)}
          placeholder="e.g. Remote work is non-negotiable, flexible on start date..."
          rows={3}
          className="w-full resize-y rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        />
      </div>

      {/* Competing offers (optional) */}
      <div>
        <label
          htmlFor="competing-offers-input"
          className="mb-1 block text-sm font-medium text-foreground"
        >
          Competing offers{" "}
          <span className="text-muted-foreground">(optional)</span>
        </label>
        <textarea
          id="competing-offers-input"
          data-testid="competing-offers-input"
          value={competingOffers}
          onChange={(e) => setCompetingOffers(e.target.value)}
          placeholder="Describe any competing offers you have..."
          rows={2}
          className="w-full resize-y rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        />
      </div>

      {/* Submit */}
      <div className="flex items-center gap-3">
        <button
          type="submit"
          data-testid="start-negotiation-button"
          disabled={!isValid || !hasCredits || isPending}
          className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isPending ? "Starting..." : "Start negotiation advisor"}
        </button>
        {!hasCredits && (
          <span
            data-testid="no-credits-message"
            className="text-sm text-muted-foreground"
          >
            Insufficient credits
          </span>
        )}
      </div>
    </form>
  );
}
