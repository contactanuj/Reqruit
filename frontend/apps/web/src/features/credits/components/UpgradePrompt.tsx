"use client";

// UpgradePrompt — FE-8.6
// Shown when daily credits <= 1. Displays remaining credits and upgrade CTA.

import { useRouter } from "next/navigation";
import { AlertCircle, Zap } from "lucide-react";
import { useCreditsStore } from "../store/credits-store";

const AI_ACTIONS = [
  { label: "Generate cover letter", cost: 1 },
  { label: "Company research", cost: 1 },
  { label: "Interview prep", cost: 1 },
  { label: "Outreach message", cost: 1 },
];

export function UpgradePrompt() {
  const router = useRouter();
  const dailyCredits = useCreditsStore((s) => s.dailyCredits);

  if (dailyCredits > 1) return null;

  return (
    <div
      role="alert"
      aria-label="Low credits warning"
      className="rounded-xl border border-amber-500/30 bg-amber-50/50 dark:bg-amber-900/10 p-4 space-y-3"
      data-testid="upgrade-prompt"
    >
      <div className="flex items-start gap-2">
        <AlertCircle
          className="h-5 w-5 text-amber-500 shrink-0 mt-0.5"
          aria-hidden="true"
        />
        <div className="flex-1">
          <h3 className="text-sm font-semibold">
            {dailyCredits === 0
              ? "You've used all your daily credits"
              : "1 credit remaining today"}
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Upgrade to get unlimited AI actions.
          </p>
        </div>
      </div>

      {/* AI actions cost table */}
      <ul className="space-y-1">
        {AI_ACTIONS.map(({ label, cost }) => (
          <li key={label} className="flex justify-between text-xs text-muted-foreground">
            <span>{label}</span>
            <span className="font-mono">{cost} credit</span>
          </li>
        ))}
      </ul>

      <button
        type="button"
        onClick={() => router.push("/settings/upgrade")}
        className="w-full flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        data-testid="upgrade-cta"
      >
        <Zap className="h-4 w-4" aria-hidden="true" />
        Upgrade
      </button>
    </div>
  );
}
