// useGamification.ts — Gamification queries (FE-8.2, FE-8.3)

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@reqruit/api-client";
import { queryKeys } from "@reqruit/api-client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type LeagueTier = "Bronze" | "Silver" | "Gold" | "Diamond";

export interface GamificationStatus {
  xp: number;
  streakDays: number;
  leagueTier: LeagueTier;
  leagueRank: number;
}

export interface ActivityDay {
  date: string; // ISO date string
  count: number;
  xpEarned: number;
}

export interface ActivityHistory {
  days: ActivityDay[];
}

// ---------------------------------------------------------------------------
// useGamificationStatus — FE-8.2
// ---------------------------------------------------------------------------

export function useGamificationStatus() {
  return useQuery<GamificationStatus>({
    queryKey: queryKeys.gamification.status(),
    queryFn: () =>
      apiClient.get<GamificationStatus>("/users/me/gamification"),
    staleTime: 60 * 1000, // 60 seconds
  });
}

// ---------------------------------------------------------------------------
// useActivityHistory — FE-8.3
// ---------------------------------------------------------------------------

export function useActivityHistory() {
  return useQuery<ActivityHistory>({
    queryKey: queryKeys.gamification.activityHistory(),
    queryFn: () =>
      apiClient.get<ActivityHistory>("/users/me/activity-history"),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
