"use client";

// CreditCounter — FE-8.6
// Sidebar widget showing remaining daily credits with aria-live for screen readers.

import { useCreditsStore } from "../store/credits-store";

export function CreditCounter() {
  const dailyCredits = useCreditsStore((s) => s.dailyCredits);

  return (
    <div
      className="px-3 py-2"
      data-testid="credit-counter"
    >
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">Credits</span>
        <span
          aria-live="polite"
          aria-label={`${dailyCredits} credits remaining today`}
          className="font-mono text-sm font-semibold tabular-nums"
        >
          {dailyCredits}
        </span>
      </div>
    </div>
  );
}
