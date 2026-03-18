"use client";

// LeagueLeaderboard — FE-14.1
// Accessible leaderboard table showing top 20 weekly XP leaders with
// current user highlight and last-week winner banner.

import { useLeaderboardQuery } from "../hooks/useLeaderboard";
import type { LeaderboardEntry } from "../types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatXp(xp: number): string {
  return xp.toLocaleString();
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function LeaderboardRow({
  entry,
  highlight,
}: {
  entry: LeaderboardEntry;
  highlight: boolean;
}) {
  return (
    <tr
      data-testid={
        highlight ? "current-user-row" : `leaderboard-row-${entry.userId}`
      }
      className={
        highlight
          ? "bg-primary/10 font-semibold"
          : "hover:bg-muted/50 transition-colors"
      }
    >
      <td className="px-3 py-2 text-center tabular-nums">{entry.rank}</td>
      <td className="px-3 py-2">
        {entry.username}
        {highlight && (
          <span
            className="ml-2 inline-flex items-center rounded-full bg-primary/20 px-2 py-0.5 text-xs font-medium text-primary"
            aria-label="This is you"
          >
            You
          </span>
        )}
      </td>
      <td className="px-3 py-2 text-right tabular-nums">
        {formatXp(entry.weeklyXp)} XP
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function LeagueLeaderboard() {
  const { data, isLoading, isError } = useLeaderboardQuery();

  if (isLoading) {
    return (
      <div
        data-testid="loading-state"
        className="flex items-center justify-center py-12 text-muted-foreground"
        role="status"
        aria-label="Loading leaderboard"
      >
        <span className="animate-pulse">Loading leaderboard…</span>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div
        data-testid="empty-state"
        className="flex flex-col items-center justify-center py-12 text-muted-foreground"
      >
        <p>Unable to load leaderboard data.</p>
      </div>
    );
  }

  const { entries, currentUserEntry, lastWeekWinner } = data;
  const top20 = entries.slice(0, 20);

  const currentUserInTop20 = top20.some((e) => e.isCurrentUser);

  if (top20.length === 0 && !currentUserEntry) {
    return (
      <div
        data-testid="empty-state"
        className="flex flex-col items-center justify-center py-12 text-muted-foreground"
      >
        <p>No leaderboard data available yet. Keep earning XP!</p>
      </div>
    );
  }

  return (
    <div data-testid="leaderboard" className="space-y-4">
      {/* Last week's winner banner */}
      {lastWeekWinner && (
        <div
          data-testid="last-week-winner"
          className="rounded-lg border border-yellow-300 bg-yellow-50 dark:border-yellow-700 dark:bg-yellow-950 px-4 py-3 text-sm"
          role="status"
        >
          <span className="font-medium">Last week&apos;s winner:</span>{" "}
          {lastWeekWinner.username} with {formatXp(lastWeekWinner.xp)} XP
        </div>
      )}

      {/* Leaderboard table */}
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th scope="col" className="px-3 py-2 text-center font-medium">
                Rank
              </th>
              <th scope="col" className="px-3 py-2 text-left font-medium">
                Player
              </th>
              <th scope="col" className="px-3 py-2 text-right font-medium">
                Weekly XP
              </th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {top20.map((entry) => (
              <LeaderboardRow
                key={entry.userId}
                entry={entry}
                highlight={entry.isCurrentUser}
              />
            ))}
          </tbody>
        </table>
      </div>

      {/* Current user outside top 20 */}
      {!currentUserInTop20 && currentUserEntry && (
        <div
          data-testid="user-rank-outside"
          className="rounded-lg border border-dashed px-4 py-3 text-sm text-muted-foreground"
        >
          You are ranked <span className="font-semibold text-foreground">#{currentUserEntry.rank}</span>{" "}
          this week with {formatXp(currentUserEntry.weeklyXp)} XP
        </div>
      )}
    </div>
  );
}
