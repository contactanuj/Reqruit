"use client";

// SessionHistory.tsx — FE-11.5: Mock Interview Session History
// Displays a table of past mock interview sessions with score, date, type, and duration.

import { useSessionHistoryQuery } from "../hooks/useSessionHistory";
import { formatDate } from "@repo/ui/lib/locale";
import { useLocale } from "@repo/ui/hooks";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SessionHistoryProps {
  onSelectSession: (sessionId: string) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function scoreColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-amber-600";
  return "text-red-600";
}

const TYPE_LABELS: Record<string, string> = {
  behavioral: "Behavioral",
  technical: "Technical",
  system_design: "System Design",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function SessionHistory({ onSelectSession }: SessionHistoryProps) {
  const locale = useLocale();
  const { data: sessions, isLoading } = useSessionHistoryQuery();

  // Loading state
  if (isLoading) {
    return (
      <div data-testid="session-history">
        <div
          data-testid="loading-state"
          className="flex items-center justify-center py-12 text-sm text-muted-foreground"
        >
          Loading sessions…
        </div>
      </div>
    );
  }

  // Empty state
  if (!sessions || sessions.length === 0) {
    return (
      <div data-testid="session-history">
        <p
          data-testid="empty-state"
          className="py-8 text-center text-sm text-muted-foreground"
        >
          No sessions yet
        </p>
      </div>
    );
  }

  return (
    <div data-testid="session-history" className="flex flex-col gap-2">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs font-medium text-muted-foreground">
            <th scope="col" className="px-3 py-2">Date</th>
            <th scope="col" className="px-3 py-2">Type</th>
            <th scope="col" className="px-3 py-2">Duration</th>
            <th scope="col" className="px-3 py-2 text-right">Score</th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((session) => (
            <tr
              key={session.id}
              data-testid={`session-row-${session.id}`}
              onClick={() => onSelectSession(session.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelectSession(session.id);
                }
              }}
              className="cursor-pointer border-b border-border transition-colors hover:bg-muted/50"
            >
              <td className="px-3 py-2.5">{formatDate(session.date, locale)}</td>
              <td className="px-3 py-2.5">
                {TYPE_LABELS[session.type] ?? session.type}
              </td>
              <td className="px-3 py-2.5">{session.duration} min</td>
              <td className={`px-3 py-2.5 text-right font-semibold ${scoreColor(session.overallScore)}`}>
                {session.overallScore}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
