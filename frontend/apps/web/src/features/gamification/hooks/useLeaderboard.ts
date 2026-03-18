// useLeaderboard.ts — Leaderboard query hook (FE-14.1)

import { useQuery } from "@tanstack/react-query";
import { apiClient, queryKeys } from "@reqruit/api-client";
import type { LeaderboardData } from "../types";

// ---------------------------------------------------------------------------
// useLeaderboardQuery — GET /gamification/leaderboard
// ---------------------------------------------------------------------------

export function useLeaderboardQuery() {
  return useQuery<LeaderboardData>({
    queryKey: queryKeys.gamification.leaderboard(),
    queryFn: () =>
      apiClient.get<LeaderboardData>("/gamification/leaderboard"),
    staleTime: 300_000, // 5 minutes
  });
}
