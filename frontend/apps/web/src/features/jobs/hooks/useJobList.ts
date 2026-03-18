// useJobList.ts — Job list hooks (FE-5.1, FE-5.3)

import { useQuery } from "@tanstack/react-query";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import type { SavedJob } from "../types";

// ---------------------------------------------------------------------------
// useJobShortlist — FE-5.1: GET /jobs/shortlist (daily curated list)
// ---------------------------------------------------------------------------

export function useJobShortlist() {
  return useQuery<SavedJob[], ApiError>({
    queryKey: queryKeys.jobs.shortlist(),
    queryFn: () => apiClient.get<SavedJob[]>("/jobs/shortlist"),
    staleTime: 15 * 60 * 1000, // 15 minutes (ARCH-20 morning briefing config)
    refetchOnWindowFocus: true,
  });
}

// ---------------------------------------------------------------------------
// useSavedJobs — FE-5.3: GET /jobs (all saved jobs)
// ---------------------------------------------------------------------------

export function useSavedJobs() {
  return useQuery<SavedJob[], ApiError>({
    queryKey: queryKeys.jobs.list(),
    queryFn: () => apiClient.get<SavedJob[]>("/jobs"),
    staleTime: 5 * 60 * 1000, // 5 minutes (NFR-R4)
    gcTime: 30 * 60 * 1000, // 30 minutes (NFR-R4)
    refetchOnWindowFocus: true,
  });
}
