// useDashboard.ts — Dashboard feature queries and mutations
// Covers FE-8.1 (morning briefing), FE-8.5 (nudges)

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient } from "@reqruit/api-client";
import { queryKeys } from "@reqruit/api-client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ActionUrgency = "deadline" | "interview" | "document" | "match";

export interface PendingAction {
  id: string;
  urgency: ActionUrgency;
  description: string;
  ctaLabel: string;
  ctaHref: string;
}

export interface MorningBriefing {
  newJobMatchCount: number;
  streakDays: number;
  pendingActions: PendingAction[];
}

export type NudgeType =
  | "follow_up"
  | "interview_prep"
  | "ghost_job"
  | "deadline";

export interface Nudge {
  id: string;
  type: NudgeType;
  message: string;
  ctaLabel: string;
  ctaHref: string;
}

// ---------------------------------------------------------------------------
// useMorningBriefing — FE-8.1
// ---------------------------------------------------------------------------

export function useMorningBriefing() {
  return useQuery<MorningBriefing>({
    queryKey: queryKeys.dashboard.morningBriefing(),
    queryFn: () =>
      apiClient.get<MorningBriefing>("/dashboard/morning-briefing"),
    staleTime: 15 * 60 * 1000, // 15 minutes (ARCH-20)
    gcTime: 60 * 60 * 1000,     // 1 hour
    refetchOnWindowFocus: true,
  });
}

// ---------------------------------------------------------------------------
// useNudges — FE-8.5
// ---------------------------------------------------------------------------

export function useNudges() {
  return useQuery<Nudge[]>({
    queryKey: queryKeys.dashboard.nudges(),
    queryFn: () => apiClient.get<Nudge[]>("/nudges"),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// ---------------------------------------------------------------------------
// useDismissNudge — FE-8.5 (optimistic)
// ---------------------------------------------------------------------------

export function useDismissNudge() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: (nudgeId: string) =>
      apiClient.patch(`/nudges/${nudgeId}/dismiss`),

    onMutate: async (nudgeId) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.dashboard.nudges() });
      const previous = queryClient.getQueryData<Nudge[]>(queryKeys.dashboard.nudges());
      queryClient.setQueryData<Nudge[]>(queryKeys.dashboard.nudges(), (old) =>
        old ? old.filter((n) => n.id !== nudgeId) : []
      );
      return { previous };
    },

    onError: (_err, _nudgeId, context) => {
      const ctx = context as { previous?: Nudge[] } | undefined;
      if (ctx?.previous) {
        queryClient.setQueryData(queryKeys.dashboard.nudges(), ctx.previous);
      }
      toast.error("Failed to dismiss nudge. Please try again.");
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.nudges() });
    },
  });
}
