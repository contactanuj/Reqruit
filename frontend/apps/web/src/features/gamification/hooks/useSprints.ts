// useSprints.ts — Sprint query and mutation hooks (FE-14.2)

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import type { Sprint } from "../types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CreateSprintPayload {
  goals: Array<{ description: string; targetCount: number }>;
}

interface RetrospectiveResponse {
  retrospective: string;
}

// ---------------------------------------------------------------------------
// useSprintsQuery — GET /gamification/sprints
// ---------------------------------------------------------------------------

export function useSprintsQuery() {
  return useQuery<Sprint[]>({
    queryKey: queryKeys.gamification.sprints(),
    queryFn: () => apiClient.get<Sprint[]>("/gamification/sprints"),
    staleTime: 60_000, // 1 minute
  });
}

// ---------------------------------------------------------------------------
// useCreateSprint — POST /gamification/sprints
// ---------------------------------------------------------------------------

export function useCreateSprint() {
  const queryClient = useQueryClient();
  const decrementCredit = useCreditsStore((s) => s.decrementCredit);
  const incrementCredit = useCreditsStore((s) => s.incrementCredit);

  return useMutation<Sprint, ApiError, CreateSprintPayload>({
    mutationFn: (payload) =>
      apiClient.post<Sprint>("/gamification/sprints", payload),

    onMutate: () => {
      decrementCredit();
    },

    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.gamification.sprints(),
      });
      toast.success("Sprint started successfully");
    },

    onError: () => {
      incrementCredit();
      toast.error("Failed to create sprint — please try again");
    },
  });
}

// ---------------------------------------------------------------------------
// useGenerateRetrospective — POST /gamification/sprints/{id}/retrospective/generate
// ---------------------------------------------------------------------------

export function useGenerateRetrospective(sprintId: string) {
  const queryClient = useQueryClient();

  return useMutation<RetrospectiveResponse, ApiError, void>({
    mutationFn: () =>
      apiClient.post<RetrospectiveResponse>(
        `/gamification/sprints/${sprintId}/retrospective/generate`,
        {},
      ),

    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.gamification.sprintDetail(sprintId),
      });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.gamification.sprints(),
      });
    },

    onError: () => {
      toast.error("Failed to generate retrospective — please try again");
    },
  });
}
