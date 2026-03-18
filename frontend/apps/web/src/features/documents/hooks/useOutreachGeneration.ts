// useOutreachGeneration.ts — hooks for AI outreach message workflow (FE-10.1)
// Follows same pattern as useCoverLetterGeneration (FE-7.1)

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import { useStreamStore } from "@/features/applications/store/stream-store";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface OutreachGeneratePayload {
  type: "linkedin" | "email";
  tone: "professional" | "casual";
  feedback?: string;
}

export interface OutreachGenerateResponse {
  thread_id: string;
}

export interface OutreachApprovePayload {
  text: string;
}

export interface OutreachApproveResponse {
  id: string;
  is_approved: boolean;
}

// ---------------------------------------------------------------------------
// useOutreachGeneration — FE-10.1 AC #2
// ---------------------------------------------------------------------------

export function useOutreachGeneration(jobId: string, contactId: string) {
  const decrementCredit = useCreditsStore((s) => s.decrementCredit);
  const incrementCredit = useCreditsStore((s) => s.incrementCredit);
  const setActiveThread = useStreamStore((s) => s.setActiveThread);
  const resetStream = useStreamStore((s) => s.reset);

  return useMutation<OutreachGenerateResponse, ApiError, OutreachGeneratePayload>({
    mutationFn: (payload) =>
      apiClient.post<OutreachGenerateResponse>(
        `/jobs/${jobId}/contacts/${contactId}/outreach/generate`,
        payload,
      ),

    onMutate: () => {
      // Optimistic credit decrement (ARCH-21)
      decrementCredit();
      resetStream();
    },

    onSuccess: (data) => {
      setActiveThread(data.thread_id);
    },

    onError: () => {
      // Revert optimistic decrement
      incrementCredit();
      toast.error("Failed to start outreach generation — please try again");
    },
  });
}

// ---------------------------------------------------------------------------
// useApproveOutreach — FE-10.1 AC #4
// ---------------------------------------------------------------------------

export function useApproveOutreach(jobId: string, contactId: string) {
  const queryClient = useQueryClient();

  return useMutation<OutreachApproveResponse, ApiError, OutreachApprovePayload>({
    mutationFn: (payload) =>
      apiClient.post<OutreachApproveResponse>(
        `/jobs/${jobId}/contacts/${contactId}/outreach/approve`,
        payload,
      ),

    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.outreach.list(jobId),
      });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.outreach.detail(jobId, contactId),
      });
    },

    onError: () => {
      toast.error("Failed to approve outreach message — please try again");
    },
  });
}
