"use client";

// Applications Stats page (FE-6.5)

import Link from "next/link";
import { ApplicationStats } from "@/features/applications/components/ApplicationStats";

export default function ApplicationsStatsPage() {
  return (
    <main className="flex flex-col gap-6 p-6" aria-label="Application statistics">
      <div className="flex items-center gap-4">
        <Link
          href="/applications"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Applications
        </Link>
        <h1 className="text-xl font-bold">Application Statistics</h1>
      </div>

      <ApplicationStats />
    </main>
  );
}
