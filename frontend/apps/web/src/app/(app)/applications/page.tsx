"use client";

// Applications page — Kanban board for tracking job applications (FE-6.1)

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useKanbanApplications } from "@/features/applications/hooks/useKanban";
import { KanbanBoard } from "@/features/applications/components/KanbanBoard";
import { BulkActionBar } from "@/features/applications/components/BulkActionBar";
import { ApplicationNotes } from "@/features/applications/components/ApplicationNotes";
import { EmptyState } from "@repo/ui/components";
import type { Application } from "@/features/applications/types";

export default function ApplicationsPage() {
  const router = useRouter();
  const { data: applications = [], isPending } = useKanbanApplications();
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);

  return (
    <main className="flex flex-col gap-6 p-6" aria-label="Applications">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Applications</h1>
        <Link
          href="/applications/stats"
          className="text-sm text-primary hover:underline"
        >
          View Stats →
        </Link>
      </div>

      {!isPending && applications.length === 0 ? (
        <EmptyState
          aria-label="No applications"
          title="No applications yet"
          description="Start applying to jobs to track your progress here."
          ctaLabel="Browse jobs"
          onCta={() => router.push("/jobs")}
        />
      ) : (
        <KanbanBoard
          applications={applications}
          isPending={isPending}
          onCardClick={setSelectedApp}
        />
      )}

      {/* Bulk action bar — appears when cards are selected */}
      <BulkActionBar />

      {/* Application detail panel placeholder */}
      {selectedApp && (
        <div
          className="fixed inset-y-0 right-0 w-96 border-l border-border bg-card shadow-xl p-6 z-40 overflow-y-auto"
          aria-label={`${selectedApp.company} - ${selectedApp.job_title} detail`}
          data-testid="application-detail"
        >
          <button
            type="button"
            onClick={() => setSelectedApp(null)}
            className="mb-4 text-sm text-muted-foreground hover:text-foreground"
            aria-label="Close detail panel"
          >
            ← Back
          </button>
          <h2 className="text-base font-semibold mb-1">{selectedApp.job_title}</h2>
          <p className="text-sm text-muted-foreground mb-4">{selectedApp.company}</p>
          <ApplicationNotes applicationId={selectedApp.id} />
        </div>
      )}
    </main>
  );
}
