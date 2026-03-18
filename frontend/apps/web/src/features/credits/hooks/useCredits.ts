// useCredits.ts — Credits usage query (FE-8.6)

import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { apiClient } from "@reqruit/api-client";
import { queryKeys } from "@reqruit/api-client";
import { useCreditsStore } from "../store/credits-store";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface FeatureUsage {
  feature: string;
  creditsUsed: number;
}

export interface DailyUsage {
  date: string;
  creditsConsumed: number;
}

export interface CreditsData {
  dailyCreditsRemaining: number;
  dailyCreditsTotal: number;
  breakdown: FeatureUsage[];
  monthlyTrend: DailyUsage[];
}

// ---------------------------------------------------------------------------
// useCredits
// ---------------------------------------------------------------------------

export function useCredits() {
  const setCredits = useCreditsStore((s) => s.setCredits);

  const query = useQuery<CreditsData>({
    queryKey: queryKeys.credits.usage(),
    queryFn: () => apiClient.get<CreditsData>("/users/me/credits"),
    staleTime: 60 * 1000, // 1 minute
  });

  // Sync to Zustand store for synchronous access by AI action buttons (Rule 6)
  useEffect(() => {
    if (query.data) {
      setCredits(query.data.dailyCreditsRemaining);
    }
  }, [query.data, setCredits]);

  return query;
}
