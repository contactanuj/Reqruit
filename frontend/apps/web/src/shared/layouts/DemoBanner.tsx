"use client";

// DemoBanner — FE-9.4
// Persistent banner shown when isDemoMode=true.

import Link from "next/link";
import { useDemoSession } from "@/features/auth/hooks/useDemoSession";

export function DemoBanner() {
  const { isDemoMode, endDemoSession } = useDemoSession();

  if (!isDemoMode) return null;

  return (
    <div
      className="bg-primary/10 border-b border-primary/20 px-4 py-2 flex items-center justify-between text-sm"
      data-testid="demo-banner"
    >
      <span className="text-muted-foreground">
        {"You're exploring Reqruit in demo mode"}
      </span>
      <button
        type="button"
        onClick={() => void endDemoSession()}
        className="rounded-md bg-primary px-3 py-1 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        data-testid="demo-create-account-cta"
      >
        Create free account
      </button>
    </div>
  );
}
