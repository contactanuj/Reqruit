// useApplicationAssembly.ts — hooks for full application assembly workflow (FE-10.2)
// Triggers multi-step assembly (resume tailoring → cover letter → outreach) and
// tracks progress via polling or SSE.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import { useCreditsStore } from "@/features/credits/store/credits-store";

// Note: We use setCredits + getState() for atomic batch credit operations.

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type AssemblyStepStatus = "pending" | "running" | "complete" | "error";

export interface AssemblyStep {
  step: string;
  label: string;
  status: AssemblyStepStatus;
  error?: string;
}

export interface AssemblyStartResponse {
  assembly_id: string;
}

export interface AssemblyStatusResponse {
  assembly_id: string;
  status: "in_progress" | "complete" | "error";
  steps: AssemblyStep[];
}

// Assembly costs 3 credits (resume + cover letter + outreach)
const ASSEMBLY_CREDIT_COST = 3;

// ---------------------------------------------------------------------------
// useStartAssembly — FE-10.2 AC #1
// ---------------------------------------------------------------------------

export function useStartAssembly(applicationId: string) {
  const setCredits = useCreditsStore((s) => s.setCredits);
  const queryClient = useQueryClient();

  return useMutation<AssemblyStartResponse, ApiError, void>({
    mutationFn: () =>
      apiClient.post<AssemblyStartResponse>(
        `/applications/${applicationId}/assemble`,
        {},
      ),

    onMutate: () => {
      // Optimistic credit decrement — 3 credits for assembly (atomic)
      const current = useCreditsStore.getState().dailyCredits;
      setCredits(Math.max(0, current - ASSEMBLY_CREDIT_COST));
    },

    onSuccess: () => {
      // Trigger assembly status polling by invalidating
      void queryClient.invalidateQueries({
        queryKey: queryKeys.applications.assemblyStatus(applicationId),
      });
    },

    onError: () => {
      // Revert all 3 credits atomically
      const current = useCreditsStore.getState().dailyCredits;
      setCredits(current + ASSEMBLY_CREDIT_COST);
      toast.error("Failed to start application assembly — please try again");
    },
  });
}

// ---------------------------------------------------------------------------
// useAssemblyStatus — FE-10.2 AC #2
// Polls every 2s while assembly is in progress
// ---------------------------------------------------------------------------

export function useAssemblyStatus(
  applicationId: string,
  assemblyId: string | null,
) {
  return useQuery<AssemblyStatusResponse, ApiError>({
    queryKey: queryKeys.applications.assemblyStatus(applicationId),
    queryFn: () =>
      apiClient.get<AssemblyStatusResponse>(
        `/applications/${applicationId}/assemble/status`,
      ),
    enabled: !!assemblyId,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Stop polling when complete or errored with no running steps
      if (!data) return 2000;
      if (data.status === "complete") return false;
      if (
        data.status === "error" &&
        !data.steps.some((s) => s.status === "running")
      ) {
        return false;
      }
      return 2000;
    },
    staleTime: 0, // Always fresh during active assembly
  });
}

// ---------------------------------------------------------------------------
// useRetryAssemblyStep — FE-10.2 AC #4
// ---------------------------------------------------------------------------

export function useRetryAssemblyStep(applicationId: string) {
  const queryClient = useQueryClient();

  return useMutation<void, ApiError, { stepName: string }>({
    mutationFn: ({ stepName }) =>
      apiClient.post<void>(
        `/applications/${applicationId}/assemble/retry?step=${encodeURIComponent(stepName)}`,
        {},
      ),

    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.applications.assemblyStatus(applicationId),
      });
    },

    onError: () => {
      toast.error("Failed to retry step — please try again");
    },
  });
}

export { ASSEMBLY_CREDIT_COST };
