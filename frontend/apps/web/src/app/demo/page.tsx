"use client";

// Demo page — FE-9.4
// Public route: starts demo session on load and redirects to /dashboard.

import { useEffect, useState } from "react";
import { useDemoSession } from "@/features/auth/hooks/useDemoSession";

export default function DemoPage() {
  const { startDemoSession } = useDemoSession();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    startDemoSession().catch((err: unknown) => {
      const message =
        err instanceof Error ? err.message : "Unable to start demo session";
      setError(message);
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center space-y-4 max-w-sm px-4">
          <p className="text-sm text-destructive font-medium">{error}</p>
          <button
            type="button"
            className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            onClick={() => {
              setError(null);
              startDemoSession().catch((err: unknown) => {
                const msg =
                  err instanceof Error
                    ? err.message
                    : "Unable to start demo session";
                setError(msg);
              });
            }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen items-center justify-center">
      <div className="text-center space-y-3">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto" />
        <p className="text-sm text-muted-foreground">Loading demo…</p>
      </div>
    </div>
  );
}
